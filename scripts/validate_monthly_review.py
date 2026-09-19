#!/usr/bin/env python3
"""Validate a reviewed monthly newsletter batch and its manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
NEWSLETTER_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-newsletter\.md$")


def front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise RuntimeError(f"Front matter introuvable: {path}")
    return yaml.safe_load(match.group(1)) or {}


def validate_batch(batch_dir: Path, manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    month = manifest.get("month")
    if not isinstance(month, str) or not MONTH_RE.fullmatch(month):
        raise RuntimeError("Mois absent ou invalide dans le manifeste.")

    expected = manifest.get("files")
    if not isinstance(expected, list) or not expected:
        raise RuntimeError("Le manifeste doit contenir au moins une newsletter.")
    if any(not isinstance(name, str) or Path(name).name != name for name in expected):
        raise RuntimeError("Le manifeste contient un nom de fichier invalide.")

    actual = sorted(path.name for path in batch_dir.glob("*.md"))
    if sorted(expected) != actual:
        raise RuntimeError(f"Fichiers différents du manifeste: attendu={sorted(expected)}, trouvé={actual}")

    for filename in actual:
        if not NEWSLETTER_FILE_RE.fullmatch(filename) or not filename.startswith(f"{month}-"):
            raise RuntimeError(f"Fichier hors du mois {month}: {filename}")
        metadata = front_matter(batch_dir / filename)
        if metadata.get("lang") != "fr":
            raise RuntimeError(f"Langue française absente du front matter: {filename}")
        permalink = metadata.get("permalink")
        if not isinstance(permalink, str) or not permalink.startswith("/fr/newsletters/"):
            raise RuntimeError(f"Permalien français invalide: {filename}")

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = validate_batch(args.batch_dir, args.manifest)
    print(f"Lot {manifest['month']} valide: {len(manifest['files'])} newsletter(s).")


if __name__ == "__main__":
    main()
