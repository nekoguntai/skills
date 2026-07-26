#!/usr/bin/env python3
"""Initialize, validate, and atomically replace bug-scrub-loop run state."""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{5,79}$")
DEPLOYMENT_POLICIES = {"final", "each-plan", "never"}
RUN_STATUSES = {"active", "stagnated", "incomplete", "blocked", "complete"}
STAGES = {
    "preflight",
    "scrub",
    "planning",
    "plan-review",
    "implementation",
    "rescrub",
    "closeout",
    "stagnated",
    "complete",
}
SEVERITIES = {"P0", "P1", "P2", "P3"}
SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
FINDING_STATUSES = {
    "confirmed",
    "planned",
    "remediating",
    "resolved",
    "backlog",
    "rejected",
    "blocked",
}
BLOCKING_FINDING_STATUSES = {"confirmed", "planned", "remediating", "blocked"}
PLAN_STATUSES = {"draft", "reviewed", "implementing", "complete", "superseded"}
PR_STATUSES = {"open", "merged", "closed"}
DEPLOYMENT_STATUSES = {"pending", "uncertain", "deferred", "success", "skipped", "failed"}
RESOURCE_STATUSES = {"active", "cleaned", "preserved", "converted"}
REQUIRED_DOMAINS = {
    "trust-boundaries",
    "persistence",
    "api-contracts",
    "async-lifecycle",
    "frontend-state",
    "error-handling",
    "tests-ci",
    "recent-changes",
}
FINDING_TRANSITIONS = {
    "confirmed": {"confirmed", "planned", "remediating", "resolved", "rejected", "blocked"},
    "planned": {"planned", "remediating", "resolved", "blocked"},
    "remediating": {"remediating", "confirmed", "resolved", "blocked"},
    "resolved": {"resolved", "confirmed"},
    "backlog": {"backlog", "resolved", "rejected"},
    "rejected": {"rejected", "confirmed"},
    "blocked": {"blocked", "planned", "remediating", "resolved"},
}
PLAN_TRANSITIONS = {
    "draft": {"draft", "reviewed", "superseded"},
    "reviewed": {"reviewed", "implementing", "complete", "superseded"},
    "implementing": {"implementing", "complete", "superseded"},
    "complete": {"complete", "reviewed", "implementing"},
    "superseded": {"superseded"},
}
PR_TRANSITIONS = {"open": {"open", "merged", "closed"}, "merged": {"merged"}, "closed": {"closed"}}
RESOURCE_TRANSITIONS = {
    "active": {"active", "cleaned", "preserved", "converted"},
    "cleaned": {"cleaned"},
    "preserved": {"preserved"},
    "converted": {"converted", "cleaned", "preserved"},
}
RUN_TRANSITIONS = {
    "active": {"active", "stagnated", "incomplete", "blocked", "complete"},
    "stagnated": {"stagnated", "active", "blocked"},
    "incomplete": {"incomplete", "active", "blocked", "complete"},
    "blocked": {"blocked", "active"},
    "complete": {"complete"},
}
DEPLOYMENT_TRANSITIONS = {
    "pending": {"pending", "uncertain", "success", "failed", "skipped"},
    "uncertain": {"uncertain", "success", "failed"},
    "deferred": {"deferred"},
    "success": {"success"},
    "skipped": {"skipped"},
    "failed": {"failed"},
}


class StateError(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StateError(message)


def require_string(value: Any, path: str) -> str:
    require(isinstance(value, str) and value.strip() != "", f"{path} must be a non-empty string")
    return value


def require_sha(value: Any, path: str) -> str:
    text = require_string(value, path)
    require(bool(SHA_PATTERN.fullmatch(text)), f"{path} must be a full lowercase Git SHA")
    return text


def require_list(value: Any, path: str) -> list[Any]:
    require(isinstance(value, list), f"{path} must be an array")
    return value


def require_integer(value: Any, path: str, minimum: int = 0) -> int:
    require(type(value) is int and value >= minimum, f"{path} must be >= {minimum}")
    return value


def require_exact_fields(value: dict[str, Any], expected: set[str], path: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    require(not missing, f"{path} is missing fields: {', '.join(missing)}")
    require(not extra, f"{path} has unknown fields: {', '.join(extra)}")


def validate_finding(value: Any, index: int) -> None:
    path = f"findings[{index}]"
    require(isinstance(value, dict), f"{path} must be an object")
    require_exact_fields(
        value,
        {
            "id",
            "fingerprint",
            "severity",
            "title",
            "owner",
            "trigger",
            "status",
            "attempts",
            "attemptRecords",
            "firstSeenIteration",
            "lastSeenIteration",
            "disposition",
            "evidence",
        },
        path,
    )
    for field in ("id", "fingerprint", "severity", "title", "owner", "trigger", "status"):
        require_string(value.get(field), f"{path}.{field}")
    require(value["severity"] in SEVERITIES, f"{path}.severity is invalid")
    require(value["status"] in FINDING_STATUSES, f"{path}.status is invalid")
    require_integer(value.get("attempts"), f"{path}.attempts")
    attempt_records = require_list(value.get("attemptRecords"), f"{path}.attemptRecords")
    attempt_keys: list[tuple[str, str, str]] = []
    for attempt_index, attempt in enumerate(attempt_records):
        attempt_path = f"{path}.attemptRecords[{attempt_index}]"
        require(isinstance(attempt, dict), f"{attempt_path} must be an object")
        require_exact_fields(attempt, {"planPath", "planCommitSha", "mergeSha"}, attempt_path)
        require_string(attempt.get("planPath"), f"{attempt_path}.planPath")
        require_sha(attempt.get("planCommitSha"), f"{attempt_path}.planCommitSha")
        require_sha(attempt.get("mergeSha"), f"{attempt_path}.mergeSha")
        attempt_keys.append((attempt["planPath"], attempt["planCommitSha"], attempt["mergeSha"]))
    require(len(attempt_keys) == len(set(attempt_keys)), f"{path}.attemptRecords contains duplicates")
    require(value["attempts"] == len(attempt_records), f"{path}.attempts must equal attemptRecords length")
    first_seen = require_integer(value.get("firstSeenIteration"), f"{path}.firstSeenIteration", 1)
    last_seen = require_integer(value.get("lastSeenIteration"), f"{path}.lastSeenIteration", first_seen)
    disposition = value.get("disposition")
    require(disposition is None or (isinstance(disposition, str) and disposition.strip()), f"{path}.disposition is invalid")
    evidence = require_list(value.get("evidence"), f"{path}.evidence")
    require(all(isinstance(item, str) and item for item in evidence), f"{path}.evidence must contain strings")
    if value["severity"] == "P3" and value["status"] not in {"backlog", "resolved", "rejected"}:
        raise StateError(f"{path}: unresolved P3 findings must use backlog status")
    if value["severity"] in {"P0", "P1", "P2"} and value["status"] == "backlog":
        raise StateError(f"{path}: P0-P2 findings cannot use backlog status")
    if value["status"] in {"resolved", "rejected"}:
        require(isinstance(disposition, str) and disposition.strip(), f"{path}.disposition is required for {value['status']}")
    if value["status"] == "resolved" and value["severity"] in {"P0", "P1", "P2"}:
        require(
            value["attempts"] > 0 or disposition.startswith("external:"),
            f"{path}: resolved P0-P2 requires an attempt or external: disposition",
        )


def validate_plan(value: Any, index: int) -> None:
    path = f"plans[{index}]"
    require(isinstance(value, dict), f"{path} must be an object")
    require_exact_fields(
        value,
        {
            "path",
            "repoRoot",
            "iteration",
            "status",
            "reviewPasses",
            "commitShas",
            "implementationCommitSha",
            "implementationCommitShas",
        },
        path,
    )
    require_string(value.get("path"), f"{path}.path")
    require(Path(value["path"]).is_absolute(), f"{path}.path must be absolute")
    require_string(value.get("repoRoot"), f"{path}.repoRoot")
    require(Path(value["repoRoot"]).is_absolute(), f"{path}.repoRoot must be absolute")
    require_integer(value.get("iteration"), f"{path}.iteration", 1)
    require(value.get("status") in PLAN_STATUSES, f"{path}.status is invalid")
    require_integer(value.get("reviewPasses"), f"{path}.reviewPasses")
    commit_shas = require_list(value.get("commitShas"), f"{path}.commitShas")
    require(all(isinstance(item, str) and bool(SHA_PATTERN.fullmatch(item)) for item in commit_shas), f"{path}.commitShas is invalid")
    require(len(commit_shas) == len(set(commit_shas)), f"{path}.commitShas contains duplicates")
    implementation_commit_sha = value.get("implementationCommitSha")
    require(
        implementation_commit_sha is None
        or (isinstance(implementation_commit_sha, str) and bool(SHA_PATTERN.fullmatch(implementation_commit_sha))),
        f"{path}.implementationCommitSha is invalid",
    )
    implementation_commit_shas = require_list(value.get("implementationCommitShas"), f"{path}.implementationCommitShas")
    require(
        all(isinstance(item, str) and bool(SHA_PATTERN.fullmatch(item)) for item in implementation_commit_shas),
        f"{path}.implementationCommitShas is invalid",
    )
    require(
        len(implementation_commit_shas) == len(set(implementation_commit_shas)),
        f"{path}.implementationCommitShas contains duplicates",
    )
    require(set(implementation_commit_shas) <= set(commit_shas), f"{path}.implementationCommitShas must be plan commits")
    require(
        (implementation_commit_sha is None and not implementation_commit_shas)
        or (bool(implementation_commit_shas) and implementation_commit_shas[-1] == implementation_commit_sha),
        f"{path}.implementationCommitShas must end with implementationCommitSha",
    )
    if value["status"] == "complete":
        require(bool(commit_shas), f"{path}.commitShas is required for completed plans")
    if value["status"] == "draft":
        require(value["reviewPasses"] == 0, f"{path}.draft plans cannot have review passes")
        require(
            implementation_commit_sha is None and not implementation_commit_shas,
            f"{path}.draft plans cannot have reviewed implementation commits",
        )
    if value["status"] in {"reviewed", "implementing", "complete"}:
        require(value["reviewPasses"] > 0, f"{path}.reviewPasses must be positive after review")
        require(implementation_commit_sha is not None, f"{path}.implementationCommitSha is required after review")


def validate_pull_request(value: Any, index: int) -> None:
    path = f"pullRequests[{index}]"
    require(isinstance(value, dict), f"{path} must be an object")
    require_exact_fields(
        value,
        {
            "number",
            "url",
            "iteration",
            "planPath",
            "targetBranch",
            "state",
            "headSha",
            "headShas",
            "planCommitSha",
            "planCommitShas",
            "mergeSha",
            "mergeVerified",
            "targetCiVerified",
            "targetCiSha",
            "resolution",
        },
        path,
    )
    require_integer(value.get("number"), f"{path}.number", 1)
    for field in ("url", "planPath", "targetBranch"):
        require_string(value.get(field), f"{path}.{field}")
    require_integer(value.get("iteration"), f"{path}.iteration", 1)
    require(value.get("state") in PR_STATUSES, f"{path}.state is invalid")
    require_sha(value.get("headSha"), f"{path}.headSha")
    head_shas = require_list(value.get("headShas"), f"{path}.headShas")
    require(all(isinstance(item, str) and bool(SHA_PATTERN.fullmatch(item)) for item in head_shas), f"{path}.headShas is invalid")
    require(bool(head_shas) and head_shas[-1] == value["headSha"], f"{path}.headShas must end with headSha")
    require(len(head_shas) == len(set(head_shas)), f"{path}.headShas contains duplicates")
    require_sha(value.get("planCommitSha"), f"{path}.planCommitSha")
    plan_commit_shas = require_list(value.get("planCommitShas"), f"{path}.planCommitShas")
    require(all(isinstance(item, str) and bool(SHA_PATTERN.fullmatch(item)) for item in plan_commit_shas), f"{path}.planCommitShas is invalid")
    require(bool(plan_commit_shas) and plan_commit_shas[-1] == value["planCommitSha"], f"{path}.planCommitShas must end with planCommitSha")
    require(len(plan_commit_shas) == len(set(plan_commit_shas)), f"{path}.planCommitShas contains duplicates")
    merge_sha = value.get("mergeSha")
    require(
        merge_sha is None or (isinstance(merge_sha, str) and bool(SHA_PATTERN.fullmatch(merge_sha))),
        f"{path}.mergeSha is invalid",
    )
    if value["state"] == "merged":
        require(merge_sha is not None, f"{path}.mergeSha is required for merged PRs")
    for field in ("mergeVerified", "targetCiVerified"):
        require(isinstance(value.get(field), bool), f"{path}.{field} must be boolean")
    target_ci_sha = value.get("targetCiSha")
    require(
        target_ci_sha is None or (isinstance(target_ci_sha, str) and bool(SHA_PATTERN.fullmatch(target_ci_sha))),
        f"{path}.targetCiSha is invalid",
    )
    resolution = value.get("resolution")
    require(resolution is None or (isinstance(resolution, str) and resolution.strip()), f"{path}.resolution is invalid")
    if value["mergeVerified"]:
        require(merge_sha is not None, f"{path}.mergeVerified requires mergeSha")
    if value["targetCiVerified"]:
        require(target_ci_sha is not None, f"{path}.targetCiVerified requires targetCiSha")
    if value["state"] == "closed":
        require(resolution is not None, f"{path}.resolution is required for closed PRs")
    if value["state"] == "open":
        require(merge_sha is None, f"{path}.open PR cannot have mergeSha")
        require(not value["mergeVerified"], f"{path}.open PR cannot have verified merge ancestry")
        require(not value["targetCiVerified"], f"{path}.open PR cannot have verified target CI")
        require(target_ci_sha is None, f"{path}.open PR cannot have targetCiSha")
        require(resolution is None, f"{path}.open PR cannot have a closure resolution")


def validate_deployment(value: Any, index: int) -> None:
    path = f"deployments[{index}]"
    require(isinstance(value, dict), f"{path} must be an object")
    require_exact_fields(
        value,
        {
            "operationId",
            "commit",
            "policy",
            "status",
            "attemptedAt",
            "completedAt",
            "healthVerified",
            "readinessVerified",
            "details",
        },
        path,
    )
    require_string(value.get("operationId"), f"{path}.operationId")
    require_sha(value.get("commit"), f"{path}.commit")
    require(value.get("policy") in DEPLOYMENT_POLICIES, f"{path}.policy is invalid")
    require(value.get("status") in DEPLOYMENT_STATUSES, f"{path}.status is invalid")
    for field in ("healthVerified", "readinessVerified"):
        require(isinstance(value.get(field), bool), f"{path}.{field} must be boolean")
    details = value.get("details")
    require(details is None or isinstance(details, str), f"{path}.details must be null or string")
    require_string(value.get("attemptedAt"), f"{path}.attemptedAt")
    completed_at = value.get("completedAt")
    require(completed_at is None or (isinstance(completed_at, str) and completed_at.strip()), f"{path}.completedAt is invalid")
    if value["status"] == "success":
        require(value["healthVerified"] and value["readinessVerified"], f"{path} success requires health/readiness")
    if value["status"] in {"success", "skipped", "failed"}:
        require(completed_at is not None, f"{path}.completedAt is required for terminal status")
    if value["status"] in {"failed", "skipped"}:
        require(isinstance(details, str) and details.strip(), f"{path}.details is required for {value['status']}")


def validate_resource(value: Any, index: int) -> None:
    path = f"resources[{index}]"
    require(isinstance(value, dict), f"{path} must be an object")
    require_exact_fields(value, {"kind", "identifier", "owner", "status"}, path)
    for field in ("kind", "identifier", "owner"):
        require_string(value.get(field), f"{path}.{field}")
    require(value.get("status") in RESOURCE_STATUSES, f"{path}.status is invalid")


def validate_coverage_pass(value: Any, index: int) -> None:
    path = f"coveragePasses[{index}]"
    require(isinstance(value, dict), f"{path} must be an object")
    require_exact_fields(
        value,
        {
            "iteration",
            "sha",
            "kind",
            "complete",
            "acceptedFindingIds",
            "acceptedFindingSeverities",
            "blockingFindingIds",
            "domains",
            "gaps",
        },
        path,
    )
    require_integer(value.get("iteration"), f"{path}.iteration", 1)
    require_sha(value.get("sha"), f"{path}.sha")
    require(value.get("kind") in {"initial", "rescrub"}, f"{path}.kind is invalid")
    require(isinstance(value.get("complete"), bool), f"{path}.complete must be boolean")
    accepted_ids = require_list(value.get("acceptedFindingIds"), f"{path}.acceptedFindingIds")
    accepted_severities = value.get("acceptedFindingSeverities")
    require(isinstance(accepted_severities, dict), f"{path}.acceptedFindingSeverities must be an object")
    blocking_ids = require_list(value.get("blockingFindingIds"), f"{path}.blockingFindingIds")
    require(all(isinstance(item, str) and item for item in accepted_ids), f"{path}.acceptedFindingIds must contain strings")
    require(all(isinstance(item, str) and item for item in blocking_ids), f"{path}.blockingFindingIds must contain strings")
    require(len(accepted_ids) == len(set(accepted_ids)), f"{path}.acceptedFindingIds contains duplicates")
    require(set(accepted_severities) == set(accepted_ids), f"{path}.acceptedFindingSeverities keys must match acceptedFindingIds")
    require(all(item in SEVERITIES for item in accepted_severities.values()), f"{path}.acceptedFindingSeverities has invalid severity")
    require(len(blocking_ids) == len(set(blocking_ids)), f"{path}.blockingFindingIds contains duplicates")
    require(set(blocking_ids) <= set(accepted_ids), f"{path}.blockingFindingIds must be accepted")
    gaps = require_list(value.get("gaps"), f"{path}.gaps")
    require(all(isinstance(item, str) and item for item in gaps), f"{path}.gaps must contain strings")
    domains = require_list(value.get("domains"), f"{path}.domains")
    names: list[str] = []
    has_blocked = False
    for domain_index, domain in enumerate(domains):
        domain_path = f"{path}.domains[{domain_index}]"
        require(isinstance(domain, dict), f"{domain_path} must be an object")
        require_exact_fields(domain, {"name", "status", "paths", "evidence", "reason"}, domain_path)
        name = require_string(domain.get("name"), f"{domain_path}.name")
        status = require_string(domain.get("status"), f"{domain_path}.status")
        require(status in {"inspected", "excluded", "blocked"}, f"{domain_path}.status is invalid")
        paths = require_list(domain.get("paths"), f"{domain_path}.paths")
        evidence = require_list(domain.get("evidence"), f"{domain_path}.evidence")
        require(all(isinstance(item, str) and item for item in paths), f"{domain_path}.paths must contain strings")
        require(all(isinstance(item, str) and item for item in evidence), f"{domain_path}.evidence must contain strings")
        reason = domain.get("reason")
        require(reason is None or isinstance(reason, str), f"{domain_path}.reason must be null or string")
        if status == "inspected":
            require(bool(paths) and bool(evidence), f"{domain_path} needs paths and evidence")
        if status in {"excluded", "blocked"}:
            require(isinstance(reason, str) and reason.strip() != "", f"{domain_path} needs a reason")
        has_blocked = has_blocked or status == "blocked"
        names.append(name)
    require(len(names) == len(set(names)), f"{path}.domains contains duplicate names")
    require(set(names) == REQUIRED_DOMAINS, f"{path}.domains must cover the required domain set")
    if value["complete"]:
        require(not has_blocked and not gaps, f"{path} cannot be complete with blocked domains or gaps")


def validate_state(state: Any) -> dict[str, Any]:
    require(isinstance(state, dict), "state must be an object")
    required = {
        "schemaVersion",
        "revision",
        "runId",
        "repoRoot",
        "targetBranch",
        "originalScope",
        "severityThreshold",
        "deploymentPolicy",
        "maxIterations",
        "containersRunningAtStart",
        "containersRunningAtCloseout",
        "status",
        "stage",
        "iteration",
        "baselineSha",
        "currentSha",
        "findings",
        "plans",
        "pullRequests",
        "deployments",
        "resources",
        "verificationCommands",
        "coveragePasses",
        "createdAt",
        "updatedAt",
    }
    require_exact_fields(state, required, "state")
    require(type(state["schemaVersion"]) is int and state["schemaVersion"] == SCHEMA_VERSION, "schemaVersion is unsupported")
    require_integer(state["revision"], "revision")
    run_id = require_string(state["runId"], "runId")
    require(bool(RUN_ID_PATTERN.fullmatch(run_id)), "runId must be lowercase kebab-case")
    repo_root = Path(require_string(state["repoRoot"], "repoRoot"))
    require(repo_root.is_absolute(), "repoRoot must be absolute")
    require_string(state["targetBranch"], "targetBranch")
    require_string(state["originalScope"], "originalScope")
    require(state["severityThreshold"] == "P2", "severityThreshold must remain P2")
    require(state["deploymentPolicy"] in DEPLOYMENT_POLICIES, "deploymentPolicy is invalid")
    maximum = state["maxIterations"]
    require(maximum is None or (type(maximum) is int and maximum > 0), "maxIterations must be null or > 0")
    require(isinstance(state["containersRunningAtStart"], bool), "containersRunningAtStart must be boolean")
    closeout_running = state["containersRunningAtCloseout"]
    require(closeout_running is None or isinstance(closeout_running, bool), "containersRunningAtCloseout is invalid")
    require(state["status"] in RUN_STATUSES, "status is invalid")
    require(state["stage"] in STAGES, "stage is invalid")
    if closeout_running is not None:
        require(state["stage"] in {"closeout", "complete"}, "containersRunningAtCloseout may only be set during closeout")
    require_integer(state["iteration"], "iteration")
    require(maximum is None or state["iteration"] <= maximum, "iteration exceeds maxIterations")
    require_sha(state["baselineSha"], "baselineSha")
    require_sha(state["currentSha"], "currentSha")
    plans = require_list(state["plans"], "plans")
    for index, plan in enumerate(plans):
        validate_plan(plan, index)
    plan_paths = [plan["path"] for plan in plans]
    require(len(plan_paths) == len(set(plan_paths)), "plans contains duplicate paths")
    pull_requests = require_list(state["pullRequests"], "pullRequests")
    for index, pull_request in enumerate(pull_requests):
        validate_pull_request(pull_request, index)
        require(pull_request["targetBranch"] == state["targetBranch"], f"pullRequests[{index}] target mismatch")
        require(pull_request["planPath"] in plan_paths, f"pullRequests[{index}] references an unknown plan")
        plan = plans[plan_paths.index(pull_request["planPath"])]
        require(
            pull_request["planCommitSha"] in plan["implementationCommitShas"],
            f"pullRequests[{index}] references an unknown plan revision",
        )
        require(
            set(pull_request["planCommitShas"]) <= set(plan["implementationCommitShas"]),
            f"pullRequests[{index}] plan revision history is not owned by its plan",
        )
    pull_request_keys = [(pull_request["url"], pull_request["number"]) for pull_request in pull_requests]
    require(len(pull_request_keys) == len(set(pull_request_keys)), "pullRequests contains duplicates")
    deployments = require_list(state["deployments"], "deployments")
    for index, deployment in enumerate(deployments):
        validate_deployment(deployment, index)
    deployment_ids = [deployment["operationId"] for deployment in deployments]
    require(len(deployment_ids) == len(set(deployment_ids)), "deployments contains duplicate operationIds")
    resources = require_list(state["resources"], "resources")
    for index, resource in enumerate(resources):
        validate_resource(resource, index)
    verification_commands = require_list(state["verificationCommands"], "verificationCommands")
    require(
        all(isinstance(command, str) and command for command in verification_commands),
        "verificationCommands must contain strings",
    )
    findings = require_list(state["findings"], "findings")
    for index, finding in enumerate(findings):
        validate_finding(finding, index)
        for attempt in finding["attemptRecords"]:
            plan_path = attempt["planPath"]
            require(plan_path in plan_paths, f"findings[{index}] references an unknown attempt plan")
            plan = plans[plan_paths.index(plan_path)]
            require(
                attempt["planCommitSha"] in plan["implementationCommitShas"],
                f"findings[{index}] attempt revision is unknown",
            )
            delivered = [
                pull_request
                for pull_request in pull_requests
                if pull_request["planPath"] == plan_path
                and pull_request["state"] == "merged"
                and pull_request["planCommitSha"] == attempt["planCommitSha"]
                and pull_request["mergeSha"] == attempt["mergeSha"]
                and pull_request["mergeVerified"]
                and pull_request["targetCiVerified"]
                and pull_request["targetCiSha"] == pull_request["mergeSha"]
            ]
            require(bool(delivered), f"findings[{index}] attempt record lacks verified merged delivery")
    finding_ids = [finding["id"] for finding in findings]
    require(len(finding_ids) == len(set(finding_ids)), "findings contains duplicate ids")
    fingerprints = [finding["fingerprint"] for finding in findings]
    require(len(fingerprints) == len(set(fingerprints)), "findings contains duplicate fingerprints")
    coverage = require_list(state["coveragePasses"], "coveragePasses")
    for index, coverage_pass in enumerate(coverage):
        validate_coverage_pass(coverage_pass, index)
        require(
            set(coverage_pass["acceptedFindingIds"]) <= set(finding_ids),
            f"coveragePasses[{index}] references unknown findings",
        )
        for finding_id, severity in coverage_pass["acceptedFindingSeverities"].items():
            finding = findings[finding_ids.index(finding_id)]
            if finding["lastSeenIteration"] == coverage_pass["iteration"]:
                require(
                    severity == finding["severity"],
                    f"coveragePasses[{index}] severity snapshot disagrees with the finding seen in that iteration",
                )
        expected_blocking_ids = {
            finding_id
            for finding_id, severity in coverage_pass["acceptedFindingSeverities"].items()
            if severity in {"P0", "P1", "P2"}
        }
        require(
            set(coverage_pass["blockingFindingIds"]) == expected_blocking_ids,
            f"coveragePasses[{index}] blockingFindingIds do not match accepted P0-P2 findings",
        )
    require_string(state["createdAt"], "createdAt")
    require_string(state["updatedAt"], "updatedAt")
    if state["status"] == "incomplete":
        require(maximum is not None and state["iteration"] == maximum, "incomplete status requires reached maxIterations")
    if state["status"] == "complete":
        require(state["stage"] == "complete", "complete status requires complete stage")
        require(bool(coverage), "complete status requires a coverage pass")
        latest = coverage[-1]
        require(latest["complete"], "complete status requires a complete final coverage pass")
        require(latest["iteration"] == state["iteration"], "final coverage iteration must equal run iteration")
        require(latest["sha"] == state["currentSha"], "final coverage SHA must equal currentSha")
        require(not latest["blockingFindingIds"], "final coverage pass still has blocking findings")
        blockers = [
            finding["id"]
            for finding in findings
            if finding["severity"] in {"P0", "P1", "P2"}
            and finding["status"] in BLOCKING_FINDING_STATUSES
        ]
        require(not blockers, f"complete status has blocking findings: {', '.join(blockers)}")
        require(
            all(plan["status"] in {"complete", "superseded"} for plan in plans),
            "complete status has unfinished plans",
        )
        for index, plan in enumerate(plans):
            if plan["status"] == "complete":
                require(
                    any(
                        pull_request["planPath"] == plan["path"]
                        and pull_request["state"] == "merged"
                        and pull_request["planCommitSha"] == plan["implementationCommitSha"]
                        and pull_request["mergeVerified"]
                        and pull_request["targetCiVerified"]
                        and pull_request["targetCiSha"] == pull_request["mergeSha"]
                        for pull_request in pull_requests
                    ),
                    f"plans[{index}] final revision lacks verified merged delivery",
                )
        require(not any(pull_request["state"] == "open" for pull_request in pull_requests), "complete status has open PRs")
        for index, pull_request in enumerate(pull_requests):
            if pull_request["state"] == "merged":
                require(pull_request["mergeVerified"], f"pullRequests[{index}] merge ancestry is unverified")
                require(pull_request["targetCiVerified"], f"pullRequests[{index}] target CI is unverified")
                require(
                    pull_request["targetCiSha"] == pull_request["mergeSha"],
                    f"pullRequests[{index}] target CI SHA must equal merge SHA",
                )
        require(all(resource["status"] == "cleaned" for resource in resources), "complete status has uncleaned resources")
        require(
            not any(deployment["status"] in {"pending", "uncertain"} for deployment in deployments),
            "complete status has unreconciled deployment operations",
        )
        for index, deployment in enumerate(deployments):
            if deployment["status"] == "failed":
                require(
                    any(
                        later["commit"] == deployment["commit"]
                        and later["policy"] == deployment["policy"]
                        and later["status"] in {"success", "skipped"}
                        for later in deployments[index + 1 :]
                    ),
                    f"deployment {deployment['operationId']} failed without a reconciled retry",
                )
        require(bool(deployments), "complete status requires deployment-policy evidence")
        final_deployment = deployments[-1]
        require(final_deployment["commit"] == state["currentSha"], "final deployment evidence must match currentSha")
        require(final_deployment["policy"] == state["deploymentPolicy"], "final deployment evidence policy mismatch")
        require(final_deployment["status"] in {"success", "skipped"}, "final deployment evidence is not complete")
        require(closeout_running is not None, "complete status requires closeout container state")
        if (
            state["deploymentPolicy"] == "never"
            or not state["containersRunningAtStart"]
            or not closeout_running
        ):
            require(final_deployment["status"] == "skipped", "final deployment must be skipped by policy/state")
        else:
            require(final_deployment["status"] == "success", "running-stack completion requires successful deployment")
    return state


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StateError(f"cannot read {path}: {error}") from error


def keyed(values: list[dict[str, Any]], field: str) -> dict[Any, dict[str, Any]]:
    return {value[field]: value for value in values}


def require_prefix(current: list[Any], candidate: list[Any], path: str) -> None:
    require(candidate[: len(current)] == current, f"{path} history cannot be removed or rewritten")


def validate_transition(current: dict[str, Any], candidate: dict[str, Any]) -> None:
    current_findings = keyed(current["findings"], "id")
    candidate_findings = keyed(candidate["findings"], "id")
    require(set(current_findings) <= set(candidate_findings), "findings cannot be removed")
    for finding_id, before in current_findings.items():
        after = candidate_findings[finding_id]
        for field in ("id", "fingerprint", "owner", "trigger", "firstSeenIteration"):
            require(after[field] == before[field], f"finding {finding_id} cannot change {field}")
        require(
            SEVERITY_RANK[after["severity"]] <= SEVERITY_RANK[before["severity"]],
            f"finding {finding_id} severity cannot be downgraded",
        )
        require(after["attempts"] >= before["attempts"], f"finding {finding_id} attempts cannot decrease")
        require_prefix(before["attemptRecords"], after["attemptRecords"], f"finding {finding_id} attemptRecords")
        require(
            after["lastSeenIteration"] >= before["lastSeenIteration"],
            f"finding {finding_id} lastSeenIteration cannot decrease",
        )
        require(
            set(before["evidence"]) <= set(after["evidence"]),
            f"finding {finding_id} evidence cannot be removed",
        )
        valid_status = after["status"] in FINDING_TRANSITIONS[before["status"]]
        if before["severity"] == "P3" and after["severity"] == "P3":
            valid_status = valid_status or (
                before["status"] in {"resolved", "rejected"} and after["status"] == "backlog"
            )
        if before["severity"] == "P3" and after["severity"] != "P3":
            valid_status = valid_status or after["status"] in {"confirmed", "planned", "remediating", "blocked"}
        require(valid_status, f"finding {finding_id} has invalid status transition {before['status']} -> {after['status']}")

    current_plans = keyed(current["plans"], "path")
    candidate_plans = keyed(candidate["plans"], "path")
    require(set(current_plans) <= set(candidate_plans), "plans cannot be removed")
    for plan_path in set(candidate_plans) - set(current_plans):
        require(candidate_plans[plan_path]["status"] == "draft", f"new plan {plan_path} must begin as draft")
    for plan_path, before in current_plans.items():
        after = candidate_plans[plan_path]
        for field in ("path", "repoRoot", "iteration"):
            require(after[field] == before[field], f"plan {plan_path} cannot change {field}")
        require(after["reviewPasses"] >= before["reviewPasses"], f"plan {plan_path} reviewPasses cannot decrease")
        require_prefix(before["commitShas"], after["commitShas"], f"plan {plan_path} commitShas")
        require_prefix(
            before["implementationCommitShas"],
            after["implementationCommitShas"],
            f"plan {plan_path} implementationCommitShas",
        )
        if after["implementationCommitSha"] != before["implementationCommitSha"]:
            require(
                after["reviewPasses"] > before["reviewPasses"],
                f"plan {plan_path} implementation revision requires a new review pass",
            )
        if before["status"] == "complete" and after["status"] == "complete":
            require(
                after["implementationCommitSha"] == before["implementationCommitSha"],
                f"plan {plan_path} implementationCommitSha requires a reopened review",
            )
        require(
            after["status"] in PLAN_TRANSITIONS[before["status"]],
            f"plan {plan_path} has invalid status transition {before['status']} -> {after['status']}",
        )

    current_prs = keyed(current["pullRequests"], "url")
    candidate_prs = keyed(candidate["pullRequests"], "url")
    require(set(current_prs) <= set(candidate_prs), "pullRequests cannot be removed")
    for url in set(candidate_prs) - set(current_prs):
        require(candidate_prs[url]["state"] == "open", f"new pull request {url} must begin open")
    for url, before in current_prs.items():
        after = candidate_prs[url]
        for field in ("number", "url", "iteration", "planPath", "targetBranch"):
            require(after[field] == before[field], f"pull request {url} cannot change {field}")
        require_prefix(before["headShas"], after["headShas"], f"pull request {url} headShas")
        require_prefix(before["planCommitShas"], after["planCommitShas"], f"pull request {url} planCommitShas")
        if before["state"] != "open":
            require(after["headSha"] == before["headSha"], f"pull request {url} headSha is frozen after close")
            require(after["planCommitSha"] == before["planCommitSha"], f"pull request {url} planCommitSha is frozen after close")
        if before["mergeSha"] is not None:
            require(after["mergeSha"] == before["mergeSha"], f"pull request {url} mergeSha cannot change")
        if before["targetCiSha"] is not None:
            require(after["targetCiSha"] == before["targetCiSha"], f"pull request {url} targetCiSha cannot change")
        if before["resolution"] is not None:
            require(after["resolution"] == before["resolution"], f"pull request {url} resolution cannot change")
        require(
            not before["mergeVerified"] or after["mergeVerified"],
            f"pull request {url} mergeVerified cannot revert",
        )
        require(
            not before["targetCiVerified"] or after["targetCiVerified"],
            f"pull request {url} targetCiVerified cannot revert",
        )
        require(
            after["state"] in PR_TRANSITIONS[before["state"]],
            f"pull request {url} has invalid state transition {before['state']} -> {after['state']}",
        )

    current_resources = {(item["kind"], item["identifier"]): item for item in current["resources"]}
    candidate_resources = {(item["kind"], item["identifier"]): item for item in candidate["resources"]}
    require(set(current_resources) <= set(candidate_resources), "resources cannot be removed")
    for resource_key, before in current_resources.items():
        after = candidate_resources[resource_key]
        require(after["owner"] == before["owner"], f"resource {resource_key} owner cannot change")
        require(
            after["status"] in RESOURCE_TRANSITIONS[before["status"]],
            f"resource {resource_key} has invalid status transition {before['status']} -> {after['status']}",
        )

    require_prefix(current["coveragePasses"], candidate["coveragePasses"], "coveragePasses")
    candidate_finding_by_id = keyed(candidate["findings"], "id")
    for coverage_pass in candidate["coveragePasses"][len(current["coveragePasses"]) :]:
        for finding_id, severity in coverage_pass["acceptedFindingSeverities"].items():
            require(
                candidate_finding_by_id[finding_id]["severity"] == severity,
                f"new coverage pass severity for {finding_id} must match current finding severity",
            )
    current_deployments = keyed(current["deployments"], "operationId")
    candidate_deployments = keyed(candidate["deployments"], "operationId")
    require(len(current_deployments) == len(current["deployments"]), "current deployments contain duplicate operationIds")
    require(len(candidate_deployments) == len(candidate["deployments"]), "deployments contain duplicate operationIds")
    require(set(current_deployments) <= set(candidate_deployments), "deployments cannot be removed")
    require(
        [item["operationId"] for item in candidate["deployments"][: len(current["deployments"])]]
        == [item["operationId"] for item in current["deployments"]],
        "deployment operation order cannot be removed or rewritten",
    )
    for operation_id in set(candidate_deployments) - set(current_deployments):
        require(
            candidate_deployments[operation_id]["status"] in {"pending", "deferred", "skipped"},
            f"new deployment {operation_id} must begin pending, deferred, or skipped",
        )
    for operation_id, before in current_deployments.items():
        after = candidate_deployments[operation_id]
        for field in ("operationId", "commit", "policy", "attemptedAt"):
            require(after[field] == before[field], f"deployment {operation_id} cannot change {field}")
        require(
            after["status"] in DEPLOYMENT_TRANSITIONS[before["status"]],
            f"deployment {operation_id} has invalid status transition {before['status']} -> {after['status']}",
        )
        for field in ("healthVerified", "readinessVerified"):
            require(not before[field] or after[field], f"deployment {operation_id} cannot revert {field}")
        if before["completedAt"] is not None:
            require(after["completedAt"] == before["completedAt"], f"deployment {operation_id} completedAt cannot change")
    require(
        candidate["status"] in RUN_TRANSITIONS[current["status"]],
        f"invalid run status transition {current['status']} -> {candidate['status']}",
    )
    for field in ("deploymentPolicy", "containersRunningAtStart"):
        require(candidate[field] == current[field], f"replace cannot change control field {field}")
    if current["containersRunningAtCloseout"] is not None:
        require(
            candidate["containersRunningAtCloseout"] == current["containersRunningAtCloseout"],
            "containersRunningAtCloseout cannot change after it is recorded",
        )
    if current["maxIterations"] is None:
        require(candidate["maxIterations"] is None, "an unlimited run cannot acquire maxIterations on resume")
    else:
        require(
            candidate["maxIterations"] is not None
            and candidate["maxIterations"] >= current["maxIterations"],
            "maxIterations may only increase",
        )
    require_prefix(current["verificationCommands"], candidate["verificationCommands"], "verificationCommands")


def atomic_write(path: Path, state: dict[str, Any]) -> None:
    descriptor: int | None = None
    temporary_name: str | None = None
    write_error: OSError | None = None
    cleanup_error: OSError | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
        temporary_name = None
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except OSError as error:
        write_error = error
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as error:
                cleanup_error = error
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            except OSError as error:
                cleanup_error = error
    if write_error is not None:
        raise StateError(f"cannot atomically write {path}: {write_error}") from write_error
    if cleanup_error is not None:
        raise StateError(f"cannot clean temporary state for {path}: {cleanup_error}") from cleanup_error


@contextmanager
def state_lock(path: Path):
    descriptor: int | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_name(f".{path.name}.lock")
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.chmod(lock_path, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    except OSError as error:
        raise StateError(f"cannot lock state {path}: {error}") from error
    finally:
        if descriptor is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
            except OSError as error:
                if sys.exc_info()[0] is None:
                    raise StateError(f"cannot unlock state {path}: {error}") from error


def command_init(arguments: argparse.Namespace) -> None:
    path = Path(arguments.path).expanduser().resolve()
    with state_lock(path):
        require(not path.exists(), f"state already exists: {path}")
        timestamp = now_iso()
        state = {
            "schemaVersion": SCHEMA_VERSION,
            "revision": 0,
            "runId": arguments.run_id,
            "repoRoot": str(Path(arguments.repo_root).resolve()),
            "targetBranch": arguments.target_branch,
            "originalScope": arguments.scope,
            "severityThreshold": "P2",
            "deploymentPolicy": arguments.deploy,
            "maxIterations": arguments.max_iterations,
            "containersRunningAtStart": arguments.containers_running,
            "containersRunningAtCloseout": None,
            "status": "active",
            "stage": "preflight",
            "iteration": 0,
            "baselineSha": arguments.baseline_sha,
            "currentSha": arguments.baseline_sha,
            "findings": [],
            "plans": [],
            "pullRequests": [],
            "deployments": [],
            "resources": [],
            "verificationCommands": [],
            "coveragePasses": [],
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        validate_state(state)
        atomic_write(path, state)
    print(path)


def command_validate(arguments: argparse.Namespace) -> None:
    path = Path(arguments.path).expanduser().resolve()
    validate_state(read_json(path))
    print(f"valid: {path}")


def command_replace(arguments: argparse.Namespace) -> None:
    path = Path(arguments.path).expanduser().resolve()
    candidate = validate_state(read_json(Path(arguments.candidate).expanduser().resolve()))
    with state_lock(path):
        current = validate_state(read_json(path))
        for field in ("schemaVersion", "runId", "repoRoot", "targetBranch", "originalScope", "severityThreshold", "createdAt"):
            require(candidate[field] == current[field], f"replace cannot change immutable field {field}")
        require(candidate["iteration"] >= current["iteration"], "replace cannot decrease iteration")
        require(candidate["revision"] == current["revision"], "replace candidate is stale")
        validate_transition(current, candidate)
        candidate["revision"] = current["revision"] + 1
        candidate["updatedAt"] = now_iso()
        validate_state(candidate)
        atomic_write(path, candidate)
    print(path)


def command_upsert_finding(arguments: argparse.Namespace) -> None:
    path = Path(arguments.path).expanduser().resolve()
    try:
        finding = json.loads(arguments.finding)
    except json.JSONDecodeError as error:
        raise StateError(f"--finding is not valid JSON: {error}") from error
    validate_finding(finding, 0)
    with state_lock(path):
        current = validate_state(read_json(path))
        candidate = copy.deepcopy(current)
        matching = next((index for index, item in enumerate(candidate["findings"]) if item["id"] == finding["id"]), None)
        if matching is None:
            candidate["findings"].append(finding)
        else:
            candidate["findings"][matching] = finding
        candidate["revision"] = current["revision"]
        validate_state(candidate)
        validate_transition(current, candidate)
        candidate["revision"] = current["revision"] + 1
        candidate["updatedAt"] = now_iso()
        validate_state(candidate)
        atomic_write(path, candidate)
    print(path)


def command_summary(arguments: argparse.Namespace) -> None:
    state = validate_state(read_json(Path(arguments.path).expanduser().resolve()))
    unresolved = [
        finding
        for finding in state["findings"]
        if finding["status"] in BLOCKING_FINDING_STATUSES or finding["status"] == "backlog"
    ]
    document = {
        "runId": state["runId"],
        "revision": state["revision"],
        "status": state["status"],
        "stage": state["stage"],
        "iteration": state["iteration"],
        "currentSha": state["currentSha"],
        "deploymentPolicy": state["deploymentPolicy"],
        "unresolved": [
            {"id": finding["id"], "severity": finding["severity"], "status": finding["status"]}
            for finding in unresolved
        ],
        "plans": len(state["plans"]),
        "pullRequests": len(state["pullRequests"]),
        "deployments": len(state["deployments"]),
        "coveragePasses": len(state["coveragePasses"]),
    }
    print(json.dumps(document, indent=2, sort_keys=True))


def command_state_path(arguments: argparse.Namespace) -> None:
    require(bool(RUN_ID_PATTERN.fullmatch(arguments.run_id)), "runId must be lowercase kebab-case")
    repo_root = Path(arguments.repo_root).expanduser().resolve()
    try:
        remote = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        remote = "no-origin"
    identity = f"{remote}\0{repo_root}".encode()
    repo_key = hashlib.sha256(identity).hexdigest()[:20]
    path = Path.home() / ".codex" / "state" / "bug-scrub-loop" / repo_key / f"{arguments.run_id}.json"
    print(path)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init")
    initialize.add_argument("--path", required=True)
    initialize.add_argument("--run-id", required=True)
    initialize.add_argument("--repo-root", required=True)
    initialize.add_argument("--target-branch", required=True)
    initialize.add_argument("--scope", required=True)
    initialize.add_argument("--baseline-sha", required=True)
    initialize.add_argument("--deploy", choices=sorted(DEPLOYMENT_POLICIES), default="final")
    initialize.add_argument("--max-iterations", type=int)
    initialize.add_argument("--containers-running", action="store_true")
    initialize.set_defaults(handler=command_init)
    validate = commands.add_parser("validate")
    validate.add_argument("--path", required=True)
    validate.set_defaults(handler=command_validate)
    replace = commands.add_parser("replace")
    replace.add_argument("--path", required=True)
    replace.add_argument("--candidate", required=True)
    replace.set_defaults(handler=command_replace)
    upsert_finding = commands.add_parser("upsert-finding")
    upsert_finding.add_argument("--path", required=True)
    upsert_finding.add_argument("--finding", required=True)
    upsert_finding.set_defaults(handler=command_upsert_finding)
    summary = commands.add_parser("summary")
    summary.add_argument("--path", required=True)
    summary.set_defaults(handler=command_summary)
    state_path = commands.add_parser("state-path")
    state_path.add_argument("--repo-root", required=True)
    state_path.add_argument("--run-id", required=True)
    state_path.set_defaults(handler=command_state_path)
    return root


def main() -> int:
    try:
        arguments = parser().parse_args()
        arguments.handler(arguments)
        return 0
    except StateError as error:
        print(f"run-state error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
