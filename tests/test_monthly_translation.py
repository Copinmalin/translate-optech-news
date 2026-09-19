import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.sync_monthly_translation_pr import (
    MONTHLY_MIN_DATE,
    build_month_plans,
    create_parser,
    pick_month,
    read_covered_slugs,
    source_newsletter_urls,
)
from scripts.validate_monthly_review import validate_batch


def url(day: str) -> str:
    return f"https://bitcoinops.org/en/newsletters/{day.replace('-', '/')}/"


class MonthlyTranslationTests(unittest.TestCase):
    def test_default_range_starts_with_the_first_optech_newsletter(self):
        args = create_parser().parse_args(["--bitcoinops-repo", "/tmp/bitcoinops"])
        self.assertEqual(args.min_date, MONTHLY_MIN_DATE.isoformat())
        self.assertEqual(args.min_date, "2018-06-08")

    def test_selects_oldest_incomplete_month_and_only_missing_files(self):
        urls = [url("2022-07-06"), url("2022-07-13"), url("2022-08-03")]
        plans = build_month_plans(urls, {"2022-07-06-newsletter"})

        self.assertEqual(pick_month(plans, None).month, "2022-07")
        self.assertEqual(pick_month(plans, None).missing_urls, (url("2022-07-13"),))

    def test_open_pull_request_files_are_excluded_before_month_selection(self):
        urls = [url("2022-07-06"), url("2022-08-03")]
        plans = build_month_plans(urls, set(), {"2022-07-06-newsletter"})

        self.assertEqual(pick_month(plans, None).month, "2022-08")

    def test_forced_complete_month_returns_none(self):
        plans = build_month_plans([url("2022-08-03")], set())
        self.assertIsNone(pick_month(plans, "2022-07"))

    def test_inventory_comes_from_checked_out_upstream_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            source = repo / "_posts/en/newsletters"
            source.mkdir(parents=True)
            (source / "2022-06-29-newsletter.md").touch()
            (source / "2022-07-06-newsletter.md").touch()
            (source / "README.md").touch()

            self.assertEqual(source_newsletter_urls(repo, date(2022, 7, 1)), [url("2022-07-06")])

    def test_covered_file_accepts_paths_or_filenames(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "covered.txt"
            path.write_text(
                "_posts/fr/newsletters/2022-07-06-newsletter.md\n2022-07-13-newsletter.md\n",
                encoding="utf-8",
            )
            self.assertEqual(
                read_covered_slugs(path),
                {"2022-07-06-newsletter", "2022-07-13-newsletter"},
            )

    def test_validates_multi_file_review_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory) / "review/months/2022-07"
            batch.mkdir(parents=True)
            files = ["2022-07-06-newsletter.md", "2022-07-13-newsletter.md"]
            for filename in files:
                (batch / filename).write_text(
                    "---\nlang: fr\npermalink: /fr/newsletters/2022/07/06/\n---\nTexte\n",
                    encoding="utf-8",
                )
            manifest = batch / "manifest.json"
            manifest.write_text(json.dumps({"month": "2022-07", "files": files}), encoding="utf-8")

            self.assertEqual(validate_batch(batch, manifest)["files"], files)


if __name__ == "__main__":
    unittest.main()
