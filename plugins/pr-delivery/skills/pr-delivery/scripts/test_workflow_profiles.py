"""Behavioral regression coverage for shared loop workflow profiles."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from loop_cleanup import workflow_state
from loop_cleanup.core import CleanupError
from loop_cleanup.git_inventory import InventoryError

SCRIPTS = Path(__file__).resolve().parent
LOOP_STATE = SCRIPTS / "loop_state.py"
WORKFLOWS = {
    "grade-loop": 2,
    "rationalize-loop": 2,
    "frontend-pr-loop": 2,
    "feature-validation-loop": 1,
    "implement-merge": None,
    "recursive-plan-review": None,
    "scaffold": None,
    "release": None,
}


class WorkflowProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = os.environ.copy()
        self.env["PR_DELIVERY_SKILL_DIR"] = str(SCRIPTS.parent)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git(self.repo, "init", "-b", "main")
        self.git(self.repo, "config", "user.name", "Workflow Profile Tests")
        self.git(self.repo, "config", "user.email", "workflow-tests@example.invalid")
        (self.repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        self.git(self.repo, "add", "tracked.txt")
        self.git(self.repo, "commit", "-m", "baseline")
        self.sha = self.git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def git(self, cwd, *args):
        return self.command(["git", *args], cwd=cwd)

    def command(self, args, cwd=None, ok=True):
        result = subprocess.run(args, cwd=cwd, env=self.env, text=True,
                                capture_output=True)
        if ok and result.returncode:
            self.fail(f"command failed: {args}\n{result.stdout}\n{result.stderr}")
        return result

    def init(self, workflow="implement-merge", budget_marker=...):
        path = self.root / f"{workflow}-{len(list(self.root.glob('*.json')))}.json"
        args = [sys.executable, str(LOOP_STATE), "init", "--path", str(path),
                "--run-id", f"test-{workflow}", "--repo-root", str(self.repo),
                "--target-branch", "main", "--current-sha", self.sha,
                "--workflow", workflow]
        if budget_marker is not ...:
            args.extend(["--max-passes", str(budget_marker)])
        self.command(args)
        return path

    def cli(self, path, *args, ok=True):
        return self.command([sys.executable, str(LOOP_STATE), *args, "--path", str(path)], ok=ok)

    def state(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def replace(self, path, mutate=None, ok=True):
        state = self.state(path)
        if mutate:
            mutate(state)
        candidate = self.root / "candidate.json"
        candidate.write_text(json.dumps(state), encoding="utf-8")
        return self.cli(path, "replace", "--candidate", str(candidate), ok=ok)

    def archive(self, path, kind="plan", contents="review artifact\n"):
        source = self.root / f"source-{len(self.state(path)['artifacts'])}.md"
        source.write_text(contents, encoding="utf-8")
        result = self.cli(path, "archive", "--source", str(source), "--kind", kind)
        return json.loads(result.stdout)

    def add_audit(self, path, outcome="clean", report_kind="plan", history=True, phase="initial", source_sha=None):
        report = self.archive(path, report_kind)
        history_artifacts = [self.archive(path, "history")] if history else []
        audit = {"iteration": self.state(path)["iteration"], "phase": phase,
                 "sourceSha": source_sha or self.sha, "report": report["archive"],
                 "history": [item["archive"] for item in history_artifacts],
                 "outcome": outcome,
                 "findings": [] if outcome == "clean" else ["follow-up needed"]}
        self.replace(path, lambda state: state["audits"].append(audit))
        return audit

    def make_settled(self, path, outcome="clean", report_kind="plan", history=True):
        audit = self.add_audit(path, outcome, report_kind, history)
        self.cli(path, "verify-cleanup")
        return audit

    def test_unlimited_profiles_reject_iteration_zero(self):
        path = self.init("implement-merge")
        state = self.state(path)
        state["iteration"] = 0
        with self.assertRaisesRegex(CleanupError, "invalid iteration"):
            workflow_state.validate(state)

    def test_delivery_stage_allows_merge_and_ci_updates_before_post_audit(self):
        path = self.init("grade-loop")
        self.add_audit(path, "actionable", "report", history=True)
        self.replace(path, lambda state: state.update(stage="planning"))
        self.replace(path, lambda state: state.update(stage="implementation"))
        self.replace(path, lambda state: state.update(stage="delivery"))
        delivery = {"url": "https://code.example.invalid/pr/1", "iteration": 1,
                    "state": "open", "mergeSha": None, "mergeVerified": False,
                    "targetCiSha": None, "targetCiVerified": False}
        self.replace(path, lambda state: state["deliveries"].append(delivery))

        self.git(self.repo, "commit", "--allow-empty", "-m", "merged change")
        merge_sha = self.git(self.repo, "rev-parse", "HEAD").stdout.strip()
        def record_merge(state):
            state["currentSha"] = merge_sha
            state["deliveries"][0].update(state="merged", mergeSha=merge_sha, mergeVerified=True)
        self.replace(path, record_merge)
        def record_ci(state):
            state["deliveries"][0].update(targetCiSha=merge_sha, targetCiVerified=True)
        self.replace(path, record_ci)
        self.assertTrue(self.state(path)["deliveries"][0]["targetCiVerified"])

        self.add_audit(path, "clean", "report", history=True, phase="post", source_sha=merge_sha)
        self.cli(path, "verify-cleanup")
        self.replace(path, lambda state: state.update(status="complete", stage="complete"))
        self.assertEqual("complete", self.state(path)["status"])

    def test_default_budget_for_every_profile(self):
        for workflow, expected in WORKFLOWS.items():
            with self.subTest(workflow=workflow):
                state = self.state(self.init(workflow))
                self.assertEqual(expected, state["maxPasses"])

    def test_grade_requires_report_and_nonempty_history_but_other_profiles_accept_plan_without_history(self):
        grade = self.state(self.init("grade-loop"))
        plan = {"source": str(self.root / "plan.md"), "archive": str(self.root / "plan-archive"),
                "sha256": "a" * 64, "iteration": 1, "kind": "plan"}
        report = dict(plan, kind="report")
        grade["artifacts"] = [report]
        audit = {"iteration": 1, "phase": "initial", "sourceSha": self.sha,
                 "report": report["archive"], "history": [], "outcome": "clean", "findings": []}
        grade["audits"] = [audit]
        with self.assertRaisesRegex(CleanupError, "grade audit requires archived history"):
            workflow_state.validate(grade)
        history = dict(plan, source=str(self.root / "history.md"),
                       archive=str(self.root / "history-archive"), kind="history")
        grade["artifacts"].append(history)
        audit["history"] = [history["archive"]]
        workflow_state.validate(grade)
        grade["artifacts"][0] = plan
        with self.assertRaisesRegex(CleanupError, "wrong/missing artifact"):
            workflow_state.validate(grade)

        general = self.state(self.init("implement-merge"))
        general["artifacts"] = [plan]
        general_audit = dict(audit, history=[])
        general["audits"] = [general_audit]
        workflow_state.validate(general)

    def test_non_grade_profiles_accept_report_plan_and_evidence_with_empty_history(self):
        for kind in ("report", "plan", "evidence"):
            with self.subTest(kind=kind):
                state = self.state(self.init("release"))
                artifact = {"source": str(self.root / f"{kind}.md"),
                            "archive": str(self.root / f"{kind}-archive"),
                            "sha256": "b" * 64, "iteration": 1, "kind": kind}
                state["artifacts"] = [artifact]
                state["audits"] = [{"iteration": 1, "phase": "initial", "sourceSha": self.sha,
                                    "report": artifact["archive"], "history": [],
                                    "outcome": "clean", "findings": []}]
                workflow_state.validate(state)

    def test_complete_and_deferred_outcomes_follow_clean_and_actionable_evidence(self):
        clean_path = self.init("implement-merge")
        self.make_settled(clean_path, "clean")
        self.replace(clean_path, lambda state: state.update(status="complete", stage="complete"))
        self.assertEqual("complete", self.state(clean_path)["status"])

        deferred_path = self.init("release")
        self.make_settled(deferred_path, "actionable", "evidence", history=False)
        self.replace(deferred_path, lambda state: state.update(
            status="deferred", stage="complete", reason="remaining work"))
        self.assertEqual("deferred", self.state(deferred_path)["status"])

    def test_blocked_run_can_resume_with_reason_cleared(self):
        path = self.init()
        self.replace(path, lambda state: state.update(status="blocked", reason="waiting for review"))
        self.replace(path, lambda state: state.update(status="active", reason=None))
        self.assertEqual(("active", None), (self.state(path)["status"], self.state(path)["reason"]))

    def test_unlimited_workflow_advances_but_finite_profile_rejects_budget_exhaustion(self):
        unlimited = self.init("implement-merge")
        self.add_audit(unlimited, "actionable")
        self.cli(unlimited, "verify-cleanup")
        self.replace(unlimited, lambda state: state.update(iteration=2))
        self.assertEqual(2, self.state(unlimited)["iteration"])

        finite = self.init("feature-validation-loop")
        self.add_audit(finite, "actionable")
        self.cli(finite, "verify-cleanup")
        result = self.replace(finite, lambda state: state.update(iteration=2), ok=False)
        self.assertIn("pass budget exceeded", result.stderr)
        self.assertEqual(1, self.state(finite)["iteration"])

    def test_non_grade_cleanup_rejects_target_drift_and_stale_inventory_receipt(self):
        path = self.init("release")
        state = self.state(path)
        self.git(self.repo, "commit", "--allow-empty", "-m", "target moved")
        with self.assertRaisesRegex(CleanupError, "target branch advanced"):
            workflow_state.verify_cleanup(state)

        self.git(self.repo, "reset", "--hard", self.sha)
        self.add_audit(path)
        self.cli(path, "verify-cleanup")
        self.git(self.repo, "branch", "late-resource")
        with self.assertRaisesRegex(InventoryError, "Git inventory differs from baseline"):
            workflow_state.verify_cleanup(self.state(path))

    def test_companion_repository_inventory_must_return_to_its_baseline(self):
        companion = self.root / "companion"
        companion.mkdir()
        self.git(companion, "init", "-b", "main")
        self.git(companion, "config", "user.name", "Workflow Profile Tests")
        self.git(companion, "config", "user.email", "workflow-tests@example.invalid")
        (companion / "tracked.txt").write_text("companion\n", encoding="utf-8")
        self.git(companion, "add", "tracked.txt")
        self.git(companion, "commit", "-m", "baseline")
        path = self.root / "with-companion.json"
        self.command([sys.executable, str(LOOP_STATE), "init", "--path", str(path),
                      "--run-id", "companion-test", "--repo-root", str(self.repo),
                      "--target-branch", "main", "--current-sha", self.sha,
                      "--workflow", "implement-merge", "--companion-repo", str(companion)])
        state = self.state(path)
        self.git(companion, "branch", "temporary-leak")
        with self.assertRaisesRegex(InventoryError, "Git inventory differs from baseline"):
            workflow_state.verify_inventories(state)
        self.git(companion, "branch", "-D", "temporary-leak")
        workflow_state.verify_inventories(state)

    def test_archive_and_state_paths_must_stay_outside_worktrees(self):
        worktree = self.root / "linked-worktree"
        self.git(self.repo, "worktree", "add", "-b", "linked", str(worktree))
        path = self.init("implement-merge")
        state = self.state(path)
        workflow_state.outside_worktrees(state, path)
        with self.assertRaisesRegex(CleanupError, "outside every worktree"):
            workflow_state.outside_worktrees(state, worktree / "durable.json")
        archive = self.archive(path, "evidence")
        archived_path = Path(archive["archive"]).resolve()
        self.assertNotIn(worktree.resolve(), archived_path.parents)

    def test_workflow_profile_is_immutable_and_missing_cli_profile_creates_no_ledger(self):
        path = self.init("implement-merge")
        candidate = self.state(path)
        candidate["workflow"] = "release"
        with self.assertRaisesRegex(CleanupError, "immutable workflow"):
            workflow_state.transition(self.state(path), candidate)

        missing = self.root / "missing-workflow.json"
        result = self.command([sys.executable, str(LOOP_STATE), "init", "--path", str(missing),
                               "--run-id", "missing-workflow", "--repo-root", str(self.repo),
                               "--target-branch", "main", "--current-sha", self.sha], ok=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("init requires --workflow", result.stderr)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
