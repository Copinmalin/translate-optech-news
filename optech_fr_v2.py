#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from markdownify import markdownify as md
from openai import OpenAI

ARCHIVE_EN = "https://bitcoinops.org/en/newsletters/"
TIMEOUT = 30
DEFAULT_MIN_DATE = date(2022, 7, 1)


def fetch(url: str) -> requests.Response:
    headers = {
        "User-Agent": "optech-fr-batch/2.0 (+https://bitcoinops.org)"
    }
    resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
    resp.raise_for_status()
    return resp


def newsletter_date_from_url(url: str) -> date:
    m = re.search(r"/newsletters/(\d{4})/(\d{2})/(\d{2})/?$", url)
    if not m:
        raise ValueError(f"Impossible d'extraire la date depuis l'URL : {url}")
    year, month, day = map(int, m.groups())
    return date(year, month, day)


def assert_date_allowed(url: str, min_date: date) -> None:
    newsletter_date = newsletter_date_from_url(url)
    if newsletter_date < min_date:
        raise RuntimeError(
            f"Newsletter trop ancienne : {newsletter_date.isoformat()} "
            f"(limite actuelle : {min_date.isoformat()})"
        )


def resolve_latest_newsletter_url() -> str:
    urls = collect_archive_newsletter_urls(date(2010, 1, 1))
    if not urls:
        raise RuntimeError("Aucune newsletter trouvée dans l'archive.")
    return urls[-1]


def normalize_target(target: str) -> str:
    if target.strip().lower() == "latest":
        return resolve_latest_newsletter_url()
    if target.startswith("http://") or target.startswith("https://"):
        return target
    raise ValueError("La cible doit être 'latest', 'batch' ou une URL complète.")


def to_fr_url(en_url: str) -> str:
    return en_url.replace("/en/newsletters/", "/fr/newsletters/")


def extract_article_markdown(html: str, base_url: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find("article") or soup.body
    if main is None:
        raise RuntimeError("Impossible de localiser le contenu principal.")

    for tag in main.select("script, style, form, input, nav, aside"):
        tag.decompose()

    for a in main.find_all("a", href=True):
        a["href"] = urljoin(base_url, a["href"])

    h1 = main.find("h1")
    if not h1:
        raise RuntimeError("Impossible de trouver le titre de l'article.")

    title = h1.get_text(" ", strip=True)
    markdown = md(str(main), heading_style="ATX")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return title, markdown


def looks_like_valid_fr_newsletter(final_url: str, html: str) -> bool:
    if "/fr/newsletters/" not in final_url:
        return False
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if h1 is None:
        return False
    title = h1.get_text(" ", strip=True)
    return ("Bulletin" in title) or ("Revue" in title)


def translate_with_openai(article_title: str, source_markdown: str, source_url: str, model: str) -> str:
    client = OpenAI()

    system_prompt = """Tu traduis des newsletters techniques Bitcoin de l'anglais vers le français.

Règles :
- Retourne uniquement du Markdown.
- Préserve le sens technique exact.
- Conserve les liens, les listes, les titres et les blocs de code.
- N'invente rien, ne résume rien, ne coupe rien.
- Garde les termes standard de l'écosystème quand ils sont plus naturels en anglais
  (ex: mempool, Lightning, covenant, watchtower, package relay, cluster mempool).
- Pour les acronymes techniques (UTXO, PSBT, DLC, HTLC, LN), ne les traduis pas.
- Style : français professionnel, clair, naturel, sans ton marketing.
"""

    user_prompt = f"""Source : {source_url}
Titre : {article_title}

Traduis ce Markdown en français :

{source_markdown}
"""

    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=user_prompt,
    )
    return response.output_text.strip()


def slug_from_title(title: str) -> str:
    m = re.search(r"#(\d+)", title)
    if m:
        return f"optech-{m.group(1)}-fr"
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", title.lower()).strip("-")
    return safe[:80] or "optech-fr"


def build_output_path(output_dir: Path, source_url: str, title: str) -> Path:
    d = newsletter_date_from_url(source_url)
    year_dir = output_dir / str(d.year)
    year_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{d.isoformat()}-{slug_from_title(title)}"
    return year_dir / f"{stem}.md"


def save_markdown(output_path: Path, content: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def collect_archive_newsletter_urls(min_date: date) -> list[str]:
    resp = fetch(ARCHIVE_EN)
    soup = BeautifulSoup(resp.text, "html.parser")

    urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"^/en/newsletters/\d{4}/\d{2}/\d{2}/?$", href):
            abs_url = urljoin(resp.url, href)
            try:
                d = newsletter_date_from_url(abs_url)
            except ValueError:
                continue
            if d >= min_date:
                urls.add(abs_url)

    return sorted(urls, key=newsletter_date_from_url)


def process_one(
    en_url: str,
    output_dir: Path,
    model: str,
    force_gpt: bool = False,
    overwrite: bool = False,
) -> dict:
    result = {
        "url": en_url,
        "date": newsletter_date_from_url(en_url).isoformat(),
        "status": "unknown",
        "mode": None,
        "output": None,
        "error": None,
    }

    try:
        if not force_gpt:
            fr_url = to_fr_url(en_url)
            try:
                fr_resp = fetch(fr_url)
                if looks_like_valid_fr_newsletter(fr_resp.url, fr_resp.text):
                    title, source_markdown = extract_article_markdown(fr_resp.text, fr_resp.url)
                    output_path = build_output_path(output_dir, en_url, title)

                    if output_path.exists() and not overwrite:
                        result["status"] = "skipped_existing"
                        result["mode"] = "native_fr"
                        result["output"] = str(output_path)
                        return result

                    save_markdown(output_path, source_markdown)

                    result["status"] = "ok"
                    result["mode"] = "native_fr"
                    result["output"] = str(output_path)
                    return result
            except Exception:
                pass

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY manquante pour la traduction GPT.")

        en_resp = fetch(en_url)
        title, source_markdown = extract_article_markdown(en_resp.text, en_resp.url)
        output_path = build_output_path(output_dir, en_url, title)

        if output_path.exists() and not overwrite:
            result["status"] = "skipped_existing"
            result["mode"] = "gpt"
            result["output"] = str(output_path)
            return result

        markdown = translate_with_openai(title, source_markdown, en_resp.url, model)
        save_markdown(output_path, markdown)

        result["status"] = "ok"
        result["mode"] = "gpt"
        result["output"] = str(output_path)
        return result

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result


def run_batch(
    min_date: date,
    output_dir: Path,
    model: str,
    force_gpt: bool,
    overwrite: bool,
    limit: int | None,
    pause: float,
    oldest_first: bool,
) -> None:
    urls = collect_archive_newsletter_urls(min_date)

    if not oldest_first:
        urls = list(reversed(urls))

    if limit is not None:
        urls = urls[:limit]

    if not urls:
        print("[INFO] Aucune newsletter à traiter.")
        return

    print(f"[INFO] {len(urls)} newsletters à traiter")

    results = []
    for idx, url in enumerate(urls, start=1):
        print(f"[{idx}/{len(urls)}] {url}")
        result = process_one(
            en_url=url,
            output_dir=output_dir,
            model=model,
            force_gpt=force_gpt,
            overwrite=overwrite,
        )
        results.append(result)

        status = result["status"]
        mode = result["mode"]
        out = result["output"]
        err = result["error"]

        if status == "ok":
            print(f"  -> OK [{mode}] {out}")
        elif status == "skipped_existing":
            print(f"  -> SKIP [{mode}] {out}")
        else:
            print(f"  -> ERROR {err}")

        if pause > 0 and idx < len(urls):
            time.sleep(pause)

    report_path = output_dir / "batch-report.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ok_count = sum(1 for r in results if r["status"] == "ok")
    skip_count = sum(1 for r in results if r["status"] == "skipped_existing")
    err_count = sum(1 for r in results if r["status"] == "error")

    print()
    print(f"[DONE] OK={ok_count} SKIP={skip_count} ERROR={err_count}")
    print(f"[REPORT] {report_path}")

    if err_count > 0:
        raise RuntimeError(f"Batch terminé avec {err_count} erreur(s).")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Récupère ou traduit en français les newsletters Bitcoin Optech."
    )
    parser.add_argument(
        "target",
        help="'batch', 'latest' ou URL de newsletter Bitcoin Optech"
    )
    parser.add_argument(
        "--force-gpt",
        action="store_true",
        help="Ignore la version FR native et force la traduction GPT"
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-5.4"),
        help="Modèle OpenAI à utiliser"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Dossier de sortie"
    )
    parser.add_argument(
        "--min-date",
        default=DEFAULT_MIN_DATE.isoformat(),
        help="Date minimale autorisée au format AAAA-MM-JJ"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre maximum de newsletters à traiter en batch"
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.5,
        help="Pause entre deux newsletters en batch"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Réécrit les fichiers déjà existants"
    )
    parser.add_argument(
        "--oldest-first",
        action="store_true",
        help="Traite du plus ancien au plus récent"
    )

    args = parser.parse_args()

    min_date = date.fromisoformat(args.min_date)
    output_dir = Path(args.output_dir)

    if args.target.strip().lower() == "batch":
        run_batch(
            min_date=min_date,
            output_dir=output_dir,
            model=args.model,
            force_gpt=args.force_gpt,
            overwrite=args.overwrite,
            limit=args.limit,
            pause=args.pause,
            oldest_first=args.oldest_first,
        )
        return

    target_url = normalize_target(args.target)
    assert_date_allowed(target_url, min_date)

    if "/fr/newsletters/" in target_url:
        en_url = target_url.replace("/fr/newsletters/", "/en/newsletters/")
    else:
        en_url = target_url

    result = process_one(
        en_url=en_url,
        output_dir=output_dir,
        model=args.model,
        force_gpt=args.force_gpt,
        overwrite=args.overwrite,
    )

    if result["status"] in {"ok", "skipped_existing"}:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        raise RuntimeError(result["error"])


if __name__ == "__main__":
    main()
