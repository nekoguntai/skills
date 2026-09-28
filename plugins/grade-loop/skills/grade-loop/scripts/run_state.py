#!/usr/bin/env python3
"""Grade-loop compatibility entry point for shared workflow state."""

import shared_cleanup  # Adds and validates the selected pr-delivery provider.
from loop_cleanup.workflow_cli import main


if __name__ == "__main__":
    raise SystemExit(main(default_workflow="grade-loop"))
