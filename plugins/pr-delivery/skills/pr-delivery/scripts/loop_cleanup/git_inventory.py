#!/usr/bin/env python3
"""Capture and verify the names and assignments that a Git cleanup could remove."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

COMMAND_TIMEOUT_SECONDS = 15


class InventoryError(RuntimeError):
    """Raised when Git state cannot be inventoried reliably."""


def _git(repo_root: str, *args: str, timeout: int = COMMAND_TIMEOUT_SECONDS) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InventoryError(f"git {' '.join(args[:2])} failed or timed out") from exc
    if result.returncode:
        raise InventoryError(f"git {' '.join(args[:2])} failed (exit {result.returncode})")
    return result.stdout


def _text(value: bytes, context: str) -> str:
    try:
        return value.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise InventoryError(f"{context} is not valid UTF-8") from exc


def _git_dirs(repo_root: str) -> tuple[str, str]:
    top = _text(_git(repo_root, "rev-parse", "--show-toplevel"), "repository root")
    common = _text(_git(repo_root, "rev-parse", "--git-common-dir"), "common Git directory")
    top_path = Path(top).resolve(strict=True)
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = Path(repo_root, common_path)
    return str(top_path), str(common_path.resolve(strict=True))


def _local_branches(repo_root: str) -> list[str]:
    data = _git(repo_root, "for-each-ref", "--format=%(refname:strip=2)", "refs/heads")
    try:
        return sorted(line.decode("utf-8") for line in data.splitlines())
    except UnicodeDecodeError as exc:
        raise InventoryError("local branch inventory is not valid UTF-8") from exc


def _remote_endpoints(repo_root: str, remote: str) -> list[tuple[str, str]]:
    endpoints: list[tuple[str, str]] = []
    for mode in ("fetch", "push"):
        raw = _git(repo_root, "remote", "get-url", "--all", *( ["--push"] if mode == "push" else []), remote)
        urls = [_text(line, "remote endpoint") for line in raw.splitlines() if line]
        endpoints.extend((mode, url) for url in urls)
    if not endpoints:
        raise InventoryError("configured remote has no usable endpoint")
    return endpoints


def _remote_branches(repo_root: str) -> list[dict[str, Any]]:
    remotes = _text(_git(repo_root, "remote"), "remote names").splitlines()
    inventory: list[dict[str, Any]] = []
    for remote in sorted(remotes):
        seen: set[str] = set()
        for mode, endpoint in _remote_endpoints(repo_root, remote):
            # A push URL can equal the fetch URL; query each endpoint only once.
            if endpoint in seen:
                continue
            seen.add(endpoint)
            try:
                listing = subprocess.run(
                    ["git", "-C", repo_root, "ls-remote", "--heads", "--", endpoint],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=COMMAND_TIMEOUT_SECONDS,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise InventoryError("remote branch inventory failed or timed out") from exc
            if listing.returncode:
                raise InventoryError("remote branch inventory failed")
            branches: set[str] = set()
            try:
                for line in listing.stdout.decode("utf-8").splitlines():
                    fields = line.split("\t", 1)
                    if len(fields) != 2 or not fields[1].startswith("refs/heads/"):
                        raise InventoryError("remote returned malformed branch inventory")
                    branches.add(fields[1][len("refs/heads/"):])
            except UnicodeDecodeError as exc:
                raise InventoryError("remote branch inventory is not valid UTF-8") from exc
            inventory.append({
                "remote": remote,
                "endpoint": hashlib.sha256(endpoint.encode("utf-8")).hexdigest(),
                "branches": sorted(branches),
            })
    return sorted(inventory, key=lambda entry: (entry["remote"], entry["endpoint"]))


def _worktrees(repo_root: str) -> list[dict[str, Any]]:
    data = _git(repo_root, "worktree", "list", "--porcelain", "-z")
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    try:
        fields = data.decode("utf-8").split("\0")
    except UnicodeDecodeError as exc:
        raise InventoryError("worktree inventory is not valid UTF-8") from exc
    for field in fields:
        if not field:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = field.partition(" ")
        current[key] = value
    if current:
        records.append(current)
    worktrees = []
    for record in records:
        path = record.get("worktree")
        if not path:
            raise InventoryError("worktree inventory omitted a path")
        resolved = str(Path(path).resolve())
        branch = record.get("branch")
        if branch and branch.startswith("refs/heads/"):
            branch = branch[len("refs/heads/"):]
        worktrees.append({
            "path": resolved,
            "branch": branch,
            "detached": "detached" in record,
            "bare": "bare" in record,
            "prunable": "prunable" in record,
            "exists": Path(resolved).is_dir(),
        })
    return sorted(worktrees, key=lambda item: item["path"])


def capture(repo_root: str | os.PathLike[str]) -> dict[str, Any]:
    """Return a SHA-independent inventory of branches, remotes, and worktrees."""
    try:
        root_arg = str(Path(repo_root).expanduser().resolve(strict=True))
        top, common = _git_dirs(root_arg)
        return {
            "version": 1,
            "root": top,
            "common_git_dir": common,
            "local_branches": _local_branches(root_arg),
            "remote_branches": _remote_branches(root_arg),
            "worktrees": _worktrees(root_arg),
        }
    except InventoryError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise InventoryError("repository inventory failed") from exc


def _require_names(value: Any, label: str) -> None:
    if not isinstance(value, list) or not all(isinstance(name, str) and name for name in value):
        raise InventoryError(f"inventory {label} must contain nonempty names")
    if value != sorted(set(value)):
        raise InventoryError(f"inventory {label} must be unique and sorted")


def _validate_remote(remote: Any) -> tuple[str, str]:
    fields = {"remote", "endpoint", "branches"}
    if not isinstance(remote, dict) or set(remote) != fields:
        raise InventoryError("malformed remote branch inventory")
    name, endpoint = remote["remote"], remote["endpoint"]
    if not isinstance(name, str) or not name:
        raise InventoryError("remote name must be nonempty")
    if (not isinstance(endpoint, str) or len(endpoint) != 64
            or any(char not in "0123456789abcdef" for char in endpoint)):
        raise InventoryError("remote endpoint fingerprint is malformed")
    _require_names(remote["branches"], "remote branches")
    return name, endpoint


def _validate_remotes(remotes: Any) -> None:
    if not isinstance(remotes, list):
        raise InventoryError("inventory remote_branches must be an array")
    identities = [_validate_remote(remote) for remote in remotes]
    if len(identities) != len(set(identities)):
        raise InventoryError("remote endpoint pairs must be unique")


def _validate_worktree(tree: Any) -> str:
    fields = {"path", "branch", "detached", "bare", "prunable", "exists"}
    if not isinstance(tree, dict) or set(tree) != fields:
        raise InventoryError("malformed worktree inventory")
    path, branch = tree["path"], tree["branch"]
    if not isinstance(path, str) or not path or not Path(path).is_absolute():
        raise InventoryError("worktree path must be a nonempty absolute path")
    if branch is not None and (not isinstance(branch, str) or not branch):
        raise InventoryError("worktree branch must be null or a nonempty name")
    bool_fields = ("detached", "bare", "prunable", "exists")
    if any(type(tree[field]) is not bool for field in bool_fields):
        raise InventoryError("worktree flags must be booleans")
    return path


def _validate_worktrees(worktrees: Any) -> None:
    if not isinstance(worktrees, list):
        raise InventoryError("inventory worktrees must be an array")
    paths = [_validate_worktree(tree) for tree in worktrees]
    if len(paths) != len(set(paths)):
        raise InventoryError("worktree paths must be unique")


def validate_inventory(value: Any) -> dict[str, Any]:
    """Validate the public inventory shape and return it unchanged."""
    fields = {"version", "root", "common_git_dir", "local_branches", "remote_branches", "worktrees"}
    if not isinstance(value, dict) or set(value) != fields or value.get("version") != 1:
        raise InventoryError("malformed inventory baseline fields")
    for key in ("root", "common_git_dir"):
        if not isinstance(value[key], str) or not value[key] or not Path(value[key]).is_absolute():
            raise InventoryError(f"inventory {key} must be a nonempty absolute path")
    _require_names(value["local_branches"], "local_branches")
    _validate_remotes(value["remote_branches"])
    _validate_worktrees(value["worktrees"])
    return value


def _render_change(label: str, added: set[str], removed: set[str]) -> str | None:
    if not added and not removed:
        return None
    return f"{label} added={sorted(added)} removed={sorted(removed)}"


def _remote_changes(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    before = {(item["remote"], item["endpoint"]): set(item["branches"]) for item in baseline["remote_branches"]}
    after = {(item["remote"], item["endpoint"]): set(item["branches"]) for item in current["remote_branches"]}
    changes = []
    for key in sorted(set(after) - set(before)):
        changes.append(f"remote endpoint added: {key[0]} ({key[1]})")
    for key in sorted(set(before) - set(after)):
        changes.append(f"remote endpoint removed: {key[0]} ({key[1]})")
    for key in sorted(set(before) | set(after)):
        if key not in before or key not in after:
            continue
        description = f"remote {key[0]} endpoint {key[1]} branches"
        change = _render_change(description, after.get(key, set()) - before.get(key, set()),
                                before.get(key, set()) - after.get(key, set()))
        if change:
            changes.append(change)
    return changes


def _worktree_changes(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    before = {item["path"]: item for item in baseline["worktrees"]}
    after = {item["path"]: item for item in current["worktrees"]}
    changes = []
    change = _render_change("worktree paths", set(after) - set(before), set(before) - set(after))
    if change:
        changes.append(change)
    for path in sorted(set(before) & set(after)):
        if before[path] != after[path]:
            changes.append(f"worktree assignment changed at {path}")
    return changes


def _inventory_differences(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    changes = []
    if baseline["root"] != current["root"]:
        changes.append(f"root changed: {baseline['root']} -> {current['root']}")
    if baseline["common_git_dir"] != current["common_git_dir"]:
        changes.append("common Git directory changed")
    branch_change = _render_change("local branches", set(current["local_branches"]) - set(baseline["local_branches"]),
                                   set(baseline["local_branches"]) - set(current["local_branches"]))
    if branch_change:
        changes.append(branch_change)
    changes.extend(_remote_changes(baseline, current))
    changes.extend(_worktree_changes(baseline, current))
    return changes


def owned_resource_present(resource: dict[str, Any], current: dict[str, Any]) -> bool:
    """Whether an owned resource record still exists in a live inventory."""
    name = resource.get("identifier")
    kind = resource.get("kind")
    if kind == "local-branch":
        return name in current["local_branches"]
    if kind == "worktree":
        return any(item["path"] == str(Path(str(name)).resolve()) for item in current["worktrees"])
    if kind == "remote-branch":
        return any(item["remote"] == resource.get("remote") and name in item["branches"]
                   for item in current["remote_branches"])
    raise InventoryError(f"unknown owned resource kind: {kind}")


def _primary_assignment(inventory: dict[str, Any]) -> dict[str, Any] | None:
    return next((item for item in inventory["worktrees"] if item["path"] == inventory["root"]), None)


def verify(baseline: dict[str, Any], owned: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Verify a loop left no owned resource behind, tolerating collaborators.

    Several agents and people share a repository, so branches and worktrees
    that this loop does not own may appear or disappear while it runs. The
    gate fails only for what this loop is responsible for: an owned resource
    that still exists, a changed repository identity, or a primary checkout
    left on a different branch. Every other difference from the starting
    inventory is returned as ``collaborator_changes`` for the report and is
    never cleaned by this loop.
    """
    validate_inventory(baseline)
    if not Path(baseline["root"]).is_dir():
        raise InventoryError(f"baseline repository root is missing: {baseline['root']}")
    current = capture(baseline["root"])
    failures = []
    if baseline["root"] != current["root"]:
        failures.append(f"root changed: {baseline['root']} -> {current['root']}")
    if baseline["common_git_dir"] != current["common_git_dir"]:
        failures.append("common Git directory changed")
    if _primary_assignment(baseline) != _primary_assignment(current):
        failures.append(f"primary checkout assignment changed at {baseline['root']}")
    leftovers = sorted(f"{item['kind']} {item['identifier']}" for item in owned or [] if owned_resource_present(item, current))
    if leftovers:
        failures.append("owned resources remain: " + ", ".join(leftovers))
    if failures:
        raise InventoryError("Git inventory cleanup failed: " + "; ".join(failures))
    return {"ok": True, "inventory": current, "collaborator_changes": _inventory_differences(baseline, current)}


def _read_baseline(path: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as stream:
            baseline = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError("could not read inventory baseline") from exc
    if not isinstance(baseline, dict):
        raise InventoryError("inventory baseline must be a JSON object")
    return baseline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture_parser = commands.add_parser("capture")
    capture_parser.add_argument("--repo-root", required=True)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--baseline", required=True)
    verify_parser.add_argument("--owned", help="JSON file listing this loop's resources (kind, identifier, remote)")
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            result = capture(args.repo_root)
        else:
            owned = json.loads(Path(args.owned).read_text(encoding="utf-8")) if args.owned else None
            result = verify(_read_baseline(args.baseline), owned)
    except (InventoryError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
