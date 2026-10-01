"""Shared state contracts and transitions for loop workflows."""
import hashlib
import re
from pathlib import Path

from .core import (
    CleanupError, need, resource_key, validate_baselines, validate_check,
    validate_owned_resource, validate_resource_transition, verify_inventories,
)

from .target import verify_target

SHA = re.compile(r"[0-9a-f]{40}")
STATUSES = {"active", "blocked", "complete", "deferred"}
STAGES = {"audit", "planning", "implementation", "delivery", "post-audit", "cleanup", "complete"}
WORKFLOWS = {"grade-loop", "rationalize-loop", "frontend-pr-loop", "visual-consistency-loop", "feature-validation-loop",
             "implement-merge", "recursive-plan-review", "scaffold", "release"}
DEFAULT_BUDGETS = {"grade-loop": 2, "rationalize-loop": 2, "frontend-pr-loop": 2,
                   "visual-consistency-loop": None, "feature-validation-loop": 1, "implement-merge": None,
                   "recursive-plan-review": None, "scaffold": None, "release": None}
PLANNING_WORKFLOWS = {"grade-loop", "rationalize-loop", "frontend-pr-loop", "visual-consistency-loop"}
FIELDS = {"workflow", "schemaVersion", "revision", "runId", "repoRoot", "targetBranch", "targetRemote", "currentSha",
          "iteration", "maxPasses", "status", "stage", "reason", "cleanup", "resources",
          "artifacts", "audits", "deliveries"}


def fields(value, expected, label):
    need(isinstance(value, dict) and set(value) == expected, f"invalid {label} fields")


def text(value, label):
    need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty")


def sha(value):
    need(isinstance(value, str) and bool(SHA.fullmatch(value)), "invalid full commit SHA")


def absolute(value):
    text(value, "path")
    need(Path(value).is_absolute(), "path must be absolute")


def validate(state):
    validate_identity(state)
    validate_lifecycle(state)
    validate_cleanup(state)
    baseline = next(b for b in state["cleanup"]["baselines"] if b["root"] == state["repoRoot"])
    remotes = {remote["remote"] for remote in baseline["remote_branches"]}
    need(state["targetRemote"] in remotes if remotes else state["targetRemote"] is None,
         "target remote must match baseline")
    validate_artifacts(state)
    validate_audits(state)
    validate_deliveries(state)
    if state["status"] in {"complete", "deferred"}:
        terminal(state)
    return state


def validate_identity(state):
    fields(state, FIELDS, "state")
    need(state["workflow"] in WORKFLOWS, "invalid workflow")
    need(type(state["schemaVersion"]) is int and state["schemaVersion"] == 1, "unsupported schema")
    need(type(state["revision"]) is int and state["revision"] >= 0, "invalid revision")
    need(type(state["iteration"]) is int and state["iteration"] >= 1, "invalid iteration")
    budget = state["maxPasses"]
    need(budget is None or type(budget) is int and budget > 0, "invalid maxPasses")
    need(budget is None or state["iteration"] <= budget, "pass budget exceeded")
    text(state["runId"], "runId")
    need(bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{5,79}", state["runId"])), "invalid runId")
    absolute(state["repoRoot"])
    text(state["targetBranch"], "targetBranch")
    sha(state["currentSha"])
    need(state["targetRemote"] is None or isinstance(state["targetRemote"], str), "invalid targetRemote")


def validate_lifecycle(state):
    need(state["status"] in STATUSES and state["stage"] in STAGES, "invalid status/stage")
    need(state["reason"] is None or isinstance(state["reason"], str), "invalid reason")
    for name in ("resources", "artifacts", "audits", "deliveries"):
        need(isinstance(state[name], list), f"{name} must be an array")
    if state["status"] == "active":
        need(state["stage"] != "complete", "active run cannot have complete stage")
    if state["status"] == "blocked":
        text(state["reason"], "blocker reason")
        need(state["stage"] != "complete", "blocked runs remain resumable at their current stage")


def validate_cleanup(state):
    fields(state["cleanup"], {"baselines", "checks"}, "cleanup")
    baselines = validate_baselines(state)
    for item in state["resources"]:
        fields(item, {"repoRoot", "kind", "identifier", "owner", "status", "iteration", "remote"}, "resource")
        for name in ("repoRoot", "kind", "identifier", "owner"):
            text(item[name], name)
        need(item["status"] in {"active", "cleaned", "preserved"}, "invalid resource status")
        need(item["remote"] is None or isinstance(item["remote"], str), "invalid remote")
        validate_owned_resource(state, item, baselines)
    keys = [resource_key(item) for item in state["resources"]]
    need(len(keys) == len(set(keys)), "duplicate resource")
    checks = state["cleanup"]["checks"]
    need(isinstance(checks, list), "checks must be an array")
    for item in checks:
        validate_check(item, state)
    iterations = [item["iteration"] for item in checks]
    need(len(iterations) == len(set(iterations)), "duplicate cleanup check")
    need(set(range(1, state["iteration"])) <= set(iterations), "missing earlier cleanup check")


def validate_artifacts(state):
    for item in state["artifacts"]:
        fields(item, {"source", "archive", "sha256", "iteration", "kind"}, "artifact")
        absolute(item["source"])
        absolute(item["archive"])
        need(item["kind"] in {"report", "history", "plan", "evidence"}, "invalid artifact kind")
        need(type(item["iteration"]) is int and 1 <= item["iteration"] <= state["iteration"], "invalid artifact pass")
        need(isinstance(item["sha256"], str) and bool(re.fullmatch(r"[0-9a-f]{64}", item["sha256"])), "invalid artifact hash")
    paths = [item["archive"] for item in state["artifacts"]]
    need(len(paths) == len(set(paths)), "duplicate artifact archive")


def validate_audits(state):
    artifacts = {item["archive"]: item for item in state["artifacts"]}
    for audit in state["audits"]:
        fields(audit, {"iteration", "phase", "sourceSha", "report", "history", "outcome", "findings"}, "audit")
        need(type(audit["iteration"]) is int and 1 <= audit["iteration"] <= state["iteration"], "invalid audit pass")
        need(audit["phase"] in {"initial", "post"}, "invalid audit phase")
        sha(audit["sourceSha"])
        need(audit["outcome"] in {"clean", "actionable", "deferred"}, "invalid audit outcome")
        need(isinstance(audit["findings"], list) and all(isinstance(x, str) and x.strip() for x in audit["findings"]), "invalid findings")
        need(bool(audit["findings"]) == (audit["outcome"] != "clean"), "findings/outcome mismatch")
        need(isinstance(audit["history"], list), "audit history must be an array")
        report_kinds = {"report"} if state["workflow"] == "grade-loop" else {"report", "plan", "evidence"}
        audit_artifact(artifacts, audit["report"], report_kinds, audit["iteration"])
        if state["workflow"] == "grade-loop":
            need(bool(audit["history"]), "grade audit requires archived history")
        for path in audit["history"]:
            audit_artifact(artifacts, path, {"history"}, audit["iteration"])


def audit_artifact(artifacts, path, kinds, iteration):
    text(path, "artifact reference")
    item = artifacts.get(path)
    need(item is not None and item["kind"] in kinds and item["iteration"] == iteration, "audit references wrong/missing artifact")


def validate_deliveries(state):
    for item in state["deliveries"]:
        fields(item, {"url", "iteration", "state", "mergeSha", "mergeVerified", "targetCiSha", "targetCiVerified"}, "delivery")
        text(item["url"], "delivery URL")
        need(type(item["iteration"]) is int and 1 <= item["iteration"] <= state["iteration"], "invalid delivery pass")
        need(item["state"] in {"open", "merged", "closed"}, "invalid delivery status")
        for flag in ("mergeVerified", "targetCiVerified"):
            need(type(item[flag]) is bool, "invalid delivery verification")
        for name in ("mergeSha", "targetCiSha"):
            if item[name] is not None:
                sha(item[name])
        if item["state"] != "merged":
            need(item["mergeSha"] is None and not item["mergeVerified"] and not item["targetCiVerified"], "unmerged delivery has merge evidence")
    urls = [item["url"] for item in state["deliveries"]]
    need(len(urls) == len(set(urls)), "duplicate delivery URL")


def settled(state):
    need(all(r["status"] == "cleaned" for r in state["resources"]), "uncleaned resources remain")
    for item in state["deliveries"]:
        need(item["state"] != "open", "open delivery remains")
        if item["state"] == "merged":
            need(item["mergeVerified"] and item["targetCiVerified"] and item["mergeSha"] is not None
                 and item["targetCiSha"] == item["mergeSha"], "delivery lacks verified merge/exact target CI")


def latest_audit(state):
    need(bool(state["audits"]), "missing audit evidence")
    audit = state["audits"][-1]
    need(audit["iteration"] == state["iteration"] and audit["sourceSha"] == state["currentSha"], "audit evidence is stale")
    merged = any(d["iteration"] == state["iteration"] and d["state"] == "merged" for d in state["deliveries"])
    need(not merged or audit["phase"] == "post", "delivered pass requires a post-delivery audit")
    return audit


def terminal(state):
    need(state["stage"] == "complete", "terminal status requires complete stage")
    settled(state)
    audit = latest_audit(state)
    if state["status"] == "complete":
        need(audit["outcome"] == "clean", "complete requires clean audit")
    else:
        need(audit["outcome"] != "clean", "deferred requires remaining findings")
        text(state["reason"], "deferral reason")
    need(any(c["iteration"] == state["iteration"] for c in state["cleanup"]["checks"]), "missing final cleanup check")


def outside_worktrees(state, path):
    path = Path(path).resolve()
    roots = [Path(w["path"]).resolve() for b in state["cleanup"]["baselines"] for w in b["worktrees"]]
    roots += [Path(r["identifier"]).resolve() for r in state["resources"] if r["kind"] == "worktree"]
    need(not any(path == root or root in path.parents for root in roots), "durable state/artifact must be outside every worktree")


def verify_artifacts(state):
    for item in state["artifacts"]:
        outside_worktrees(state, item["archive"])
        try:
            digest = hashlib.sha256(Path(item["archive"]).read_bytes()).hexdigest()
        except OSError as error:
            raise CleanupError("archived evidence is unreadable") from error
        need(digest == item["sha256"], "archived evidence hash mismatch")


def verify_cleanup(state):
    """Gate a pass boundary; return collaborator changes per repository for the report."""
    verify_target(state)
    settled(state)
    latest_audit(state)
    verify_artifacts(state)
    return verify_inventories(state)


def transition(current, candidate):
    for key in ("workflow", "schemaVersion", "runId", "repoRoot", "targetBranch", "targetRemote", "maxPasses"):
        need(candidate[key] == current[key], f"immutable {key}")
    need(candidate["revision"] == current["revision"], "stale candidate revision")
    need(current["status"] not in {"complete", "deferred"}, "terminal run is read-only")
    validate_resource_transition(current, candidate)
    need(candidate["artifacts"] == current["artifacts"], "use archive to register artifacts")
    need(candidate["audits"][:len(current["audits"])] == current["audits"], "audits are append-only")
    for audit in candidate["audits"][len(current["audits"]):]:
        need(audit["iteration"] == candidate["iteration"], "new audits belong to the current pass")
    delivery_transition(current, candidate)
    if candidate["status"] == "active":
        work_stage_transition(current, candidate)
    advanced = candidate["iteration"] != current["iteration"]
    if advanced:
        advance(current, candidate)
    if candidate["status"] in {"complete", "deferred"}:
        verify_cleanup(candidate)
    elif candidate["status"] == "active" and candidate["stage"] == "cleanup":
        verify_cleanup(candidate)



def work_stage_transition(current, candidate):
    stage = candidate["stage"]
    if candidate["workflow"] not in PLANNING_WORKFLOWS:
        if stage in {"planning", "implementation"} or (stage == "delivery" and current["stage"] != "delivery"):
            verify_decision(candidate)
        return
    if stage == "implementation":
        need(current["stage"] in {"planning", "implementation", "delivery"},
             "enter planning before implementation")
    if stage == "delivery":
        need(current["stage"] in {"implementation", "delivery"},
             "enter implementation before delivery")
    if stage in {"planning", "implementation"} or (stage == "delivery" and current["stage"] != "delivery"):
        verify_decision(candidate)
    if stage == "implementation" and current["stage"] == "planning":
        need(candidate["audits"][-1]["outcome"] == "actionable",
             "implementation entry requires selected actionable findings")


def verify_decision(state):
    verify_target(state)
    verify_artifacts(state)
    if state["workflow"] not in PLANNING_WORKFLOWS:
        return
    need(bool(state["audits"]), "planning requires audit evidence")
    audit = state["audits"][-1]
    need(audit["sourceSha"] == state["currentSha"], "planning audit evidence is stale")
    need(audit["iteration"] in {state["iteration"], state["iteration"] - 1},
         "planning requires current or just-completed pass evidence")
    if state["stage"] == "planning" and state["workflow"] in PLANNING_WORKFLOWS:
        need(audit["outcome"] == "actionable", "planning requires actionable findings")
    prior_delivery = any(d["iteration"] == audit["iteration"] and d["state"] == "merged"
                         for d in state["deliveries"])
    if prior_delivery:
        need(audit["phase"] == "post", "reuse requires a post-delivery audit")


def advance(current, candidate):
    need(candidate["iteration"] == current["iteration"] + 1, "advance one pass at a time")
    need(candidate["currentSha"] == current["currentSha"], "refresh audit evidence before advancing to a changed target")
    need(candidate["stage"] == "audit" and candidate["status"] == "active", "next pass must start active/audit")
    need(candidate["reason"] is None, "clear reason before the next pass")
    need(candidate["resources"] == current["resources"] and candidate["audits"] == current["audits"]
         and candidate["deliveries"] == current["deliveries"], "advance before adding next-pass work")
    need(any(c["iteration"] == current["iteration"] for c in current["cleanup"]["checks"]), "verify cleanup before advance")
    need(latest_audit(current)["outcome"] == "actionable", "next pass needs actionable findings")
    verify_cleanup(current)


def delivery_transition(current, candidate):
    before = {d["url"]: d for d in current["deliveries"]}
    after = {d["url"]: d for d in candidate["deliveries"]}
    need(before.keys() <= after.keys(), "deliveries cannot be removed")
    for url, item in after.items():
        if url not in before:
            need(item["state"] == "open" and item["iteration"] == candidate["iteration"], "new delivery must start open in current pass")
            continue
        old = before[url]
        need(old["iteration"] == item["iteration"], "delivery pass is immutable")
        if old["state"] == "closed":
            need(old == item, "closed delivery is immutable")
        elif old["state"] == "merged":
            need(item["state"] == "merged", "merged delivery cannot reopen")
            for name in ("mergeSha", "targetCiSha"):
                need(old[name] is None or item[name] == old[name], "delivery SHA is immutable")
            for flag in ("mergeVerified", "targetCiVerified"):
                need(not old[flag] or item[flag], "delivery verification cannot revert")
