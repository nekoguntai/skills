"""Generic immutable cleanup-state primitives shared by loop skills."""

from pathlib import Path

from .git_inventory import capture, validate_inventory, verify

DELIVERY_CLEANUP_API_VERSION = 1


class CleanupError(ValueError):
    """Raised when a cleanup contract is invalid."""


def need(condition, message):
    if not condition:
        raise CleanupError(message)


def validate_baselines(state):
    cleanup = state.get("cleanup")
    baselines = cleanup.get("baselines") if isinstance(cleanup, dict) else None
    need(isinstance(baselines, list) and bool(baselines), "cleanup baseline is required")
    for baseline in baselines:
        validate_inventory(baseline)
    roots = [item["root"] for item in baselines]
    identities = [item["common_git_dir"] for item in baselines]
    need(len(roots) == len(set(roots)) and len(identities) == len(set(identities)),
         "cleanup baselines must represent distinct repositories")
    need(state["repoRoot"] in roots, "primary repository baseline is missing")
    need(all(plan["repoRoot"] in roots for plan in state.get("plans", [])),
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
    baseline = next((item for item in baselines if item["root"] == resource["repoRoot"]), None)
    need(baseline is not None, "resource repository has no baseline")
    if resource["kind"] == "remote-branch":
        need(resource["remote"] in {item["remote"] for item in baseline["remote_branches"]},
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


def capture_baselines(repo_root, companion_roots):
    return {"baselines": [capture(root) for root in [repo_root, *companion_roots]], "checks": []}


def verify_inventories(state):
    """Check each repository for this run's leftovers; return collaborator changes.

    Resources the run owns must be gone. Changes made by other collaborators
    (branches and worktrees this run never reserved) are reported, not failed.
    """
    report = {}
    for baseline in validate_baselines(state):
        owned = [item for item in state.get("resources", []) if item.get("repoRoot") == baseline["root"]]
        report[baseline["root"]] = verify(baseline, owned)["collaborator_changes"]
    return report


def validate_resource_transition(current, candidate):
    """Enforce immutable receipts and stable ownership for resource records."""
    before = current["cleanup"]
    after = candidate["cleanup"]
    need(before["baselines"] == after["baselines"], "cleanup baselines are immutable")
    need(after["checks"] == before["checks"], "use verify-cleanup to record live cleanup checks")
    old = {resource_key(item): item for item in current["resources"]}
    new = {resource_key(item): item for item in candidate["resources"]}
    need(set(old) <= set(new), "resources cannot be removed")
    transitions = {"active": {"active", "cleaned", "preserved", "converted"},
                   "cleaned": {"cleaned"}, "preserved": {"preserved", "cleaned"},
                   "converted": {"converted", "cleaned", "preserved"}}
    for resource in candidate["resources"]:
        previous = old.get(resource_key(resource))
        if previous is None:
            need(resource["status"] == "active", "reserve resources as active before creation")
        else:
            for field in ("repoRoot", "iteration", "remote", "owner", "kind", "identifier"):
                need(resource[field] == previous[field], f"resource {field} is immutable")
            need(resource["status"] in transitions[previous["status"]],
                 f"invalid resource status transition {previous['status']} -> {resource['status']}")
