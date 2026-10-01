"""CLI contract tests for grade-loop's durable state and cleanup gates."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "run_state.py"
PROVIDER = SKILL_DIR.parents[2] / "pr-delivery" / "skills" / "pr-delivery"
if not (PROVIDER / "scripts" / "loop_cleanup" / "core.py").is_file():
    PROVIDER = Path.home() / ".codex" / "skills" / "pr-delivery"
SHA = "a" * 40


class GradeStateCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.state_dir = self.root / "durable"
        self.state_dir.mkdir()
        self.state_path = self.state_dir / "run.json"
        self.source_dir = self.root / "audit-sources"
        self.source_dir.mkdir()
        self.candidate_path = self.state_dir / "candidate.json"
        self.env = os.environ.copy()
        self.env.setdefault("PR_DELIVERY_SKILL_DIR", str(PROVIDER))
        self.init_repo(self.repo)
        self.init_state()

    def tearDown(self):
        self.temp.cleanup()

    def init_repo(self, path):
        path.mkdir(parents=True, exist_ok=True)
        self.git(path, "init", "-b", "main")
        self.git(path, "config", "user.name", "Grade State Tests")
        self.git(path, "config", "user.email", "grade-state-tests@example.invalid")
        (path / "README.md").write_text("fixture\n", encoding="utf-8")
        self.git(path, "add", "README.md")
        self.git(path, "commit", "-m", "fixture")

    @staticmethod
    def git(repo, *args):
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True
        )
        if result.returncode:
            raise AssertionError(f"git {args!r} failed: {result.stderr}")
        return result.stdout.strip()

    def cli(self, *args, env=None, ok=True):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            env=env or self.env,
        )
        if ok and result.returncode != 0:
            self.fail(f"CLI {args!r} failed ({result.returncode}): {result.stderr}")
        if not ok and result.returncode == 0:
            self.fail(f"CLI {args!r} unexpectedly succeeded: {result.stdout}")
        return result

    def init_state(self, max_passes=2):
        self.cli(
            "init", "--path", self.state_path, "--run-id", "grade-test-run-01",
            "--repo-root", self.repo, "--target-branch", "main", "--current-sha",
            self.git(self.repo, "rev-parse", "HEAD"), "--max-passes", str(max_passes),
        )

    def add_origin_and_reinitialize(self):
        remote = self.root / "origin.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        self.git(self.repo, "remote", "add", "origin", str(remote))
        self.git(self.repo, "push", "origin", "main")
        self.state_path.unlink()
        self.init_state()
        return remote

    def state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def replace(self, mutate=None, ok=True, expected=None):
        state = self.state()
        candidate = copy.deepcopy(state)
        if mutate:
            mutate(candidate)
        self.candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
        result = self.cli(
            "replace", "--path", self.state_path, "--candidate", self.candidate_path,
            ok=ok,
        )
        if expected:
            self.assertIn(expected, result.stderr)
        return result

    def archive_audit(self, phase="initial", outcome="clean", iteration=None, source_root=None):
        state = self.state()
        iteration = iteration or state["iteration"]
        source_root = Path(source_root) if source_root else self.source_dir
        report = source_root / f"report-{iteration}-{phase}.md"
        history = source_root / f"history-{iteration}-{phase}.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        history.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(f"grade report {iteration} {phase}\n", encoding="utf-8")
        history.write_text(f'{{"pass": {iteration}, "phase": "{phase}"}}\n', encoding="utf-8")
        report_out = self.cli("archive", "--path", self.state_path, "--source", report, "--kind", "report")
        history_out = self.cli("archive", "--path", self.state_path, "--source", history, "--kind", "history")
        report_archive = json.loads(report_out.stdout)["archive"]
        history_archive = json.loads(history_out.stdout)["archive"]

        def add_audit(candidate):
            findings = [] if outcome == "clean" else ["actionable finding"]
            candidate["audits"].append({
                "iteration": iteration,
                "phase": phase,
                "sourceSha": candidate["currentSha"],
                "report": report_archive,
                "history": [history_archive],
                "outcome": outcome,
                "findings": findings,
            })

        self.replace(add_audit)
        return Path(report_archive), Path(history_archive)

    def verify_artifacts(self, ok=True, expected=None):
        result = self.cli("verify-artifacts", "--path", self.state_path, ok=ok)
        if expected:
            self.assertIn(expected, result.stderr)
        return result

    def reserve_resource(self, kind, identifier, remote=None):
        self.replace(lambda state: state["resources"].append({
            "repoRoot": str(self.repo.resolve()),
            "kind": kind,
            "identifier": str(identifier),
            "owner": self.state()["runId"],
            "status": "active",
            "iteration": self.state()["iteration"],
            "remote": remote,
        }))

    def mark_resources_cleaned(self):
        self.replace(lambda state: [resource.update(status="cleaned") for resource in state["resources"]])

    def test_initial_clean_exit_archives_survive_audit_worktree_removal(self):
        branch = "codex/grade-audit"
        worktree = self.root / "audit-worktree"
        self.reserve_resource("local-branch", branch)
        self.reserve_resource("worktree", worktree)
        self.git(self.repo, "worktree", "add", "-b", branch, str(worktree), "main")
        report_root = worktree / "docs" / "plans"
        report_archive, history_archive = self.archive_audit(source_root=report_root)
        self.assertTrue(report_archive.is_file())
        self.assertTrue(history_archive.is_file())
        self.assertNotEqual(report_archive.parent, worktree)
        self.verify_artifacts()
        report_source = report_root / "report-1-initial.md"
        history_source = report_root / "history-1-initial.json"
        report_source.unlink()
        history_source.unlink()
        self.verify_artifacts()
        self.assertFalse(report_source.exists())
        self.assertFalse(history_source.exists())
        self.git(self.repo, "worktree", "remove", str(worktree))
        self.git(self.repo, "branch", "-D", branch)
        self.mark_resources_cleaned()
        self.cli("verify-cleanup", "--path", self.state_path)
        self.cli("verify-cleanup", "--path", self.state_path)
        self.assertEqual(len(self.state()["cleanup"]["checks"]), 1)
        self.replace(lambda state: state.update(status="complete", stage="complete"))
        self.cli("validate", "--path", self.state_path)
        self.assertTrue(report_archive.read_text(encoding="utf-8").startswith("grade report"))
        self.assertTrue(history_archive.read_text(encoding="utf-8").startswith("{"))

    def test_deferred_exit_requires_clean_gate_and_reason(self):
        self.archive_audit(outcome="actionable")
        self.replace(
            lambda state: state.update(status="deferred", stage="complete", reason="budget exhausted"),
            ok=False,
            expected="missing final cleanup check",
        )
        self.cli("verify-cleanup", "--path", self.state_path)
        self.replace(lambda state: state.update(status="deferred", stage="complete", reason="budget exhausted"))
        self.assertEqual(self.state()["status"], "deferred")

    def test_pass_advance_requires_cleanup_and_budget_two_rejects_three(self):
        self.archive_audit(outcome="actionable")
        self.replace(lambda state: state.update(iteration=2), ok=False, expected="missing earlier cleanup check")
        self.cli("verify-cleanup", "--path", self.state_path)
        self.replace(lambda state: state.update(iteration=2))
        self.assertEqual(self.state()["iteration"], 2)
        self.replace(lambda state: state.update(iteration=3), ok=False, expected="pass budget exceeded")
        self.archive_audit(outcome="actionable")
        self.replace(
            lambda state: state.update(status="deferred", stage="complete", reason="budget exhausted"),
            ok=False,
            expected="missing final cleanup check",
        )
        self.cli("verify-cleanup", "--path", self.state_path)
        self.replace(lambda state: state.update(status="deferred", stage="complete", reason="budget exhausted"))
        self.assertEqual(self.state()["iteration"], 2)
        self.assertEqual(self.state()["status"], "deferred")

    def test_owned_branch_leak_after_receipt_blocks_terminal_exit_but_collaborators_do_not(self):
        self.archive_audit()
        self.cli("verify-cleanup", "--path", self.state_path)
        # After the receipt: a collaborator's branch appears, and a branch this
        # run reserved is recorded cleaned but left behind.
        self.git(self.repo, "branch", "collaborator-branch")
        self.reserve_resource("local-branch", "leaked-after-receipt")
        self.git(self.repo, "branch", "leaked-after-receipt")
        self.mark_resources_cleaned()
        self.replace(
            lambda state: state.update(status="complete", stage="complete"),
            ok=False,
            expected="owned resources remain: local-branch leaked-after-receipt",
        )
        self.git(self.repo, "branch", "-D", "leaked-after-receipt")
        self.cli("verify-cleanup", "--path", self.state_path)
        self.replace(lambda state: state.update(status="complete", stage="complete"))
        self.assertEqual(self.state()["status"], "complete")

    def test_remote_branch_leak_blocks_cleanup(self):
        remote = self.root / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        self.git(self.repo, "remote", "add", "origin", str(remote))
        self.git(self.repo, "push", "origin", "main")
        # Reinitialize so the baseline includes this configured remote.
        self.state_path.unlink()
        self.init_state()
        self.assertEqual(self.state()["targetRemote"], "origin")
        name = "codex/remote-leak"
        self.reserve_resource("remote-branch", name, remote="origin")
        self.git(self.repo, "branch", name, "main")
        self.git(self.repo, "push", "origin", f"{name}:{name}")
        self.mark_resources_cleaned()
        self.archive_audit()
        self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertIn("remote-branch codex/remote-leak", self.cli("verify-cleanup", "--path", self.state_path, ok=False).stderr)

    def test_baseline_and_resource_ownership_are_immutable(self):
        baseline = copy.deepcopy(self.state()["cleanup"]["baselines"])
        baseline[0]["local_branches"] = []
        self.replace(lambda state: state["cleanup"].update(baselines=baseline), ok=False, expected="cleanup baselines are immutable")
        bad_resource = {
            "repoRoot": str(self.repo.resolve()), "kind": "local-branch",
            "identifier": "foreign-branch", "owner": "someone-else", "status": "active",
            "iteration": 1, "remote": None,
        }
        self.replace(lambda state: state["resources"].append(bad_resource), ok=False, expected="resource owner must equal runId")

    def test_corrupt_archive_blocks_cleanup(self):
        report, _ = self.archive_audit()
        report.write_text("tampered\n", encoding="utf-8")
        result = self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertIn("hash mismatch", result.stderr)

    def test_missing_archive_blocks_cleanup(self):
        report, _ = self.archive_audit()
        report.unlink()
        result = self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertIn("unreadable", result.stderr)

    def test_changed_source_since_archive_blocks_artifact_verification(self):
        self.archive_audit()
        source = Path(self.state()["artifacts"][1]["source"])
        source.write_text("changed after archive\n", encoding="utf-8")
        self.verify_artifacts(ok=False, expected="source changed since archive")

    def test_history_archive_corruption_blocks_cleanup(self):
        _, history = self.archive_audit()
        history.write_text("changed archive\n", encoding="utf-8")
        result = self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertIn("hash mismatch", result.stderr)

    def test_history_archive_missing_blocks_cleanup(self):
        _, history = self.archive_audit()
        history.unlink()
        result = self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertIn("unreadable", result.stderr)

    def test_target_remote_advance_blocks_cleanup_and_completion(self):
        remote = self.add_origin_and_reinitialize()
        self.assertEqual(self.state()["targetRemote"], "origin")
        baseline = self.state()["cleanup"]["baselines"][0]
        baseline_local_branches = baseline["local_branches"]
        baseline_remote_branches = baseline["remote_branches"][0]["branches"]
        self.archive_audit()
        self.cli("verify-cleanup", "--path", self.state_path)
        (self.repo / "README.md").write_text("target advanced\n", encoding="utf-8")
        self.git(self.repo, "add", "README.md")
        self.git(self.repo, "commit", "-m", "advance target")
        self.git(self.repo, "push", "origin", "main")
        local_names = self.git(
            self.repo, "for-each-ref", "--format=%(refname:strip=2)", "refs/heads"
        ).splitlines()
        self.assertEqual(local_names, baseline_local_branches)
        remote_names = subprocess.run(
            ["git", "--git-dir", str(remote), "for-each-ref", "--format=%(refname:strip=2)", "refs/heads"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip().splitlines()
        self.assertEqual(remote_names, baseline_remote_branches)
        self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.replace(
            lambda state: state.update(stage="planning"),
            ok=False,
            expected="target branch advanced",
        )
        self.replace(
            lambda state: state.update(status="complete", stage="complete"),
            ok=False,
            expected="target branch advanced",
        )

    def test_blocked_run_requires_reason_remains_resumable_and_can_retain_resource(self):
        branch = "codex/preserved-work"
        self.reserve_resource("local-branch", branch)
        self.git(self.repo, "branch", branch, "main")
        self.replace(
            lambda state: state.update(status="blocked", stage="audit", reason=None),
            ok=False,
            expected="blocker reason must be nonempty",
        )
        self.replace(
            lambda state: state.update(status="blocked", stage="complete", reason="investigation needed"),
            ok=False,
            expected="blocked runs remain resumable",
        )
        self.replace(lambda state: state.update(status="blocked", stage="audit", reason="investigation needed"))
        self.assertEqual(self.state()["resources"][0]["status"], "active")
        self.replace(lambda state: state.update(status="active", stage="audit", reason=None))
        self.git(self.repo, "branch", "-D", branch)
        self.mark_resources_cleaned()
        self.archive_audit()
        self.cli("verify-cleanup", "--path", self.state_path)

    def test_no_remote_target_tracks_local_target_tip(self):
        self.assertIsNone(self.state()["targetRemote"])
        self.archive_audit()
        self.cli("verify-cleanup", "--path", self.state_path)
        (self.repo / "README.md").write_text("local target advanced\n", encoding="utf-8")
        self.git(self.repo, "add", "README.md")
        self.git(self.repo, "commit", "-m", "advance local target")
        new_sha = self.git(self.repo, "rev-parse", "HEAD")
        self.replace(
            lambda state: state.update(stage="planning", currentSha=new_sha),
            ok=False,
            expected="planning audit evidence is stale",
        )
        self.replace(
            lambda state: state.update(stage="planning"),
            ok=False,
            expected="target branch advanced",
        )
        self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertIn("target branch advanced", self.replace(
            lambda state: state.update(status="complete", stage="complete"),
            ok=False,
        ).stderr)

    def test_unchanged_target_allows_pass_two_planning_from_preserved_audit(self):
        self.archive_audit(outcome="actionable")
        self.cli("verify-cleanup", "--path", self.state_path)
        self.replace(lambda state: state.update(iteration=2))
        self.assertEqual(len(self.state()["audits"]), 1)
        self.replace(lambda state: state.update(stage="planning"))
        self.assertEqual(self.state()["stage"], "planning")
        self.assertEqual(len(self.state()["audits"]), 1)

    def test_merged_delivery_pending_ci_then_exact_green_post_audit_completes(self):
        self.archive_audit(outcome="actionable")
        delivery = {
            "url": "https://forge.example/pr/2", "iteration": 1, "state": "open",
            "mergeSha": None, "mergeVerified": False, "targetCiSha": None,
            "targetCiVerified": False,
        }
        self.replace(lambda state: state.update(stage="planning"))
        self.replace(lambda state: state.update(stage="implementation"))
        self.replace(lambda state: state.update(stage="delivery", deliveries=[delivery]))

        (self.repo / "README.md").write_text("merged target\n", encoding="utf-8")
        self.git(self.repo, "add", "README.md")
        self.git(self.repo, "commit", "-m", "merged remediation")
        merge_sha = self.git(self.repo, "rev-parse", "HEAD")
        merged_pending_ci = {
            **delivery, "state": "merged", "mergeSha": merge_sha,
            "mergeVerified": True,
        }
        self.replace(lambda state: state.update(
            currentSha=merge_sha, stage="post-audit", deliveries=[merged_pending_ci]
        ))
        self.cli("verify-cleanup", "--path", self.state_path, ok=False)
        self.assertIn("delivery lacks verified merge/exact target CI", self.cli(
            "verify-cleanup", "--path", self.state_path, ok=False
        ).stderr)

        exact_green = {**merged_pending_ci, "targetCiSha": merge_sha, "targetCiVerified": True}
        self.replace(lambda state: state.update(deliveries=[exact_green]))
        self.archive_audit(phase="post", outcome="clean")
        self.replace(lambda state: state.update(stage="cleanup"))
        self.cli("verify-cleanup", "--path", self.state_path)
        self.replace(lambda state: state.update(status="complete", stage="complete"))
        self.cli("validate", "--path", self.state_path)
        self.assertEqual(self.state()["audits"][-1]["phase"], "post")

    def test_merged_delivery_without_post_audit_cannot_be_deferred(self):
        self.archive_audit(outcome="actionable")
        delivery = {
            "url": "https://forge.example/pr/1", "iteration": 1, "state": "open",
            "mergeSha": None, "mergeVerified": False, "targetCiSha": None,
            "targetCiVerified": False,
        }
        self.replace(lambda state: state["deliveries"].append(delivery))
        merged = {**delivery, "state": "merged", "mergeSha": SHA, "mergeVerified": True,
                  "targetCiSha": SHA, "targetCiVerified": True}
        self.replace(lambda state: state["deliveries"].__setitem__(0, merged))
        self.replace(lambda state: state.update(stage="planning"), ok=False,
                     expected="reuse requires a post-delivery audit")
        self.replace(
            lambda state: state.update(status="deferred", stage="complete", reason="remaining finding"),
            ok=False,
            expected="delivered pass requires a post-delivery audit",
        )

    def test_implementation_cannot_skip_actionable_planning(self):
        self.archive_audit()
        self.replace(lambda state: state.update(stage="implementation"), ok=False,
                     expected="enter planning before implementation")
        self.replace(lambda state: state.update(stage="planning"), ok=False,
                     expected="planning requires actionable findings")
        self.archive_audit(outcome="actionable")
        self.replace(lambda state: state.update(stage="planning"))
        self.replace(lambda state: state.update(stage="implementation"))

    def test_missing_legacy_baseline_is_rejected(self):
        state = self.state()
        state["cleanup"]["baselines"] = []
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        result = self.cli("validate", "--path", self.state_path, ok=False)
        self.assertIn("cleanup baseline is required", result.stderr)

    def test_missing_provider_fails_closed_before_state_creation(self):
        env = self.env.copy()
        env["PR_DELIVERY_SKILL_DIR"] = str(self.root / "missing-provider")
        new_state = self.state_dir / "must-not-exist.json"
        result = self.cli(
            "init", "--path", new_state, "--run-id", "grade-test-run-02",
            "--repo-root", self.repo, "--target-branch", "main", "--current-sha",
            self.git(self.repo, "rev-parse", "HEAD"), env=env, ok=False,
        )
        self.assertIn("shared cleanup provider", result.stderr)
        self.assertFalse(new_state.exists())


if __name__ == "__main__":
    unittest.main()
