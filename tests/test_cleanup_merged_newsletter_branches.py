import unittest
from unittest.mock import patch

from scripts.cleanup_merged_newsletter_branches import (
    CleanupCandidate,
    branch_is_safe_to_delete,
    discover_candidates,
    flatten_pages,
    run_gh_api,
)


class CleanupMergedNewsletterBranchesTests(unittest.TestCase):
    def test_flattens_paginated_api_results(self):
        self.assertEqual(flatten_pages([[{"name": "a"}], [{"name": "b"}]]), [{"name": "a"}, {"name": "b"}])

    @patch("scripts.cleanup_merged_newsletter_branches.subprocess.run")
    def test_decodes_multiple_pages_without_gh_slurp(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = '[{"name":"a"}]\n[{"name":"b"}]\n'
        run.return_value.stderr = ""

        self.assertEqual(
            run_gh_api("repos/example/project/branches?per_page=100", paginate=True),
            [[{"name": "a"}], [{"name": "b"}]],
        )
        self.assertNotIn("--slurp", run.call_args.args[0])

    @patch("scripts.cleanup_merged_newsletter_branches.published_newsletter_files")
    @patch("scripts.cleanup_merged_newsletter_branches.branch_is_safe_to_delete", return_value=True)
    @patch("scripts.cleanup_merged_newsletter_branches.find_merged_upstream_pr")
    @patch("scripts.cleanup_merged_newsletter_branches.list_branches")
    def test_fork_cleanup_requires_a_merged_pr_and_published_file(self, branches, merged_pr, safe, files):
        branches.return_value = [
            "master",
            "Newsletter-421-translate-in-French",
            "Newsletter-422-translate-in-French",
        ]
        merged_pr.side_effect = [{"number": 2873, "head": {"sha": "abc"}}, None]
        files.return_value = ("_posts/fr/newsletters/2026-09-05-newsletter.md",)

        candidates, retained = discover_candidates(
            "Copinmalin/bitcoinops.github.io",
            "fork",
            "bitcoinops/bitcoinops.github.io",
            "Copinmalin",
        )

        self.assertEqual(
            candidates,
            [
                CleanupCandidate(
                    "Newsletter-421-translate-in-French",
                    "421",
                    2873,
                    ("_posts/fr/newsletters/2026-09-05-newsletter.md",),
                )
            ],
        )
        self.assertEqual(retained, ["Newsletter-422-translate-in-French"])

    @patch("scripts.cleanup_merged_newsletter_branches.published_newsletter_files")
    @patch("scripts.cleanup_merged_newsletter_branches.branch_is_safe_to_delete", return_value=True)
    @patch("scripts.cleanup_merged_newsletter_branches.find_merged_upstream_pr")
    @patch("scripts.cleanup_merged_newsletter_branches.list_branches")
    def test_review_cleanup_ignores_unrelated_branches(self, branches, merged_pr, safe, files):
        branches.return_value = [
            "main",
            "feat/weekly-newsletter-review",
            "review/newsletter-420-33242811788",
        ]
        merged_pr.return_value = {"number": 2864}
        files.return_value = ("_posts/fr/newsletters/2026-08-28-newsletter.md",)

        candidates, retained = discover_candidates(
            "Copinmalin/translate-optech-news",
            "review",
            "bitcoinops/bitcoinops.github.io",
            "Copinmalin",
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].branch, "review/newsletter-420-33242811788")
        self.assertEqual(retained, [])

    @patch("scripts.cleanup_merged_newsletter_branches.published_newsletter_files")
    @patch("scripts.cleanup_merged_newsletter_branches.branch_is_safe_to_delete", return_value=True)
    @patch("scripts.cleanup_merged_newsletter_branches.find_merged_upstream_pr")
    @patch("scripts.cleanup_merged_newsletter_branches.list_branches")
    def test_missing_master_file_retains_branch(self, branches, merged_pr, safe, files):
        branches.return_value = ["review/newsletter-421-33917758394"]
        merged_pr.return_value = {"number": 2873}
        files.return_value = ()

        candidates, retained = discover_candidates(
            "Copinmalin/translate-optech-news",
            "review",
            "bitcoinops/bitcoinops.github.io",
            "Copinmalin",
        )

        self.assertEqual(candidates, [])
        self.assertEqual(retained, ["review/newsletter-421-33917758394"])

    @patch("scripts.cleanup_merged_newsletter_branches.run_gh_api")
    def test_fork_branch_must_still_match_merged_pr_head(self, api):
        api.return_value = {"object": {"sha": "current"}}

        self.assertFalse(
            branch_is_safe_to_delete(
                "Copinmalin/bitcoinops.github.io",
                "fork",
                "Newsletter-421-translate-in-French",
                "bitcoinops/bitcoinops.github.io",
                {"head": {"sha": "merged-head"}},
                ("_posts/fr/newsletters/2026-09-04-newsletter.md",),
            )
        )

    @patch("scripts.cleanup_merged_newsletter_branches.run_gh_api")
    def test_review_branch_file_must_match_published_master_file(self, api):
        api.side_effect = [{"sha": "same-blob"}, {"sha": "same-blob"}]

        self.assertTrue(
            branch_is_safe_to_delete(
                "Copinmalin/translate-optech-news",
                "review",
                "review/newsletter-421-33917758394",
                "bitcoinops/bitcoinops.github.io",
                {"head": {"sha": "unused"}},
                ("_posts/fr/newsletters/2026-09-04-newsletter.md",),
            )
        )


if __name__ == "__main__":
    unittest.main()
