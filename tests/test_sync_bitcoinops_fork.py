import unittest
from pathlib import Path
from unittest.mock import call, patch

from scripts.sync_bitcoinops_fork import sync_fork


class SyncBitcoinOpsForkTests(unittest.TestCase):
    @patch("scripts.sync_bitcoinops_fork.run_git")
    def test_fast_forwards_and_pushes_a_behind_fork(self, git):
        git.side_effect = [
            "origin",
            "",
            "",
            "",
            "0 3",
            "",
            "",
            "",
            "",
            "abc123",
            "abc123",
        ]

        result = sync_fork(Path("/repo"))

        self.assertEqual(result.behind_before, 3)
        self.assertIn(call(Path("/repo"), "merge", "--ff-only", "upstream/master"), git.call_args_list)
        self.assertIn(call(Path("/repo"), "push", "origin", "master"), git.call_args_list)

    @patch("scripts.sync_bitcoinops_fork.run_git")
    def test_refuses_to_overwrite_unique_fork_commits(self, git):
        git.side_effect = ["origin\nupstream", "", "", "", "2 4"]

        with self.assertRaisesRegex(RuntimeError, "2 commit"):
            sync_fork(Path("/repo"))

        self.assertNotIn(call(Path("/repo"), "push", "origin", "master"), git.call_args_list)

    @patch("scripts.sync_bitcoinops_fork.run_git")
    def test_does_not_push_when_already_current(self, git):
        git.side_effect = [
            "origin\nupstream",
            "",
            "",
            "",
            "0 0",
            "",
            "",
            "",
            "abc123",
            "abc123",
        ]

        result = sync_fork(Path("/repo"))

        self.assertEqual(result.behind_before, 0)
        self.assertNotIn(call(Path("/repo"), "push", "origin", "master"), git.call_args_list)


if __name__ == "__main__":
    unittest.main()
