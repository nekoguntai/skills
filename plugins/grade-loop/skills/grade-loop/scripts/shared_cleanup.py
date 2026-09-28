"""Load the shared pr-delivery cleanup API without stale-provider fallback."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def _candidate_skill_dirs() -> list[Path]:
    explicit = os.environ.get("PR_DELIVERY_SKILL_DIR")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not (path / "scripts" / "loop_cleanup" / "core.py").is_file():
            raise ImportError("PR_DELIVERY_SKILL_DIR does not contain the shared cleanup provider")
        return [path]
    here = Path(__file__).resolve()
    plugins_dir = here.parents[4]
    source_sibling = plugins_dir / "pr-delivery" / "skills" / "pr-delivery"
    installed = Path.home() / ".codex" / "skills" / "pr-delivery"
    return [source_sibling, installed]


def load_shared_cleanup():
    for skill_dir in _candidate_skill_dirs():
        scripts = skill_dir / "scripts"
        if not (scripts / "loop_cleanup" / "core.py").is_file():
            continue
        scripts_text = str(scripts)
        if scripts_text not in sys.path:
            sys.path.insert(0, scripts_text)
        package = importlib.import_module("loop_cleanup")
        core = importlib.import_module("loop_cleanup.core")
        expected_package = (scripts / "loop_cleanup" / "__init__.py").resolve()
        actual_package = Path(package.__file__).resolve()
        if actual_package != expected_package:
            raise ImportError("loaded shared cleanup package does not match selected provider")
        if package.DELIVERY_CLEANUP_API_VERSION != 1:
            raise ImportError("unsupported pr-delivery cleanup API version")
        if core.DELIVERY_CLEANUP_API_VERSION != package.DELIVERY_CLEANUP_API_VERSION:
            raise ImportError("inconsistent pr-delivery cleanup API version")
        if package.DELIVERY_WORKFLOW_API_VERSION != 1:
            raise ImportError("unsupported pr-delivery workflow API version")
        return core
    raise ImportError("shared pr-delivery cleanup provider was not found")


core = load_shared_cleanup()
