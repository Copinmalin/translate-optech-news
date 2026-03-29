#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

import optech_fr as base

SITE_BASE = "https://bitcoinops.org"


def split_front_matter(markdown_text: str) -> tuple[str, str]:
    m = re.match(r"^(---\n.*?\n---\n)(.*)$", markdown_text, re.DOTALL)
    if not m:
        return "", markdown_text
    return m.group(1), m.group(2)


def extract_dom_ids(html_text: str) -> list[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        return []
    ids = []
    seen = set()
    for el in main.find_all(attrs={"id": True}):
        el_id = str(el.get("id", "")).strip()
        if el_id and el_id not in seen:
            ids.append(el_id)
            seen.add(el_id)
    return ids


_page_cache: dict[str, tuple[bool, str, list[str]]] = {}
_resolution_log: dict[str, dict] = {}


def fetch_page(path: str) -> tuple[bool, str, list[str]]:
    if path in _page_cache:
        return _page_cache[path]
    url = SITE_BASE + path
    try:
        resp = base.fetch(url)
        html = resp.text
        ids = extract_dom_ids(html)
        _page_cache[path] = (True, html, ids)
        return _page_cache[path]
    except Exception:
        _page_cache[path] = (False, "", [])
        return _page_cache[path]


def candidate_paths(path_no_anchor: str, target_lang: str) -> list[str]:
    if target_lang not in {"en", "fr"}:
        return [path_no_anchor]

    if path_no_anchor.startswith("/en/"):
        base_path = f"/{target_lang}/" + path_no_anchor[len("/en/"):]
    elif path_no_anchor.startswith("/fr/"):
        base_path = f"/{target_lang}/" + path_no_anchor[len("/fr/"):]
    else:
        base_path = path_no_anchor

    candidates = [base_path]
    if "/newsletters/" in base_path:
        candidates.append(base_path.replace("/newsletters/", "/bulletins/", 1))
    if "/bulletins/" in base_path:
        candidates.append(base_path.replace("/bulletins/", "/newsletters/", 1))

    final = []
    seen = set()
    for c in candidates:
        if c not in seen:
            seen.add(c)
            final.append(c)
    return final


def resolve_internal_url(en_relative_url: str) -> str:
    parsed = urlsplit(en_relative_url)
    raw_en_path = parsed.path
    en_anchor = parsed.fragment

    if not raw_en_path.startswith("/en/"):
        return en_relative_url

    chosen_en_path = None
    en_ids = []
    for candidate in candidate_paths(raw_en_path, "en"):
        exists, _, ids = fetch_page(candidate)
        if exists:
            chosen_en_path = candidate
            en_ids = ids
            break

    if chosen_en_path is None:
        _resolution_log[en_relative_url] = {"status": "kept_en", "reason": "en_missing"}
        return en_relative_url

    chosen_fr_path = None
    fr_ids = []
    for candidate in candidate_paths(chosen_en_path, "fr"):
        exists, _, ids = fetch_page(candidate)
        if exists:
            chosen_fr_path = candidate
            fr_ids = ids
            break

    if chosen_fr_path is None:
        _resolution_log[en_relative_url] = {"status": "kept_en", "reason": "fr_missing", "normalized_en": chosen_en_path}
        return en_relative_url

    if not en_anchor:
        _resolution_log[en_relative_url] = {"status": "resolved", "resolved_to": chosen_fr_path}
        return chosen_fr_path

    if en_anchor in fr_ids:
        resolved = f"{chosen_fr_path}#{en_anchor}"
        _resolution_log[en_relative_url] = {"status": "resolved", "resolved_to": resolved, "mode": "same_anchor"}
        return resolved

    if en_anchor in en_ids:
        idx = en_ids.index(en_anchor)
        if idx < len(fr_ids):
            resolved = f"{chosen_fr_path}#{fr_ids[idx]}"
            _resolution_log[en_relative_url] = {"status": "resolved", "resolved_to": resolved, "mode": "dom_index"}
            return resolved

    _resolution_log[en_relative_url] = {"status": "resolved_base_only", "resolved_to": chosen_fr_path, "reason": "anchor_unresolved"}
    return chosen_fr_path


def localize_internal_links(markdown_text: str) -> str:
    pattern = re.compile(r"/en/[A-Za-z0-9_./\-]+(?:#[A-Za-z0-9_\-]+)?")
    return pattern.sub(lambda m: resolve_internal_url(m.group(0)), markdown_text)


def is_reference_definition(line: str) -> bool:
    return bool(re.match(r"^\[[^\]]+\]:\s", line))


def is_list_item(line: str) -> bool:
    return bool(re.match(r"^\s*([-*+] |\d+\. )", line))


def wrap_paragraph(text: str, width: int, initial_indent: str = "", subsequent_indent: str = "") -> str:
    return textwrap.fill(
        " ".join(text.split()),
        width=width,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def wrap_markdown_body(text: str, width: int) -> str:
    lines = text.splitlines()
    out = []
    buf = []
    in_code = False
    i = 0

    def flush_plain():
        nonlocal buf
        if buf:
            out.append(wrap_paragraph(" ".join(s.strip() for s in buf), width))
            buf = []

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_plain()
            out.append(line)
            in_code = not in_code
            i += 1
            continue

        if in_code:
            out.append(line)
            i += 1
            continue

        if not stripped:
            flush_plain()
            out.append("")
            i += 1
            continue

        if stripped.startswith("#") or stripped.startswith("{%") or stripped.startswith("%}") or is_reference_definition(line) or stripped.startswith(">"):
            flush_plain()
            out.append(line)
            i += 1
            continue

        if is_list_item(line):
            flush_plain()
            m = re.match(r"^(\s*)([-*+] |\d+\. )(.*)$", line)
            indent = (m.group(1) or "") + (m.group(2) or "")
            continuation_indent = " " * len(indent)
            item_lines = [m.group(3)]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].rstrip()
                nxt_stripped = nxt.strip()
                if not nxt_stripped:
                    break
                if is_list_item(nxt) or nxt_stripped.startswith("#") or nxt_stripped.startswith("```") or is_reference_definition(nxt) or nxt_stripped.startswith("{%"):
                    break
                item_lines.append(nxt_stripped)
                j += 1
            out.append(wrap_paragraph(" ".join(item_lines), width, initial_indent=indent, subsequent_indent=continuation_indent))
            i = j
            continue

        buf.append(line)
        i += 1

    flush_plain()
    return "\n".join(out).strip() + "\n"


def postprocess_output(path_str: str) -> None:
    path = Path(path_str)
    if not path.exists():
        return
    preferences = base.load_preferences()
    width = int(preferences.get("wrap_width", 140))
    text = path.read_text(encoding="utf-8")
    front_matter, body = split_front_matter(text)
    body = localize_internal_links(body)
    body = wrap_markdown_body(body, width)
    path.write_text(front_matter + body, encoding="utf-8")

    report_path = path.parent.parent.parent / "link-resolution-report.json"
    report_path.write_text(json.dumps(_resolution_log, ensure_ascii=False, indent=2), encoding="utf-8")


_original_process_one = base.process_one


def process_one(*args, **kwargs):
    result = _original_process_one(*args, **kwargs)
    if result.get("status") in {"ok", "skipped_existing"} and result.get("output"):
        postprocess_output(result["output"])
    return result


base.process_one = process_one

if __name__ == "__main__":
    base.main()
