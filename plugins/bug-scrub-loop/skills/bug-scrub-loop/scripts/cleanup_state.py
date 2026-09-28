"""Structural cleanup contracts and live, read-only iteration gates."""
from pathlib import Path

from git_inventory import InventoryError, capture, validate_inventory, verify


class CleanupError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise CleanupError(message)


def validate_cleanup(state):
    cleanup = state.get("cleanup")
    need(isinstance(cleanup, dict) and set(cleanup) == {"baselines", "checks"},
         "cleanup requires baselines and checks")
    baselines = validate_baselines(state)
    for resource in state["resources"]:
        validate_owned_resource(state, resource, baselines)
    checks = cleanup["checks"]
    need(isinstance(checks, list), "cleanup checks must be an array")
    for check in checks:
        validate_check(check, state)
    need(len({check["iteration"] for check in checks}) == len(checks),
         "duplicate iteration cleanup checks")
    for iteration in range(1, state["iteration"]):
        need(any(check["iteration"] == iteration for check in checks),
             f"iteration {iteration} lacks a cleanup check")
    if state["stage"] in {"rescrub", "complete"} or state["status"] == "complete":
        require_settled(state)
        need(any(check["iteration"] == state["iteration"] for check in checks),
             "current iteration lacks a cleanup check")


def validate_baselines(state):
    baselines = state["cleanup"]["baselines"]
    need(isinstance(baselines, list) and bool(baselines), "cleanup baseline is required")
    for baseline in baselines:
        validate_inventory(baseline)
    roots = [item["root"] for item in baselines]
    identities = [item["common_git_dir"] for item in baselines]
    need(len(roots) == len(set(roots)) and len(identities) == len(set(identities)),
         "cleanup baselines must represent distinct repositories")
    need(state["repoRoot"] in roots, "primary repository baseline is missing")
    need(all(plan["repoRoot"] in roots for plan in state["plans"]),
         "plan repository has no cleanup baseline")
    return baselines


def validate_check(check, state):
    need(isinstance(check, dict) and set(check) == {"iteration", "verifiedAt", "repositories"},
         "invalid cleanup check")
    need(type(check["iteration"]) is int and 0 <= check["iteration"] <= state["iteration"],
         "invalid cleanup check iteration")
    need(isinstance(check["verifiedAt"], str) and bool(check["verifiedAt"]),
         "cleanup check needs verification time")
    need(check["repositories"] == [b["root"] for b in state["cleanup"]["baselines"]],
         "cleanup check must cover every baseline repository")


def baseline_contains(resource, baseline):
    name = resource["identifier"]
    if resource["kind"] == "local-branch":
        return name in baseline["local_branches"]
    if resource["kind"] == "worktree":
        return any(item["path"] == name for item in baseline["worktrees"])
    return any(item["remote"] == resource["remote"] and name in item["branches"]
               for item in baseline["remote_branches"])


def validate_owned_resource(state, resource, baselines):
    need(resource["kind"] in {"local-branch", "remote-branch", "worktree"},
         "resource kind must be local-branch, remote-branch, or worktree")
    need(resource["owner"] == state["runId"], "resource owner must equal runId")
    need(type(resource["iteration"]) is int and 1 <= resource["iteration"] <= state["iteration"],
         "invalid resource iteration")
    baseline = next((b for b in baselines if b["root"] == resource["repoRoot"]), None)
    need(baseline is not None, "resource repository has no baseline")
    if resource["kind"] == "remote-branch":
        need(resource["remote"] in {b["remote"] for b in baseline["remote_branches"]},
             "resource remote is not in baseline")
    else:
        need(resource["remote"] is None, "only remote branches may name a remote")
    if resource["kind"] == "worktree":
        need(Path(resource["identifier"]).is_absolute(), "worktree identifier must be absolute")
    need(not baseline_contains(resource, baseline), "cannot claim a baseline resource as loop-owned")
    if resource["iteration"] < state["iteration"]:
        need(resource["status"] == "cleaned", "earlier iteration has uncleaned resources")


def resource_key(item):
    return (item.get("repoRoot"), item["kind"], item.get("remote"), item["identifier"])


def require_settled(state):
    need(all(r["status"] == "cleaned" for r in state["resources"]),
         "cleanup gate has uncleaned resources")
    need(all(p["state"] != "open" for p in state["pullRequests"]),
         "cleanup gate has open PRs")
    for pr in state["pullRequests"]:
        if pr["state"] == "merged":
            need(pr["mergeVerified"] and pr["targetCiVerified"]
                 and pr["targetCiSha"] == pr["mergeSha"],
                 "cleanup gate requires verified merge and exact target CI")
    need(all(p["status"] in {"complete", "superseded"} for p in state["plans"]),
         "cleanup gate has unfinished plans")


def verify_live(state):
    require_settled(state)
    for baseline in state["cleanup"]["baselines"]:
        verify(baseline)


def validate_cleanup_transition(current, candidate):
    before = current["cleanup"]
    after = candidate["cleanup"]
    need(before["baselines"] == after["baselines"], "cleanup baselines are immutable")
    need(after["checks"][:len(before["checks"])] == before["checks"],
         "cleanup checks are append-only")
    need(after["checks"] == before["checks"],
         "use verify-cleanup to record live cleanup checks")
    old = {resource_key(r): r for r in current["resources"]}
    for resource in candidate["resources"]:
        previous = old.get(resource_key(resource))
        if previous is None:
            need(resource["status"] == "active", "reserve resources as active before creation")
        else:
            for field in ("repoRoot", "iteration", "remote"):
                need(resource[field] == previous[field], f"resource {field} is immutable")
    advanced = candidate["iteration"] > current["iteration"]
    if advanced:
        need(candidate["iteration"] == current["iteration"] + 1, "cannot skip iterations")
        need(all(r["iteration"] <= current["iteration"] for r in candidate["resources"]),
             "advance iteration before reserving its resources")
        need(any(c["iteration"] == current["iteration"] for c in after["checks"]),
             "verify cleanup before advancing iteration")
    if advanced or candidate["stage"] in {"rescrub", "complete"} or candidate["status"] == "complete":
        verify_live(candidate)


def capture_baselines(repo_root, companion_roots):
    return {"baselines": [capture(root) for root in [repo_root, *companion_roots]], "checks": []}
