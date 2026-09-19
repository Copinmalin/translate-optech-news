#!/usr/bin/env python3
"""Prepare the oldest incomplete month of French newsletters for review."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import optech_fr
import optech_fr_linkresolver3 as translator


NEWSLETTER_FILE_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-newsletter\.md$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
MONTHLY_MIN_DATE = date(2018, 6, 8)


@dataclass(frozen=True)
class MonthPlan:
    month: str
    urls: tuple[str, ...]
    missing_urls: tuple[str, ...]


@dataclass(frozen=True)
class TranslationOutcome:
    translated_files: tuple[Path, ...]
    results: tuple[dict, ...]


def newsletter_url(newsletter_date: str) -> str:
    year, month, day = newsletter_date.split("-")
    return f"https://bitcoinops.org/en/newsletters/{year}/{month}/{day}/"


def source_newsletter_urls(bitcoinops_repo: Path, min_date: date) -> list[str]:
    """Read the English newsletter inventory from the checked-out upstream tree."""

    source_dir = bitcoinops_repo / "_posts" / "en" / "newsletters"
    if not source_dir.is_dir():
        raise RuntimeError(f"Dossier source anglais introuvable: {source_dir}")

    urls = []
    for path in source_dir.glob("*-newsletter.md"):
        match = NEWSLETTER_FILE_RE.fullmatch(path.name)
        if not match:
            continue
        newsletter_date = date.fromisoformat(match.group("date"))
        if newsletter_date >= min_date:
            urls.append(newsletter_url(newsletter_date.isoformat()))
    return sorted(urls, key=optech_fr.newsletter_date_from_url)


def existing_fr_slugs(bitcoinops_repo: Path) -> set[str]:
    fr_dir = bitcoinops_repo / "_posts" / "fr" / "newsletters"
    if not fr_dir.exists():
        return set()
    return {path.stem for path in fr_dir.glob("*.md")}


def read_covered_slugs(path: Path | None) -> set[str]:
    if path is None:
        return set()
    if not path.exists():
        raise RuntimeError(f"Fichier de newsletters couvertes introuvable: {path}")
    return {
        Path(line.strip()).stem
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def month_from_url(url: str) -> str:
    newsletter_date = optech_fr.newsletter_date_from_url(url)
    return f"{newsletter_date.year:04d}-{newsletter_date.month:02d}"


def build_month_plans(
    urls: list[str],
    fr_slugs: set[str],
    covered_slugs: set[str] | None = None,
) -> list[MonthPlan]:
    covered = covered_slugs or set()
    per_month: dict[str, list[str]] = defaultdict(list)
    for url in urls:
        per_month[month_from_url(url)].append(url)

    plans: list[MonthPlan] = []
    for month in sorted(per_month):
        month_urls = tuple(sorted(per_month[month], key=optech_fr.newsletter_date_from_url))
        missing = tuple(
            url
            for url in month_urls
            if optech_fr.slug_from_en_url(url) not in fr_slugs
            and optech_fr.slug_from_en_url(url) not in covered
        )
        if missing:
            plans.append(MonthPlan(month=month, urls=month_urls, missing_urls=missing))
    return plans


def pick_month(plan_list: list[MonthPlan], forced_month: str | None) -> MonthPlan | None:
    if forced_month is None:
        return plan_list[0] if plan_list else None
    if not MONTH_RE.fullmatch(forced_month):
        raise ValueError("Le mois forcé doit respecter le format AAAA-MM.")
    return next((plan for plan in plan_list if plan.month == forced_month), None)


def translate_missing_newsletters(month_plan: MonthPlan, output_dir: Path, model: str) -> TranslationOutcome:
    translated: list[Path] = []
    results: list[dict] = []

    for index, url in enumerate(month_plan.missing_urls, start=1):
        print(f"[TRANSLATE {index}/{len(month_plan.missing_urls)}] {url}")
        result = translator.process_one(en_url=url, output_dir=output_dir, model=model, overwrite=False)
        results.append(result)
        if result["status"] not in {"ok", "skipped_existing"}:
            raise RuntimeError(f"Échec de traduction pour {url}: {result.get('error', 'erreur inconnue')}")
        translated.append(Path(result["output"]).resolve())

    return TranslationOutcome(tuple(translated), tuple(results))


def write_github_outputs(values: dict[str, str]) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bitcoinops-repo",
        required=True,
        help="Clone local de bitcoinops/bitcoinops.github.io utilisé comme source de vérité",
    )
    parser.add_argument("--work-dir", default="output/monthly-workflow")
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--min-date", default=MONTHLY_MIN_DATE.isoformat())
    parser.add_argument("--month", default=None, help="Force un mois au format AAAA-MM")
    parser.add_argument(
        "--covered-slugs-file",
        type=Path,
        default=None,
        help="Fichier des newsletters déjà présentes dans des PR amont ouvertes",
    )
    return parser


def main() -> None:
    args = create_parser().parse_args()
    bitcoinops_repo = Path(args.bitcoinops_repo).resolve()
    if not (bitcoinops_repo / ".git").exists():
        raise RuntimeError(f"Le dossier bitcoinops-repo n'est pas un dépôt git: {bitcoinops_repo}")

    min_date = date.fromisoformat(args.min_date)
    urls = source_newsletter_urls(bitcoinops_repo, min_date)
    plans = build_month_plans(
        urls,
        existing_fr_slugs(bitcoinops_repo),
        read_covered_slugs(args.covered_slugs_file),
    )
    month_plan = pick_month(plans, args.month)
    if month_plan is None:
        message = (
            f"Le mois forcé {args.month} n'a aucune traduction manquante."
            if args.month
            else "Toutes les newsletters disponibles sont traduites ou déjà couvertes par une PR ouverte."
        )
        print(f"[INFO] {message}")
        write_github_outputs({"selected": "false"})
        return

    print(f"[SELECTED] {month_plan.month} ({len(month_plan.missing_urls)} newsletter(s) manquante(s))")
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    outcome = translate_missing_newsletters(month_plan, work_dir, args.model)

    manifest = {
        "month": month_plan.month,
        "min_date": min_date.isoformat(),
        "model": args.model,
        "source_urls": list(month_plan.missing_urls),
        "files": [path.name for path in outcome.translated_files],
    }
    manifest_path = work_dir / "monthly-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("[SUMMARY]")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    write_github_outputs(
        {
            "selected": "true",
            "month": month_plan.month,
            "file_count": str(len(outcome.translated_files)),
            "manifest": str(manifest_path),
        }
    )


if __name__ == "__main__":
    main()
