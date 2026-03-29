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
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

ARCHIVE_EN = "https://bitcoinops.org/en/newsletters/"
RAW_BASE = "https://raw.githubusercontent.com/bitcoinops/bitcoinops.github.io/master"
TIMEOUT = 30
DEFAULT_MIN_DATE = date(2022, 7, 1)
PREFERENCES_PATH = Path("preferences_fr.yaml")


def fetch(url: str) -> requests.Response:
    headers = {"User-Agent": "optech-fr-md/5.0 (+https://bitcoinops.org)"}
    resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
    resp.raise_for_status()
    return resp


def load_preferences() -> dict:
    if PREFERENCES_PATH.exists():
        return yaml.safe_load(PREFERENCES_PATH.read_text(encoding="utf-8")) or {}
    return {}


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


def slug_from_en_url(en_url: str) -> str:
    d = newsletter_date_from_url(en_url)
    return f"{d.isoformat()}-newsletter"


def upstream_raw_md_url(en_url: str, lang: str = "en") -> str:
    slug = slug_from_en_url(en_url)
    return f"{RAW_BASE}/_posts/{lang}/newsletters/{slug}.md"


def parse_front_matter(markdown_text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", markdown_text, re.DOTALL)
    if not m:
        raise RuntimeError("Front matter introuvable dans le Markdown source.")
    front_matter_raw = m.group(1)
    body = m.group(2)
    data = yaml.safe_load(front_matter_raw) or {}
    return data, body


def render_front_matter(data: dict) -> str:
    ordered_keys = ["title", "permalink", "name", "slug", "type", "layout", "lang"]
    lines = ["---"]
    for key in ordered_keys:
        if key in data:
            value = data[key]
            if isinstance(value, str):
                if key == "title":
                    lines.append(f"{key}: '{value}'")
                else:
                    lines.append(f"{key}: {value}")
            else:
                lines.append(f"{key}: {value}")
    for key, value in data.items():
        if key not in ordered_keys:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def translate_title(en_title: str) -> str:
    m = re.search(r"#(\d+)", en_title)
    if m:
        return f"Bulletin Hebdomadaire Bitcoin Optech #{m.group(1)}"
    title = en_title.replace("Bitcoin Optech Newsletter", "Bulletin Hebdomadaire Bitcoin Optech")
    title = title.replace("Year-in-Review Special", "Revue Spéciale Année")
    return title


def adapt_front_matter_for_fr(front_matter: dict) -> dict:
    data = dict(front_matter)
    if "title" in data and isinstance(data["title"], str):
        data["title"] = translate_title(data["title"])
    if "permalink" in data and isinstance(data["permalink"], str):
        data["permalink"] = data["permalink"].replace("/en/", "/fr/")
    if "name" in data and isinstance(data["name"], str) and not data["name"].endswith("-fr"):
        data["name"] = f"{data['name']}-fr"
    if "slug" in data and isinstance(data["slug"], str) and not data["slug"].endswith("-fr"):
        data["slug"] = f"{data['slug']}-fr"
    data["lang"] = "fr"
    return data


def translate_body_with_openai(body_markdown: str, source_url: str, model: str, preferences: dict) -> str:
    client = OpenAI()

    preferred_terms = preferences.get("preferred_terms", {})
    headings = preferences.get("headings", {})
    preferred_phrases = preferences.get("preferred_phrases", {})

    terms_block = "\n".join(f"- {k} -> {v}" for k, v in preferred_terms.items())
    headings_block = "\n".join(f"- {k} -> {v}" for k, v in headings.items())
    phrases_block = "\n".join(f"- {k}: {v}" for k, v in preferred_phrases.items())

    system_prompt = f"""Tu traduis des fichiers source Markdown/Jekyll de Bitcoin Optech de l'anglais vers le français.

Règles impératives :
- Retourne uniquement le corps Markdown, sans front matter YAML.
- Préserve strictement la structure Markdown d'origine.
- Préserve autant que possible les mêmes retours à la ligne, la même indentation et la même disposition visuelle que le Markdown source.
- Ne recompose pas librement les paragraphes.
- Ne modifie pas les clés des liens de référence, par exemple [topic covenants], [news194 silent payments], [Bitcoin Core #24836], etc.
- Ne modifie pas les URLs.
- Ne modifie pas les tags Liquid/Jekyll, par exemple {{% include references.md %}}.
- Ne modifie pas les noms de référence en bas du fichier.
- Conserve les backticks, emphases, listes, titres et ancres.
- Utilise préférentiellement le terme 'bulletin' plutôt que 'newsletter'.
- Respecte ces préférences lexicales et de titrage.

Termes préférés :
{terms_block}

Titres de sections préférés :
{headings_block}

Phrases standard préférées :
{phrases_block}

N'invente rien, ne résume rien, ne coupe rien.
"""

    user_prompt = f"""Source : {source_url}

Traduis ce corps Markdown en français en conservant la mise en page d'origine autant que possible :

{body_markdown}
"""

    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=user_prompt,
    )
    return response.output_text.strip() + "\n"


def normalize_headings(text: str, headings: dict) -> str:
    for en, fr in headings.items():
        text = re.sub(rf"^##\s+{re.escape(en)}\s*$", f"## {fr}", text, flags=re.MULTILINE)
    return text


def apply_preferred_replacements(text: str, preferences: dict) -> str:
    terms = preferences.get("preferred_terms", {})
    for src, dst in sorted(terms.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"\b{re.escape(src)}\b", dst, text, flags=re.IGNORECASE)
    text = normalize_headings(text, preferences.get("headings", {}))
    return text


def build_output_path(output_dir: Path, en_url: str) -> Path:
    slug = slug_from_en_url(en_url)
    target_dir = output_dir / "_posts" / "fr" / "newsletters"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{slug}.md"


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


def process_one(en_url: str, output_dir: Path, model: str, overwrite: bool = False) -> dict:
    preferences = load_preferences()
    result = {
        "url": en_url,
        "date": newsletter_date_from_url(en_url).isoformat(),
        "status": "unknown",
        "mode": "upstream_markdown_gpt_v5",
        "output": None,
        "source_markdown": upstream_raw_md_url(en_url, "en"),
        "error": None,
    }

    try:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY manquante pour la traduction GPT.")

        source_url = upstream_raw_md_url(en_url, "en")
        source_md = fetch(source_url).text
        front_matter, body = parse_front_matter(source_md)
        front_matter_fr = adapt_front_matter_for_fr(front_matter)
        translated_body = translate_body_with_openai(body, source_url, model, preferences)
        translated_body = apply_preferred_replacements(translated_body, preferences)

        final_markdown = render_front_matter(front_matter_fr) + "\n" + translated_body
        output_path = build_output_path(output_dir, en_url)

        if output_path.exists() and not overwrite:
            result["status"] = "skipped_existing"
            result["output"] = str(output_path)
            return result

        save_markdown(output_path, final_markdown)
        result["status"] = "ok"
        result["output"] = str(output_path)
        return result

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result


def run_batch(min_date: date, output_dir: Path, model: str, overwrite: bool, limit: int | None, pause: float, oldest_first: bool) -> None:
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
        result = process_one(en_url=url, output_dir=output_dir, model=model, overwrite=overwrite)
        results.append(result)

        if result["status"] == "ok":
            print(f"  -> OK {result['output']}")
        elif result["status"] == "skipped_existing":
            print(f"  -> SKIP {result['output']}")
        else:
            print(f"  -> ERROR {result['error']}")

        if pause > 0 and idx < len(urls):
            time.sleep(pause)

    report_path = output_dir / "batch-report.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

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

    parser = argparse.ArgumentParser(description="Traduit en français les newsletters Bitcoin Optech depuis le Markdown source du dépôt upstream en conservant au maximum la mise en page source.")
    parser.add_argument("target", help="'batch', 'latest' ou URL de newsletter Bitcoin Optech")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5.4"), help="Modèle OpenAI à utiliser")
    parser.add_argument("--output-dir", default="output", help="Dossier de sortie")
    parser.add_argument("--min-date", default=DEFAULT_MIN_DATE.isoformat(), help="Date minimale autorisée au format AAAA-MM-JJ")
    parser.add_argument("--limit", type=int, default=None, help="Nombre maximum de newsletters à traiter en batch")
    parser.add_argument("--pause", type=float, default=0.5, help="Pause entre deux newsletters en batch")
    parser.add_argument("--overwrite", action="store_true", help="Réécrit les fichiers déjà existants")
    parser.add_argument("--oldest-first", action="store_true", help="Traite du plus ancien au plus récent")
    args = parser.parse_args()

    min_date = date.fromisoformat(args.min_date)
    output_dir = Path(args.output_dir)

    if args.target.strip().lower() == "batch":
        run_batch(min_date=min_date, output_dir=output_dir, model=args.model, overwrite=args.overwrite, limit=args.limit, pause=args.pause, oldest_first=args.oldest_first)
        return

    target_url = normalize_target(args.target)
    assert_date_allowed(target_url, min_date)
    result = process_one(en_url=target_url, output_dir=output_dir, model=args.model, overwrite=args.overwrite)

    if result["status"] in {"ok", "skipped_existing"}:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        raise RuntimeError(result["error"])


if __name__ == "__main__":
    main()
