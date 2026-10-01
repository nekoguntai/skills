"""Regression tests for cleanup baselines and run-state iteration gates."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
RUN_STATE = SCRIPTS / "run_state.py"


class CleanupStateCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git(self.repo, "init", "-b", "main")
        self.git(self.repo, "config", "user.email", "test@example.invalid")
        self.git(self.repo, "config", "user.name", "Cleanup Test")
        (self.repo / "tracked.txt").write_text("baseline\n")
        self.git(self.repo, "add", "tracked.txt")
        self.git(self.repo, "commit", "-m", "baseline")
        self.sha = self.git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.state_path = self.root / "run.json"
        self.init_state()

    def git(self, cwd, *args):
        return self.command(["git", *args], cwd=cwd)

    def command(self, args, cwd=None, ok=True):
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
        if ok and result.returncode:
            self.fail(f"command failed: {args}\nstdout: {result.stdout}\nstderr: {result.stderr}")
        return result

    def cli(self, *args, ok=True):
        return self.command([sys.executable, str(RUN_STATE), *map(str, args)], ok=ok)

    def init_state(self, companions=()):
        args = ["init", "--path", self.state_path, "--run-id", "cleanup-test",
                "--repo-root", self.repo, "--target-branch", "main", "--scope", "test",
                "--baseline-sha", self.sha]
        for companion in companions:
            args.extend(["--companion-repo", str(companion)])
        return self.cli(*args)

    def read_state(self):
        return json.loads(self.state_path.read_text())

    def write_state(self, state, name="candidate.json"):
        path = self.root / name
        path.write_text(json.dumps(state, indent=2) + "\n")
        return path

    def replace_with(self, state, ok=True):
        candidate = self.write_state(state)
        return self.cli("replace", "--path", self.state_path, "--candidate", candidate, ok=ok)

    def add_dirty_resource(self, kind, identifier, remote=None):
        state = self.read_state()
        state["resources"].append({"repoRoot": str(self.repo), "kind": kind,
            "identifier": str(identifier), "owner": state["runId"], "status": "cleaned",
            "iteration": 1, "remote": remote})
        self.write_state(state)
        return state

    def test_init_captures_immutable_primary_and_companion_baselines(self):
        companion = self.root / "companion"
        companion.mkdir()
        self.git(companion, "init", "-b", "main")
        self.git(companion, "config", "user.email", "test@example.invalid")
        self.git(companion, "config", "user.name", "Cleanup Test")
        (companion / "tracked.txt").write_text("companion\n")
        self.git(companion, "add", "tracked.txt")
        self.git(companion, "commit", "-m", "baseline")
        self.state_path.unlink()
        self.init_state([companion])
        state = self.read_state()
        baselines = state["cleanup"]["baselines"]
        self.assertEqual({str(self.repo), str(companion)}, {item["root"] for item in baselines})
        original = json.loads(json.dumps(baselines))
        state["cleanup"]["baselines"][0]["common_git_dir"] = str(self.root / "other.git")
        result = self.replace_with(state, ok=False)
        self.assertIn("baselines are immutable", result.stderr)
        self.assertEqual(original, self.read_state()["cleanup"]["baselines"])

    def test_iteration_zero_verifies_then_advances_to_iteration_one(self):
        self.cli("verify-cleanup", "--path", self.state_path)
        state = self.read_state()
        self.assertEqual([0], [item["iteration"] for item in state["cleanup"]["checks"]])
        state["iteration"] = 1
        self.replace_with(state)
        self.assertEqual(1, self.read_state()["iteration"])

    def test_squash_rewrite_keeps_inventory_valid_without_sha_ancestry(self):
        original = self.sha
        self.git(self.repo, "checkout", "--orphan", "squash-fixture")
        self.git(self.repo, "commit", "--allow-empty", "-m", "squashed history")
        squashed_sha = self.git(self.repo, "rev-parse", "HEAD").stdout.strip()
        self.assertNotEqual(original, squashed_sha)
        self.git(self.repo, "checkout", "main")
        self.git(self.repo, "reset", "--hard", "squash-fixture")
        self.git(self.repo, "branch", "-D", "squash-fixture")
        self.cli("verify-cleanup", "--path", self.state_path)

    def test_resource_reservation_creation_cleanup_and_boundary_gate(self):
        self.cli("verify-cleanup", "--path", self.state_path)
        state = self.read_state()
        state["iteration"] = 1
        self.replace_with(state)

        branch = "loop-owned"
        state = self.read_state()
        state["resources"].append({"repoRoot": str(self.repo), "kind": "local-branch",
            "identifier": branch, "owner": "cleanup-test", "status": "active",
            "iteration": 1, "remote": None})
        self.replace_with(state)
        self.git(self.repo, "branch", branch)

        state = self.read_state()
        state["resources"][0]["status"] = "cleaned"
        self.replace_with(state)
        blocked = self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertNotEqual(0, blocked.returncode)
        self.assertEqual("cleaned", self.read_state()["resources"][0]["status"])
        self.assertEqual([0], [item["iteration"] for item in self.read_state()["cleanup"]["checks"]])

        # Remove the test-owned branch, record a fresh live receipt, then cross
        # the iteration boundary successfully.
        self.git(self.repo, "branch", "-D", branch)
        self.cli("verify-cleanup", "--path", self.state_path)
        state = self.read_state()
        self.assertEqual([0, 1], [item["iteration"] for item in state["cleanup"]["checks"]])
        state["iteration"] = 2
        self.replace_with(state)
        self.assertEqual(2, self.read_state()["iteration"])

    def test_complete_transition_checks_live_inventory_after_prior_receipt(self):
        self.cli("verify-cleanup", "--path", self.state_path)
        state = self.read_state()
        state["iteration"] = 1
        self.replace_with(state)
        self.cli("verify-cleanup", "--path", self.state_path)

        # The receipt is valid when written. A branch this run reserved, recorded
        # cleaned, but left behind must still block completion despite that
        # receipt; a collaborator's unreserved branch does not.
        self.git(self.repo, "branch", "collaborator-branch")
        state = self.read_state()
        state["resources"].append({"repoRoot": str(self.repo), "kind": "local-branch",
            "identifier": "late-leak", "owner": "cleanup-test", "status": "active",
            "iteration": 1, "remote": None})
        self.replace_with(state)
        self.git(self.repo, "branch", "late-leak")
        state = self.read_state()
        state["resources"][-1]["status"] = "cleaned"
        self.replace_with(state)
        complete = self.read_state()
        complete["status"] = "complete"
        complete["stage"] = "complete"
        complete["containersRunningAtCloseout"] = False
        complete["coveragePasses"] = [{
            "iteration": 1,
            "sha": complete["currentSha"],
            "kind": "initial",
            "complete": True,
            "acceptedFindingIds": [],
            "acceptedFindingSeverities": {},
            "blockingFindingIds": [],
            "domains": [{"name": name, "status": "excluded", "paths": [],
                         "evidence": [], "reason": "not applicable to this fixture"}
                        for name in sorted({
                            "trust-boundaries", "persistence", "api-contracts", "async-lifecycle",
                            "frontend-state", "error-handling", "tests-ci", "recent-changes",
                        })],
            "gaps": [],
        }]
        complete["deployments"] = [{
            "operationId": "cleanup-test-deploy", "commit": complete["currentSha"],
            "policy": "final", "status": "skipped", "attemptedAt": "2026-09-28T00:00:00Z",
            "completedAt": "2026-09-28T00:00:00Z", "healthVerified": False,
            "readinessVerified": False, "details": "fixture does not deploy",
        }]
        result = self.replace_with(complete, ok=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("owned resources remain: local-branch late-leak", result.stderr)
        self.assertEqual("active", self.read_state()["status"])
        self.git(self.repo, "branch", "-d", "late-leak")
        self.replace_with(complete)
        self.assertEqual("complete", self.read_state()["status"])

    def test_baseline_resources_cannot_be_claimed_as_loop_owned(self):
        state = self.read_state()
        state["resources"].append({"repoRoot": str(self.repo), "kind": "local-branch",
            "identifier": "main", "owner": "cleanup-test", "status": "active",
            "iteration": 1, "remote": None})
        state["iteration"] = 1
        result = self.replace_with(state, ok=False)
        self.assertIn("cannot claim a baseline resource", result.stderr)

    def test_live_gate_reports_unreserved_and_rejects_owned_local_remote_and_worktree(self):
        cases = ("local", "remote", "worktree")
        for case in cases:
            with self.subTest(resource=case):
                self.temp.cleanup()
                self.setUp()
                if case == "local":
                    self.git(self.repo, "branch", "loop-added")
                elif case == "remote":
                    bare = self.root / "origin.git"
                    self.command(["git", "init", "--bare", str(bare)])
                    self.git(self.repo, "remote", "add", "origin", str(bare))
                    # Re-capture with the configured empty remote so only the
                    # newly pushed branch differs from the baseline.
                    self.state_path.unlink()
                    self.init_state()
                    self.git(self.repo, "push", "-u", "origin", "main")
                else:
                    worktree = self.root / "extra-worktree"
                    self.git(self.repo, "worktree", "add", "-b", "loop-wt", str(worktree))
                state = self.read_state()
                state["cleanup"]["checks"].append({"iteration": 0, "verifiedAt": "stale",
                    "repositories": [str(self.repo)]})
                self.state_path.write_text(json.dumps(state))
                # Unreserved, the new resource is a collaborator's: reported only.
                reported = self.cli("verify-cleanup", "--path", self.state_path)
                self.assertIn("collaborator change", reported.stdout)
                # Recorded as this run's (claimed cleaned), it must block the gate.
                state = self.read_state()
                kind, identifier, remote = {
                    "local": ("local-branch", "loop-added", None),
                    "remote": ("remote-branch", "main", "origin"),
                    "worktree": ("worktree", str((self.root / "extra-worktree").resolve()), None),
                }[case]
                state["resources"].append({"repoRoot": str(self.repo), "kind": kind, "identifier": identifier,
                    "owner": "cleanup-test", "status": "cleaned", "iteration": 1, "remote": remote})
                state["iteration"] = 1
                self.state_path.write_text(json.dumps(state))
                checks_before = state["cleanup"]["checks"]
                revision_before = state["revision"]
                result = self.cli("verify-cleanup", "--path", self.state_path, ok=False)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("owned resources remain", result.stderr)
                after = self.read_state()
                self.assertEqual(checks_before, after["cleanup"]["checks"])
                self.assertEqual(revision_before, after["revision"])

    def test_dirty_owned_resource_stays_active_when_cleanup_is_blocked(self):
        branch = "loop-owned"
        self.git(self.repo, "branch", branch)
        state = self.read_state()
        state["resources"].append({"repoRoot": str(self.repo), "kind": "local-branch",
            "identifier": branch, "owner": "cleanup-test", "status": "active",
            "iteration": 1, "remote": None})
        # Iteration 1 owns this resource; the branch remains present and must not be
        # marked cleaned merely to satisfy the receipt gate.
        state["iteration"] = 1
        self.state_path.write_text(json.dumps(state))
        result = self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertNotEqual(0, result.returncode)
        after = self.read_state()
        self.assertEqual("active", after["resources"][0]["status"])
        self.assertEqual([], after["cleanup"]["checks"])
        self.assertIn(branch, self.git(self.repo, "branch", "--format=%(refname:short)").stdout)

    def test_repeated_verification_is_idempotent_and_resume_keeps_receipt(self):
        self.cli("verify-cleanup", "--path", self.state_path)
        first = self.read_state()
        self.cli("verify-cleanup", "--path", self.state_path)
        second = self.read_state()
        self.assertEqual(first["revision"], second["revision"])
        self.assertEqual(first["cleanup"]["checks"], second["cleanup"]["checks"])
        # A second process invocation models resuming the same run from disk.
        self.assertEqual(0, second["iteration"])
        self.assertEqual([str(self.repo)], second["cleanup"]["checks"][0]["repositories"])

    def test_legacy_v1_state_is_readable_but_cannot_be_mutated(self):
        state = self.read_state()
        state.pop("cleanup")
        state["schemaVersion"] = 1
        for resource in state["resources"]:
            for field in ("repoRoot", "iteration", "remote"):
                resource.pop(field, None)
        self.state_path.write_text(json.dumps(state))
        valid = self.cli("validate", "--path", self.state_path)
        self.assertEqual(0, valid.returncode)
        result = self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertIn("legacy state", result.stderr)
        state["stage"] = "scrub"
        result = self.replace_with(state, ok=False)
        self.assertIn("legacy state is read-only", result.stderr)


if __name__ == "__main__":
    unittest.main()
