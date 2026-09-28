"""Behavioral tests for the read-only Git inventory helper."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("git_inventory.py")
SPEC = importlib.util.spec_from_file_location("git_inventory", SCRIPT)
assert SPEC and SPEC.loader
git_inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(git_inventory)


def command(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        args, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ).stdout.strip()


class GitInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.origin = self.base / "origin.git"
        command("git", "init", "--bare", str(self.origin))
        command("git", "init", "-b", "main", str(self.repo))
        command("git", "config", "user.name", "Inventory Test", cwd=self.repo)
        command("git", "config", "user.email", "inventory@example.invalid", cwd=self.repo)
        (self.repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
        command("git", "add", "tracked.txt", cwd=self.repo)
        command("git", "commit", "-m", "initial", cwd=self.repo)
        command("git", "remote", "add", "origin", str(self.origin), cwd=self.repo)
        command("git", "push", "-u", "origin", "main", cwd=self.repo)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def capture(self) -> dict:
        return git_inventory.capture(self.repo)

    def test_captures_branch_names_push_endpoint_and_worktree_assignments(self) -> None:
        command("git", "branch", "local-only", cwd=self.repo)
        command("git", "branch", "remote-only", cwd=self.repo)
        command("git", "push", "origin", "remote-only", cwd=self.repo)
        extra_push = self.base / "push.git"
        command("git", "init", "--bare", str(extra_push))
        command("git", "config", "--add", "remote.origin.pushurl", str(extra_push), cwd=self.repo)
        tree = self.base / "linked tree"
        command("git", "worktree", "add", "-b", "linked-branch", str(tree), "main", cwd=self.repo)

        inventory = self.capture()

        self.assertEqual(inventory["local_branches"], ["linked-branch", "local-only", "main", "remote-only"])
        self.assertEqual({remote["remote"] for remote in inventory["remote_branches"]}, {"origin"})
        self.assertEqual(len(inventory["remote_branches"]), 2)
        self.assertEqual(
            sorted(entry["branches"] for entry in inventory["remote_branches"]),
            [[], ["main", "remote-only"]],
        )
        self.assertTrue(all("https://" not in entry["endpoint"] for entry in inventory["remote_branches"]))
        self.assertIn(
            {"path": str(tree.resolve()), "branch": "linked-branch", "detached": False,
             "bare": False, "prunable": False, "exists": True},
            inventory["worktrees"],
        )

    def test_detects_leaked_local_and_remote_branches(self) -> None:
        baseline = self.capture()
        command("git", "branch", "leaked-local", cwd=self.repo)
        command("git", "push", "origin", "main:refs/heads/leaked-remote", cwd=self.repo)
        with self.assertRaises(git_inventory.InventoryError):
            git_inventory.verify(baseline)

    def test_repository_without_remotes_is_supported(self) -> None:
        command("git", "remote", "remove", "origin", cwd=self.repo)
        inventory = self.capture()
        self.assertEqual(inventory["remote_branches"], [])
        self.assertTrue(git_inventory.verify(inventory)["ok"])

    def test_relative_remote_url_resolves_from_repository_root(self) -> None:
        command("git", "remote", "set-url", "origin", "../origin.git", cwd=self.repo)
        inventory = self.capture()
        self.assertEqual(inventory["remote_branches"][0]["branches"], ["main"])

    def test_rejects_duplicate_remote_endpoint_and_worktree_entries(self) -> None:
        baseline = self.capture()
        duplicate_remote = dict(baseline)
        duplicate_remote["remote_branches"] = baseline["remote_branches"] * 2
        with self.assertRaises(git_inventory.InventoryError):
            git_inventory.validate_inventory(duplicate_remote)

        duplicate_worktree = dict(baseline)
        duplicate_worktree["worktrees"] = baseline["worktrees"] * 2
        with self.assertRaises(git_inventory.InventoryError):
            git_inventory.validate_inventory(duplicate_worktree)

    def test_detects_replaced_branch_even_when_branch_count_is_unchanged(self) -> None:
        command("git", "branch", "before", cwd=self.repo)
        baseline = self.capture()
        command("git", "branch", "-m", "before", "after", cwd=self.repo)
        with self.assertRaisesRegex(git_inventory.InventoryError, "local branches added"):
            git_inventory.verify(baseline)

    def test_ignores_head_advancement(self) -> None:
        baseline = self.capture()
        with (self.repo / "tracked.txt").open("a", encoding="utf-8") as stream:
            stream.write("advanced\n")
        command("git", "commit", "-am", "advance head", cwd=self.repo)
        result = git_inventory.verify(baseline)
        self.assertTrue(result["ok"])

    def test_remote_failure_fails_closed_without_exposing_endpoint(self) -> None:
        secret_endpoint = "https://user:secret@example.invalid/private.git"
        command("git", "remote", "set-url", "origin", secret_endpoint, cwd=self.repo)
        with self.assertRaises(git_inventory.InventoryError) as caught:
            self.capture()
        self.assertNotIn("secret", str(caught.exception))
        self.assertNotIn(secret_endpoint, str(caught.exception))

    def test_detects_missing_worktree_directory_and_preserves_dirty_worktree(self) -> None:
        tree = self.base / "linked"
        command("git", "worktree", "add", "-b", "linked", str(tree), "main", cwd=self.repo)
        baseline = self.capture()
        (tree / "untracked.txt").write_text("keep me", encoding="utf-8")
        self.assertTrue(git_inventory.verify(baseline)["ok"])
        self.assertTrue((tree / "untracked.txt").exists())
        (tree / "untracked.txt").unlink()
        shutil.rmtree(tree)
        with self.assertRaises(git_inventory.InventoryError):
            git_inventory.verify(baseline)

    def test_repeated_verification_is_idempotent_and_cli_round_trips(self) -> None:
        baseline = self.capture()
        self.assertEqual(git_inventory.verify(baseline), git_inventory.verify(baseline))
        baseline_file = self.base / "baseline.json"
        baseline_file.write_text(json.dumps(baseline), encoding="utf-8")
        cli = subprocess.run(
            ["python3", str(SCRIPT), "verify", "--baseline", str(baseline_file)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.assertTrue(json.loads(cli.stdout)["ok"])
        captured = subprocess.run(
            ["python3", str(SCRIPT), "capture", "--repo-root", str(self.repo)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.assertEqual(json.loads(captured.stdout), baseline)


if __name__ == "__main__":
    unittest.main()
