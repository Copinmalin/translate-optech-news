#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
resolve_optech_newsletter_links.py

Détecte et remplace dans les traductions FR les liens internes vers des newsletters
anglais par la version FR correspondante, lorsque celle-ci existe et que l'ancre
peut être déterminée de manière fiable. Produit également un rapport des cas traités.

Usage :

  python resolve_optech_newsletter_links.py \
    --bitcoinops-repo /chemin/vers/bitcoinops.github.io \
    --lang fr \
    --file _posts/fr/newsletters/2018-07-17-newsletter.md \
    --write \
    --report reports/unresolved_links_fr.md

Ou pour traiter tous les fichiers :

  python resolve_optech_newsletter_links.py \
    --bitcoinops-repo /chemin/vers/bitcoinops.github.io \
    --lang fr \
    --all \
    --write \
    --report reports/unresolved_links_fr.md

Voir la spécification fonctionnelle pour plus de détails.
"""

import argparse
import json
import os
import re
from typing import Dict, List, Tuple, Optional


def extract_anchors(html_content: str) -> List[str]:
    """Extrait toutes les valeurs d’attribut id="..." dans l’ordre d’apparition."""
    return re.findall(r'id="([^"]+)"', html_content)


def load_overrides(path: str) -> Dict[str, Dict[str, str]]:
    """Charge les surcharges d’ancres depuis un fichier JSON."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        raise RuntimeError(f"Le fichier d’overrides {path} est invalide.")


def read_html(repo_path: str, lang: str, date: str) -> Optional[str]:
    """
    Lit le fichier HTML généré pour une newsletter donnée.
    `date` est au format YYYY-MM-DD.
    Retourne None si le fichier n’existe pas.
    """
    year, month, day = date.split("-")
    html_path = os.path.join(
        repo_path, "_site", lang, "newsletters", year, month, day, "index.html"
    )
    if not os.path.exists(html_path):
        return None
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


def resolve_anchor(
    en_anchor: str,
    anchors_en: List[str],
    anchors_fr: List[str],
    overrides_date: Optional[Dict[str, str]],
) -> Tuple[Optional[str], str]:
    """
    Résout l’ancre FR correspondant à l’ancre EN.
    Retourne (ancre_fr, statut).
    """
    # Surcharge manuelle
    if overrides_date and en_anchor in overrides_date:
        return overrides_date[en_anchor], "RESOLVED_BY_OVERRIDE"

    # Mapping par position si possible
    if en_anchor in anchors_en:
        idx = anchors_en.index(en_anchor)
        if idx < len(anchors_fr):
            return anchors_fr[idx], "RESOLVED_BY_POSITION"

    # Non résolu
    return None, "MANUAL_REVIEW_REQUIRED"


def process_file(
    repo_path: str,
    file_path: str,
    overrides: Dict[str, Dict[str, str]],
    lang: str,
    write: bool,
    report: List[Dict[str, str]],
) -> bool:
    """
    Traite un fichier markdown FR pour remplacer les liens EN vers des newsletters.
    Retourne True si le fichier a été modifié.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"/en/newsletters/(\d{4})/(\d{2})/(\d{2})/#([A-Za-z0-9\-]+)"
    )
    matches = list(pattern.finditer(content))
    if not matches:
        return False

    modified = False
    for m in matches:
        year, month, day, anchor_en = m.groups()
        date = f"{year}-{month}-{day}"
        en_url = m.group(0)

        # Vérifier l’existence de la cible FR
        md_fr = os.path.join(
            repo_path,
            "_posts",
            lang,
            "newsletters",
            f"{date}-newsletter.md",
        )
        html_fr = read_html(repo_path, lang, date)
        html_en = read_html(repo_path, "en", date)

        if not (os.path.exists(md_fr) and html_fr and html_en):
            report.append(
                {
                    "source_file": file_path,
                    "original_url": en_url,
                    "target_base_url": f"/{lang}/newsletters/{year}/{month}/{day}/",
                    "resolved_url": None,
                    "status": "SKIPPED_NO_FR_TARGET",
                    "reason": "Version FR manquante ou HTML non généré",
                }
            )
            continue

        anchors_en = extract_anchors(html_en)
        anchors_fr = extract_anchors(html_fr)
        resolved_anchor, status = resolve_anchor(
            anchor_en,
            anchors_en,
            anchors_fr,
            overrides.get(date),
        )

        if resolved_anchor:
            new_url = f"/{lang}/newsletters/{year}/{month}/{day}/#{resolved_anchor}"
            report.append(
                {
                    "source_file": file_path,
                    "original_url": en_url,
                    "target_base_url": f"/{lang}/newsletters/{year}/{month}/{day}/",
                    "resolved_url": new_url,
                    "status": status,
                    "reason": "",
                }
            )
            if write:
                content = content.replace(en_url, new_url)
                modified = True
        else:
            report.append(
                {
                    "source_file": file_path,
                    "original_url": en_url,
                    "target_base_url": f"/{lang}/newsletters/{year}/{month}/{day}/",
                    "resolved_url": None,
                    "status": "MANUAL_REVIEW_REQUIRED",
                    "reason": "Impossible de déterminer l’ancre FR",
                }
            )

    if write and modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    return modified


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Résout les liens internes des newsletters Optech (EN vers FR) "
            "dans les fichiers markdown traduits."
        )
    )
    parser.add_argument(
        "--bitcoinops-repo",
        required=True,
        help="Chemin local du dépôt bitcoinops.github.io",
    )
    parser.add_argument(
        "--lang",
        default="fr",
        help="Langue cible, par défaut 'fr'",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file",
        help="Fichier markdown FR à traiter, chemin relatif depuis la racine du repo",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Traiter tous les fichiers dans _posts/<lang>/newsletters",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Appliquer effectivement les remplacements (sinon simulation)",
    )
    parser.add_argument(
        "--overrides",
        default=os.path.join(
            os.path.dirname(__file__), "..", "data", "manual_anchor_overrides_fr.json"
        ),
        help="Chemin vers le fichier JSON de surcharges",
    )
    parser.add_argument(
        "--report",
        help=(
            "Chemin du fichier où écrire un rapport JSON ligne par ligne des actions effectuées"
        ),
    )
    args = parser.parse_args()

    overrides = load_overrides(args.overrides)
    repo_path = args.bitcoinops_repo
    report_data: List[Dict[str, str]] = []

    if args.file:
        target_file = os.path.join(repo_path, args.file)
        process_file(
            repo_path,
            target_file,
            overrides,
            args.lang,
            args.write,
            report_data,
        )
    else:
        # Parcourir tous les fichiers .md dans _posts/<lang>/newsletters
        newsletters_dir = os.path.join(
            repo_path, "_posts", args.lang, "newsletters"
        )
        for name in os.listdir(newsletters_dir):
            if name.endswith(".md"):
                process_file(
                    repo_path,
                    os.path.join(newsletters_dir, name),
                    overrides,
                    args.lang,
                    args.write,
                    report_data,
                )

    # Écrire le rapport si demandé
    if args.report:
        os.makedirs(os.path.dirname(args.report), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            for entry in report_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Résumé en console
    resolved = sum(1 for r in report_data if r["resolved_url"])
    skipped = sum(1 for r in report_data if r["status"].startswith("SKIPPED"))
    manual = sum(1 for r in report_data if r["status"] == "MANUAL_REVIEW_REQUIRED")
    print(
        f"Liens résolus: {resolved}, ignorés: {skipped}, nécessitant une revue manuelle: {manual}"
    )


if __name__ == "__main__":
    main()
