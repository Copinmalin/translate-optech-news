#!/usr/bin/env python3
"""Fast-forward the fork master branch to Bitcoin Optech upstream master."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


UPSTREAM_URL = "https://github.com/bitcoinops/bitcoinops.github.io.git"


@dataclass(frozen=True)
class SyncResult:
    ahead_before: int
    behind_before: int
    master_sha: str


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sync_fork(repo: Path, upstream_url: str = UPSTREAM_URL) -> SyncResult:
    remotes = set(run_git(repo, "remote").splitlines())
    if "origin" not in remotes:
        raise RuntimeError("Remote origin introuvable dans le fork.")
    if "upstream" in remotes:
        run_git(repo, "remote", "set-url", "upstream", upstream_url)
    else:
        run_git(repo, "remote", "add", "upstream", upstream_url)

    run_git(repo, "fetch", "origin", "master")
    run_git(repo, "fetch", "upstream", "master")
    counts = run_git(repo, "rev-list", "--left-right", "--count", "origin/master...upstream/master")
    ahead, behind = (int(value) for value in counts.split())
    if ahead:
        raise RuntimeError(
            "Le master du fork contient "
            f"{ahead} commit(s) absent(s) de l'amont. Synchronisation automatique interrompue."
        )

    run_git(repo, "checkout", "master")
    run_git(repo, "merge", "--ff-only", "upstream/master")
    if behind:
        run_git(repo, "push", "origin", "master")
    run_git(repo, "fetch", "origin", "master")

    upstream_sha = run_git(repo, "rev-parse", "upstream/master")
    origin_sha = run_git(repo, "rev-parse", "origin/master")
    if origin_sha != upstream_sha:
        raise RuntimeError("Le master du fork ne correspond pas à upstream/master après synchronisation.")
    return SyncResult(ahead, behind, upstream_sha)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--upstream-url", default=UPSTREAM_URL)
    args = parser.parse_args()
    result = sync_fork(args.repo.resolve(), args.upstream_url)
    print(
        "SYNCED "
        f"ahead_before={result.ahead_before} "
        f"behind_before={result.behind_before} "
        f"master={result.master_sha}"
    )


if __name__ == "__main__":
    main()
