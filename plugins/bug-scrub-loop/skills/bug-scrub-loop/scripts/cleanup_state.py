"""Bug scrub loop cleanup policy composed from shared cleanup primitives."""
from shared_cleanup import core
from loop_cleanup.git_inventory import InventoryError, capture, validate_inventory, verify

CleanupError = core.CleanupError
need = core.need
validate_baselines = core.validate_baselines
validate_check = core.validate_check
baseline_contains = core.baseline_contains
validate_owned_resource = core.validate_owned_resource
resource_key = core.resource_key
capture_baselines = core.capture_baselines


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


def require_settled(state):
    need(all(resource["status"] == "cleaned" for resource in state["resources"]),
         "cleanup gate has uncleaned resources")
    need(all(pr["state"] != "open" for pr in state["pullRequests"]),
         "cleanup gate has open PRs")
    for pr in state["pullRequests"]:
        if pr["state"] == "merged":
            need(pr["mergeVerified"] and pr["targetCiVerified"]
                 and pr["targetCiSha"] == pr["mergeSha"],
                 "cleanup gate requires verified merge and exact target CI")
    need(all(plan["status"] in {"complete", "superseded"} for plan in state.get("plans", [])),
         "cleanup gate has unfinished plans")


def verify_live(state):
    """Require settled delivery and no owned leftovers; return collaborator changes."""
    require_settled(state)
    return core.verify_inventories(state)


def validate_cleanup_transition(current, candidate):
    core.validate_resource_transition(current, candidate)
    before = current["cleanup"]
    after = candidate["cleanup"]
    need(after["checks"][:len(before["checks"])] == before["checks"],
         "cleanup checks are append-only")
    advanced = candidate["iteration"] > current["iteration"]
    if advanced:
        need(candidate["iteration"] == current["iteration"] + 1, "cannot skip iterations")
        need(all(resource["iteration"] <= current["iteration"] for resource in candidate["resources"]),
             "advance iteration before reserving its resources")
        need(any(check["iteration"] == current["iteration"] for check in after["checks"]),
             "verify cleanup before advancing iteration")
    if advanced or candidate["stage"] in {"rescrub", "complete"} or candidate["status"] == "complete":
        verify_live(candidate)
