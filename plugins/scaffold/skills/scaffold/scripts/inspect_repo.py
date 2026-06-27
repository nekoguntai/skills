#!/usr/bin/env python3
"""Inspect a repo for scaffold-relevant CI and coverage facts."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}


def run(cmd: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_root(cwd: Path) -> Path:
    root = run(["git", "rev-parse", "--show-toplevel"], cwd)
    return Path(root) if root else cwd


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def walk_files(root: Path, max_depth: int = 4) -> list[Path]:
    files: list[Path] = []
    root_depth = len(root.parts)
    for current, dirs, names in os.walk(root):
        path = Path(current)
        depth = len(path.parts) - root_depth
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".cache")]
        if depth > max_depth:
            dirs[:] = []
            continue
        for name in names:
            files.append(path / name)
    return files


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def detect_host(root: Path, remotes: str | None) -> str:
    text = remotes or ""
    if "github.com" in text:
        return "github"
    if any(marker in text for marker in ("codeberg.org", "forgejo", "gitea")):
        return "forgejo"
    if (root / ".forgejo" / "workflows").exists():
        return "forgejo"
    if (root / ".github" / "workflows").exists():
        return "github"
    return "unknown"


def default_branch(root: Path) -> str | None:
    symbolic = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], root)
    if symbolic and "/" in symbolic:
        return symbolic.split("/", 1)[1]
    branches = run(["git", "branch", "--format", "%(refname:short)"], root) or ""
    for candidate in ("main", "master", "trunk"):
        if candidate in branches.splitlines():
            return candidate
    return None


def package_manager(root: Path) -> str | None:
    lockfiles = [
        ("package-lock.json", "npm"),
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lock", "bun"),
        ("bun.lockb", "bun"),
    ]
    for filename, manager in lockfiles:
        if (root / filename).exists():
            return manager
    return "npm" if (root / "package.json").exists() else None


def node_info(root: Path) -> dict[str, Any] | None:
    package = read_json(root / "package.json")
    if not package:
        return None
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    selected = {
        key: scripts[key]
        for key in sorted(scripts)
        if re.search(r"(^ci$|test|coverage|lint|typecheck|build|audit)", key)
    }
    workspaces = package.get("workspaces")
    return {
        "package_manager": package_manager(root),
        "node_engine": package.get("engines", {}).get("node")
        if isinstance(package.get("engines"), dict)
        else None,
        "workspaces": workspaces,
        "scripts": selected,
        "has_vitest": any((root / name).exists() for name in [
            "vitest.config.ts",
            "vitest.config.mts",
            "vitest.config.js",
            "vitest.config.mjs",
        ]),
        "has_jest": any((root / name).exists() for name in [
            "jest.config.js",
            "jest.config.cjs",
            "jest.config.mjs",
            "jest.config.ts",
        ]),
    }


def python_info(root: Path, files: list[Path]) -> dict[str, Any] | None:
    markers = [
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "uv.lock",
        "poetry.lock",
        "tox.ini",
        "noxfile.py",
        "pytest.ini",
        ".coveragerc",
    ]
    py_files = [p for p in files if p.suffix == ".py"]
    if not py_files and not any((root / marker).exists() for marker in markers):
        return None
    manager = "uv" if (root / "uv.lock").exists() else None
    if manager is None and (root / "poetry.lock").exists():
        manager = "poetry"
    if manager is None and (root / "pyproject.toml").exists():
        manager = "pyproject"
    if manager is None and (root / "requirements.txt").exists():
        manager = "pip"
    return {
        "manager": manager,
        "markers": [marker for marker in markers if (root / marker).exists()],
        "python_file_count": len(py_files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    args = parser.parse_args()

    cwd = Path.cwd().resolve()
    root = git_root(cwd).resolve()
    files = walk_files(root)
    remotes = run(["git", "remote", "-v"], root)
    host = detect_host(root, remotes)
    if host == "github":
        workflow_dir = ".github/workflows"
    elif host == "forgejo":
        workflow_dir = ".forgejo/workflows"
    else:
        workflow_dir = None
    refs = ["references/ci-baseline.md", "references/hosts.md"]

    node = node_info(root)
    if node:
        refs.append("references/node.md")
    python = python_info(root, files)
    if python:
        refs.append("references/python.md")

    docker_markers = [
        rel(path, root)
        for path in files
        if path.name in {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
    ]
    workflows = [
        rel(path, root)
        for path in files
        if "/workflows/" in rel(path, root) and path.suffix in {".yml", ".yaml"}
    ]

    data: dict[str, Any] = {
        "repo_root": root.as_posix(),
        "host": host,
        "default_branch": default_branch(root),
        "workflow_dir": workflow_dir,
        "existing_workflows": sorted(workflows),
        "references_to_read": refs,
        "node": node,
        "python": python,
        "docker_or_compose": sorted(docker_markers),
    }

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(f"repo_root: {data['repo_root']}")
        print(f"host: {host}")
        print(f"default_branch: {data['default_branch']}")
        print(f"workflow_dir: {workflow_dir}")
        print("references_to_read:")
        for item in refs:
            print(f"  - {item}")
        if node:
            print(f"node: {node['package_manager']} scripts={', '.join(node['scripts']) or 'none'}")
        if python:
            print(f"python: {python['manager']} markers={', '.join(python['markers']) or 'none'}")
        if docker_markers:
            print(f"docker_or_compose: {', '.join(sorted(docker_markers))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
