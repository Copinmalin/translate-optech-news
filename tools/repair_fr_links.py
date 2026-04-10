#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import optech_fr as base

SITE_BASE = "https://bitcoinops.org"
OUTPUT_DIR = Path("output")

_page_cache: dict[str, tuple[bool, str, list[str]]] = {}


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


def resolve_internal_url(en_relative_url: str) -> tuple[str, dict]:
    parsed = urlsplit(en_relative_url)
    raw_en_path = parsed.path
    en_anchor = parsed.fragment

    if not raw_en_path.startswith("/en/"):
        return en_relative_url, {"status": "ignored_non_en"}

    chosen_en_path = None
    en_ids = []
    for candidate in candidate_paths(raw_en_path, "en"):
        exists, _, ids = fetch_page(candidate)
        if exists:
            chosen_en_path = candidate
            en_ids = ids
            break

    if chosen_en_path is None:
        return en_relative_url, {"status": "kept_en", "reason": "en_missing"}

    chosen_fr_path = None
    fr_ids = []
    for candidate in candidate_paths(chosen_en_path, "fr"):
        exists, _, ids = fetch_page(candidate)
        if exists:
            chosen_fr_path = candidate
            fr_ids = ids
            break

    if chosen_fr_path is None:
        return en_relative_url, {"status": "kept_en", "reason": "fr_missing", "normalized_en": chosen_en_path}

    if not en_anchor:
        return chosen_fr_path, {"status": "resolved", "mode": "base_only", "resolved_to": chosen_fr_path}

    if en_anchor in fr_ids:
        resolved = f"{chosen_fr_path}#{en_anchor}"
        return resolved, {"status": "resolved", "mode": "same_anchor", "resolved_to": resolved}

    if en_anchor in en_ids:
        idx = en_ids.index(en_anchor)
        if idx < len(fr_ids):
            resolved = f"{chosen_fr_path}#{fr_ids[idx]}"
            return resolved, {"status": "resolved", "mode": "dom_index", "resolved_to": resolved}

    return chosen_fr_path, {"status": "resolved_base_only", "reason": "anchor_unresolved", "resolved_to": chosen_fr_path}


def localize_internal_links(markdown_text: str) -> tuple[str, list[dict]]:
    changes: list[dict] = []
    pattern = re.compile(r"/en/[A-Za-z0-9_./\-]+(?:#[A-Za-z0-9_\-]+)?")

    def repl(match: re.Match) -> str:
        original = match.group(0)
        replacement, meta = resolve_internal_url(original)
        if replacement != original:
            changes.append({"from": original, "to": replacement, **meta})
        else:
            changes.append({"from": original, "to": replacement, **meta})
        return replacement

    new_text = pattern.sub(repl, markdown_text)
    return new_text, changes


def collect_files(target: str) -> list[Path]:
    p = Path(target)
    if p.is_file():
        return [p]
    if p.is_dir():
        return sorted(p.rglob("*.md"))
    return sorted(Path().glob(target))


def process_file(path: Path, apply_changes: bool) -> dict:
    original = path.read_text(encoding="utf-8")
    front_matter, body = split_front_matter(original)
    new_body, changes = localize_internal_links(body)
    updated = front_matter + new_body
    changed = updated != original

    if apply_changes and changed:
        path.write_text(updated, encoding="utf-8")

    return {
        "file": str(path),
        "changed": changed,
        "changes": changes,
        "old_text": original,
        "new_text": updated,
    }


def write_reports(results: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    report = []
    diff_chunks = []

    for result in results:
        report.append({
            "file": result["file"],
            "changed": result["changed"],
            "changes": result["changes"],
        })
        if result["changed"]:
            diff = difflib.unified_diff(
                result["old_text"].splitlines(keepends=True),
                result["new_text"].splitlines(keepends=True),
                fromfile=result["file"],
                tofile=result["file"],
            )
            diff_chunks.append("".join(diff))

    (OUTPUT_DIR / "link-repair-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "link-repair-diff.patch").write_text(
        "\n".join(diff_chunks),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair internal EN links in existing FR newsletters.")
    parser.add_argument("--mode", choices=["audit", "apply"], default="audit")
    parser.add_argument("--target", default="_posts/fr/newsletters")
    parser.add_argument("--branch", default="fix/fr-links")
    args = parser.parse_args()

    files = collect_files(args.target)
    if not files:
        raise SystemExit(f"No markdown files found for target: {args.target}")

    results = [process_file(path, apply_changes=(args.mode == "apply")) for path in files]
    write_reports(results)

    changed_count = sum(1 for r in results if r["changed"])
    print(f"Processed {len(results)} file(s), changed {changed_count}.")
    print(f"Report: {OUTPUT_DIR / 'link-repair-report.json'}")
    print(f"Diff: {OUTPUT_DIR / 'link-repair-diff.patch'}")


if __name__ == "__main__":
    main()
