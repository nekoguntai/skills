#!/usr/bin/env python3
"""Compatibility API and CLI for shared Git inventory capture and verification."""

from __future__ import annotations

from shared_cleanup import core as _core  # bootstraps the provider path
from loop_cleanup.git_inventory import *  # noqa: F401,F403
from loop_cleanup.git_inventory import main as _shared_main


def main(argv: list[str] | None = None) -> int:
    return _shared_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
