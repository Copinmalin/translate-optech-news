#!/usr/bin/env python3
"""Traduit le plus ancien mois incomplet et prépare la PR vers bitcoinops.github.io."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import optech_fr


@dataclass
class MonthPlan:
    month: str
    urls: list[str]
    missing_urls: list[str]


@dataclass
class TranslationOutcome:
    translated_files: list[Path]
    results: list[dict]


def run_git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True)
    return proc.stdout.strip()


def existing_fr_slugs(bitcoinops_repo: Path) -> set[str]:
    fr_dir = bitcoinops_repo / "_posts" / "fr" / "newsletters"
    if not fr_dir.exists():
        return set()
    return {p.stem for p in fr_dir.glob("*.md")}


def month_from_url(url: str) -> str:
    d = optech_fr.newsletter_date_from_url(url)
    return f"{d.year:04d}-{d.month:02d}"


def build_month_plans(min_date: date, fr_slugs: set[str]) -> list[MonthPlan]:
    urls = optech_fr.collect_archive_newsletter_urls(min_date)

    per_month: dict[str, list[str]] = defaultdict(list)
    for url in urls:
        per_month[month_from_url(url)].append(url)

    plans: list[MonthPlan] = []
    for month in sorted(per_month.keys()):
        month_urls = sorted(per_month[month], key=optech_fr.newsletter_date_from_url)
        missing = [u for u in month_urls if optech_fr.slug_from_en_url(u) not in fr_slugs]
        if missing:
            plans.append(MonthPlan(month=month, urls=month_urls, missing_urls=missing))

    return plans


def translate_missing_newsletters(month_plan: MonthPlan, output_dir: Path, model: str) -> TranslationOutcome:
    translated: list[Path] = []
    results: list[dict] = []

    for idx, url in enumerate(month_plan.missing_urls, start=1):
        print(f"[TRANSLATE {idx}/{len(month_plan.missing_urls)}] {url}")
        result = optech_fr.process_one(en_url=url, output_dir=output_dir, model=model, overwrite=False)
        results.append(result)
        if result["status"] != "ok":
            raise RuntimeError(f"Échec de traduction pour {url}: {result.get('error', 'erreur inconnue')}")
        translated.append(Path(result["output"]).resolve())

    return TranslationOutcome(translated_files=translated, results=results)


def copy_into_bitcoinops(bitcoinops_repo: Path, translated_files: list[Path]) -> list[Path]:
    target_dir = bitcoinops_repo / "_posts" / "fr" / "newsletters"
    target_dir.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for src in translated_files:
        dst = target_dir / src.name
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def commit_for_month(bitcoinops_repo: Path, month: str, copied_files: list[Path], branch_prefix: str) -> tuple[str, str]:
    title = f"Newsletter {month.replace('-', '.')} translate in French"
    unique_suffix = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    branch = f"{branch_prefix}{month}-{unique_suffix}"

    run_git(bitcoinops_repo, "checkout", "-b", branch)
    run_git(bitcoinops_repo, "add", *[str(path.relative_to(bitcoinops_repo)) for path in copied_files])
    run_git(bitcoinops_repo, "commit", "-m", title)
    return title, branch


def create_pr_with_gh(bitcoinops_repo: Path, title: str, repo_slug: str, body: str) -> None:
    subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo_slug,
            "--title",
            title,
            "--body",
            body,
        ],
        cwd=bitcoinops_repo,
        check=True,
        text=True,
    )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Sélectionne automatiquement le plus ancien mois incomplet, "
            "traduit les newsletters manquantes et prépare la PR bitcoinops.github.io."
        )
    )
    parser.add_argument("--bitcoinops-repo", required=True, help="Chemin local du clone bitcoinops.github.io")
    parser.add_argument("--work-dir", default="output/monthly-workflow", help="Dossier de travail pour les traductions")
    parser.add_argument("--model", default="gpt-5.4", help="Modèle OpenAI utilisé par optech_fr.py")
    parser.add_argument(
        "--min-date",
        default=optech_fr.DEFAULT_MIN_DATE.isoformat(),
        help="Date minimale des newsletters à considérer (AAAA-MM-JJ)",
    )
    parser.add_argument("--branch-prefix", default="fr-newsletter-", help="Préfixe de branche pour la PR")
    parser.add_argument("--repo-slug", default="Copinmalin/bitcoinops.github.io", help="Repo GitHub cible pour gh pr create")
    parser.add_argument(
        "--month",
        default=None,
        help="Force un mois (AAAA-MM). Sinon, sélection automatique du plus ancien mois incomplet.",
    )
    parser.add_argument("--print-gh-pr", action="store_true", help="Affiche la commande gh pr create suggérée")
    parser.add_argument("--create-pr", action="store_true", help="Crée la PR automatiquement via gh")
    return parser


def pick_month(plan_list: list[MonthPlan], forced_month: str | None) -> MonthPlan:
    if forced_month is None:
        return plan_list[0]
    for plan in plan_list:
        if plan.month == forced_month:
            return plan
    raise RuntimeError(f"Le mois forcé {forced_month} n'a aucune traduction manquante dans la plage sélectionnée.")


def main() -> None:
    args = create_parser().parse_args()
    bitcoinops_repo = Path(args.bitcoinops_repo).resolve()
    if not (bitcoinops_repo / ".git").exists():
        raise RuntimeError(f"Le dossier bitcoinops-repo n'est pas un dépôt git: {bitcoinops_repo}")

    min_date = date.fromisoformat(args.min_date)
    fr_slugs = existing_fr_slugs(bitcoinops_repo)
    month_plans = build_month_plans(min_date=min_date, fr_slugs=fr_slugs)
    if not month_plans:
        print("[INFO] Tous les mois disponibles sont déjà traduits dans la plage demandée.")
        return

    month_plan = pick_month(month_plans, args.month)
    print(f"[SELECTED] {month_plan.month} ({len(month_plan.missing_urls)} newsletter(s) manquante(s))")

    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    translated = translate_missing_newsletters(month_plan=month_plan, output_dir=work_dir, model=args.model)

    copied = copy_into_bitcoinops(bitcoinops_repo=bitcoinops_repo, translated_files=translated.translated_files)
    title, branch = commit_for_month(
        bitcoinops_repo=bitcoinops_repo,
        month=month_plan.month,
        copied_files=copied,
        branch_prefix=args.branch_prefix,
    )

    summary = {
        "selected_month": month_plan.month,
        "missing_count": len(month_plan.missing_urls),
        "translated_files": [str(p) for p in translated.translated_files],
        "copied_files": [str(p.relative_to(bitcoinops_repo)) for p in copied],
        "branch": branch,
        "title": title,
    }
    print("[SUMMARY]")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    body = "Monthly French newsletter translation batch."

    if args.create_pr:
        create_pr_with_gh(bitcoinops_repo=bitcoinops_repo, title=title, repo_slug=args.repo_slug, body=body)
        print("[PR] Créée via gh pr create")
    elif args.print_gh_pr:
        print("[PR-CMD]")
        print(
            "gh pr create "
            f"--repo {args.repo_slug} "
            f"--title \"{title}\" "
            f"--body \"{body}\""
        )


if __name__ == "__main__":
    main()
