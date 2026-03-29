#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import textwrap
import unicodedata
from pathlib import Path

import optech_fr as base


def split_front_matter(markdown_text: str) -> tuple[str, str]:
    m = re.match(r"^(---\n.*?\n---\n)(.*)$", markdown_text, re.DOTALL)
    if not m:
        return "", markdown_text
    return m.group(1), m.group(2)


def strip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"<!--.*?-->", "", text)
    return text.strip()


def slugify_heading(text: str) -> str:
    text = strip_markdown(text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = text.replace("'", "")
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text


def extract_headings(markdown_text: str) -> list[dict]:
    headings = []
    in_code = False
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            text = m.group(2).strip()
            headings.append({"text": text, "slug": slugify_heading(text)})
    return headings


_link_cache: dict[tuple[str, str, str, str], str] = {}


def localize_newsletter_anchor(year: str, month: str, day: str, en_anchor: str) -> str | None:
    key = (year, month, day, en_anchor)
    if key in _link_cache:
        return _link_cache[key]

    en_url = f"https://bitcoinops.org/en/newsletters/{year}/{month}/{day}/"
    try:
        en_md = base.fetch(base.upstream_raw_md_url(en_url, "en")).text
        fr_md = base.fetch(base.upstream_raw_md_url(en_url, "fr")).text
    except Exception:
        _link_cache[key] = None
        return None

    en_fm, en_body = base.parse_front_matter(en_md)
    fr_fm, fr_body = base.parse_front_matter(fr_md)

    en_headings = extract_headings(en_body)
    fr_headings = extract_headings(fr_body)

    idx = None
    for i, heading in enumerate(en_headings):
        if heading["slug"] == en_anchor:
            idx = i
            break

    fr_permalink = fr_fm.get("permalink") or f"/fr/newsletters/{year}/{month}/{day}/"
    if idx is None:
        localized = fr_permalink
    elif idx < len(fr_headings):
        localized = f"{fr_permalink}#{fr_headings[idx]['slug']}"
    else:
        localized = fr_permalink

    _link_cache[key] = localized
    return localized


def localize_internal_links(markdown_text: str) -> str:
    def repl(match: re.Match) -> str:
        year, month, day, anchor = match.group(1), match.group(2), match.group(3), match.group(4)
        localized = localize_newsletter_anchor(year, month, day, anchor)
        return localized or match.group(0)

    pattern = re.compile(r"/en/(?:newsletters|bulletins)/(\d{4})/(\d{2})/(\d{2})/#([a-z0-9\-]+)")
    return pattern.sub(repl, markdown_text)


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


_original_process_one = base.process_one


def process_one(*args, **kwargs):
    result = _original_process_one(*args, **kwargs)
    if result.get("status") in {"ok", "skipped_existing"} and result.get("output"):
        postprocess_output(result["output"])
    return result


base.process_one = process_one

if __name__ == "__main__":
    base.main()
