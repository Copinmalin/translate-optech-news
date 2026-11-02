#!/usr/bin/env python3
"""Localize newsletter links using a rendered upstream tree including the review batch.

No network requests are made. Ambiguous anchors require a reviewed override.
Audit mode fails on every English link whose French source exists in this tree.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

from bs4 import BeautifulSoup


URL_RE = re.compile(
    r"(?<![\w:/])(?:https://bitcoinops\.org)?/en/newsletters/"
    r"\d{4}/\d{2}/\d{2}/(?:[?#][^\s<>\)\]\"']*)?"
)
PROTECTED_RE = re.compile(
    r"(?ms)\A---\n.*?\n---\n|^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[^\n]*(?:\n|$)"
    r"|{%\s*comment\s*%}.*?{%\s*endcomment\s*%}|<!--.*?-->|`[^`\n]*`"
)


class Resolver:
    def __init__(self, repo: Path, overrides: dict):
        self.repo = repo
        self.overrides = overrides
        self.pages: dict[str, tuple[set[str], list[tuple[tuple, str]]]] = {}

    def page(self, path: str) -> tuple[set[str], list[tuple[tuple, str]]]:
        if path not in self.pages:
            html = self.repo / "_site" / path.strip("/") / "index.html"
            soup = BeautifulSoup(html.read_text(encoding="utf-8"), "html.parser")
            article = soup.find("article") or soup.find("main")
            if article is None:
                raise ValueError(f"Article HTML introuvable : {html}")
            ids = [str(node["id"]) for node in article.select("[id]")]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Ancres dupliquées : {html}")
            outline = []
            for node in article.select("h2[id], h3[id], h4[id], h5[id], h6[id], li[id]"):
                depth = sum(parent.name in {"ul", "ol"} for parent in node.parents)
                outline.append(((node.name, depth), str(node["id"])))
            self.pages[path] = (set(ids), outline)
        return self.pages[path]

    def resolve(self, url: str) -> dict:
        parsed = urlsplit(url)
        fr_path = parsed.path.replace("/en/newsletters/", "/fr/newsletters/", 1)
        date = parsed.path.strip("/").split("/")[2:]
        source = self.repo / "_posts/fr/newsletters" / ("-".join(date) + "-newsletter.md")
        if not source.is_file():
            return {"status": "kept_en", "reason": "fr_source_missing"}
        try:
            fr_ids, fr_outline = self.page(fr_path)
            anchor = unquote(parsed.fragment)
            mode = "same_anchor" if anchor else "base_only"
            if anchor and anchor not in fr_ids:
                override = self.overrides.get("-".join(date), {}).get(anchor)
                if override is not None:
                    if override not in fr_ids:
                        raise ValueError(f"Surcharge absente du rendu FR : {override}")
                    anchor, mode = override, "override"
                else:
                    _, en_outline = self.page(parsed.path)
                    # Compare the complete anchored outline, not arbitrary DOM indices.
                    # Shared stable anchors must also stay aligned. Any structural drift
                    # requires an explicit override instead of a positional guess.
                    if [kind for kind, _ in en_outline] != [kind for kind, _ in fr_outline]:
                        raise ValueError("Structures EN et FR différentes")
                    shared = {a for _, a in en_outline} & {a for _, a in fr_outline}
                    if any(a != b and (a in shared or b in shared)
                           for (_, a), (_, b) in zip(en_outline, fr_outline)):
                        raise ValueError("Ancres communes désalignées")
                    matches = [b for (_, a), (_, b) in zip(en_outline, fr_outline) if a == anchor]
                    if len(matches) != 1:
                        raise ValueError(f"Correspondance d'ancre ambiguë : {anchor}")
                    anchor, mode = matches[0], "aligned_outline"
            target = urlunsplit(("", "", fr_path, parsed.query, anchor))
            return {"status": "convertible", "to": target, "mode": mode}
        except (OSError, ValueError) as error:
            return {"status": "unresolved", "reason": str(error)}


def process_text(text: str, resolver: Resolver, apply: bool) -> tuple[str, list[dict]]:
    protected = [(match.start(), match.end()) for match in PROTECTED_RE.finditer(text)]
    report = []

    def replace(match: re.Match) -> str:
        if any(start <= match.start() < end for start, end in protected):
            return match.group(0)
        url = match.group(0)
        result = {"from": url, **resolver.resolve(url)}
        report.append(result)
        return result["to"] if apply and result["status"] == "convertible" else url

    return URL_RE.sub(replace, text), report


def run(repo: Path, target: Path, overrides: dict, apply: bool) -> tuple[list[dict], bool]:
    files = [target] if target.is_file() else sorted(target.rglob("*-newsletter.md"))
    if not files:
        raise ValueError(f"Aucun bulletin à contrôler : {target}")
    resolver = Resolver(repo, overrides)
    report = []
    failed = False
    pending = []
    for path in files:
        original = path.read_text(encoding="utf-8")
        updated, links = process_text(original, resolver, apply)
        for link in links:
            report.append({"file": str(path), **link})
            if link["status"] == "unresolved" or (not apply and link["status"] == "convertible"):
                failed = True
        pending.append((path, original, updated))
    # Do not partially rewrite a batch that needs human anchor decisions.
    if apply and not failed:
        for path, original, updated in pending:
            if updated != original:
                path.write_text(updated, encoding="utf-8")
    return report, failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitcoinops-repo", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--overrides", type=Path,
                        default=Path(__file__).resolve().parents[1] / "data/manual_anchor_overrides_fr.json")
    args = parser.parse_args()
    overrides = json.loads(args.overrides.read_text(encoding="utf-8"))
    report, failed = run(args.bitcoinops_repo, args.target, overrides, args.apply)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in report:
        print(f"{item['status']}: {item['file']}: {item['from']} -> {item.get('to', item.get('reason'))}")
    if failed:
        raise SystemExit("Liens EN avec cible FR disponible : correction ou surcharge d'ancre requise.")


if __name__ == "__main__":
    main()
