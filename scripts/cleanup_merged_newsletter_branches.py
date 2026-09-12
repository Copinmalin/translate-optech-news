#!/usr/bin/env python3
"""Supprime les branches de newsletter dont la PR amont est fusionnée et publiée."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from urllib.parse import quote


FORK_BRANCH_RE = re.compile(r"^Newsletter-(?P<number>\d+)-translate-in-French$")
REVIEW_BRANCH_RE = re.compile(r"^review/newsletter-(?P<number>\d+)-\d+$")
NEWSLETTER_FILE_RE = re.compile(r"^_posts/fr/newsletters/\d{4}-\d{2}-\d{2}-newsletter\.md$")


@dataclass(frozen=True)
class CleanupCandidate:
    branch: str
    newsletter_number: str
    upstream_pr: int
    published_files: tuple[str, ...]


def run_gh_api(endpoint: str, *, method: str = "GET", paginate: bool = False) -> object:
    command = ["gh", "api"]
    if method != "GET":
        command.extend(["--method", method])
    if paginate:
        command.append("--paginate")
    command.append(endpoint)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Échec de gh api pour {endpoint}: {result.stderr.strip()}")
    if method == "DELETE":
        return None
    if not paginate:
        return json.loads(result.stdout)

    decoder = json.JSONDecoder()
    pages = []
    position = 0
    while position < len(result.stdout):
        while position < len(result.stdout) and result.stdout[position].isspace():
            position += 1
        if position >= len(result.stdout):
            break
        page, position = decoder.raw_decode(result.stdout, position)
        pages.append(page)
    return pages


def flatten_pages(payload: object) -> list[dict]:
    if not isinstance(payload, list):
        raise RuntimeError("Réponse GitHub paginée inattendue")
    if payload and isinstance(payload[0], list):
        return [item for page in payload for item in page]
    return payload


def list_branches(repository: str) -> list[str]:
    pages = run_gh_api(f"repos/{repository}/branches?per_page=100", paginate=True)
    return [item["name"] for item in flatten_pages(pages)]


def find_merged_upstream_pr(upstream_repo: str, owner: str, newsletter_number: str) -> dict | None:
    branch = f"Newsletter-{newsletter_number}-translate-in-French"
    endpoint = (
        f"repos/{upstream_repo}/pulls?state=all&base=master"
        f"&head={owner}:{branch}&per_page=100"
    )
    pulls = run_gh_api(endpoint)
    merged = [pull for pull in pulls if pull.get("merged_at")]
    if not merged:
        return None
    return max(merged, key=lambda pull: pull["number"])


def published_newsletter_files(upstream_repo: str, pull_number: int) -> tuple[str, ...]:
    pages = run_gh_api(
        f"repos/{upstream_repo}/pulls/{pull_number}/files?per_page=100",
        paginate=True,
    )
    paths = tuple(
        item["filename"]
        for item in flatten_pages(pages)
        if NEWSLETTER_FILE_RE.fullmatch(item["filename"])
    )
    for path in paths:
        encoded_path = quote(path, safe="/")
        run_gh_api(f"repos/{upstream_repo}/contents/{encoded_path}?ref=master")
    return paths


def branch_is_safe_to_delete(
    target_repo: str,
    branch_kind: str,
    branch: str,
    upstream_repo: str,
    pull: dict,
    published_files: tuple[str, ...],
) -> bool:
    encoded_branch = quote(branch, safe="")
    if branch_kind == "fork":
        ref = run_gh_api(f"repos/{target_repo}/git/refs/heads/{encoded_branch}")
        return ref["object"]["sha"] == pull["head"]["sha"]

    for published_path in published_files:
        filename = published_path.rsplit("/", 1)[-1]
        review_path = quote(f"review/newsletters/{filename}", safe="/")
        review_file = run_gh_api(
            f"repos/{target_repo}/contents/{review_path}?ref={encoded_branch}"
        )
        published_file = run_gh_api(
            f"repos/{upstream_repo}/contents/{quote(published_path, safe='/')}?ref=master"
        )
        if review_file["sha"] != published_file["sha"]:
            return False
    return True


def discover_candidates(
    target_repo: str,
    branch_kind: str,
    upstream_repo: str,
    owner: str,
) -> tuple[list[CleanupCandidate], list[str]]:
    pattern = FORK_BRANCH_RE if branch_kind == "fork" else REVIEW_BRANCH_RE
    candidates: list[CleanupCandidate] = []
    retained: list[str] = []

    for branch in sorted(list_branches(target_repo)):
        match = pattern.fullmatch(branch)
        if not match:
            continue
        number = match.group("number")
        pull = find_merged_upstream_pr(upstream_repo, owner, number)
        if pull is None:
            retained.append(branch)
            continue
        files = published_newsletter_files(upstream_repo, pull["number"])
        if not files:
            retained.append(branch)
            continue
        if not branch_is_safe_to_delete(
            target_repo,
            branch_kind,
            branch,
            upstream_repo,
            pull,
            files,
        ):
            retained.append(branch)
            continue
        candidates.append(CleanupCandidate(branch, number, pull["number"], files))

    return candidates, retained


def delete_branch(repository: str, branch: str) -> None:
    encoded_branch = quote(branch, safe="")
    run_gh_api(f"repos/{repository}/git/refs/heads/{encoded_branch}", method="DELETE")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--branch-kind", choices=("fork", "review"), required=True)
    parser.add_argument("--upstream-repo", default="bitcoinops/bitcoinops.github.io")
    parser.add_argument("--owner", default="Copinmalin")
    parser.add_argument("--execute", action="store_true")
    return parser


def main() -> None:
    args = create_parser().parse_args()
    candidates, retained = discover_candidates(
        target_repo=args.target_repo,
        branch_kind=args.branch_kind,
        upstream_repo=args.upstream_repo,
        owner=args.owner,
    )

    for branch in retained:
        print(f"KEEP {args.target_repo}:{branch} (PR amont non fusionnée ou publication absente de master)")

    action = "DELETE" if args.execute else "WOULD_DELETE"
    for candidate in candidates:
        files = ", ".join(candidate.published_files)
        print(
            f"{action} {args.target_repo}:{candidate.branch} "
            f"(PR amont #{candidate.upstream_pr}, publié: {files})"
        )
        if args.execute:
            delete_branch(args.target_repo, candidate.branch)

    print(f"SUMMARY candidates={len(candidates)} retained={len(retained)} execute={args.execute}")


if __name__ == "__main__":
    main()
