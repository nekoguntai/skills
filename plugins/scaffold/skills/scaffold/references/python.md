# Python Projects

Read this when `pyproject.toml`, `requirements*.txt`, `tox.ini`, `noxfile.py`,
or Python source packages are present.

## Environment

Prefer the repo's existing tool:

- `uv.lock` or existing `uv` commands: `uv sync --all-extras` or the repo's
  established `uv sync` command;
- Poetry: `poetry install --sync`;
- Hatch/PDM/tox/nox: use the repo's configured environment runner;
- plain pip: install from locked requirements where present.

Use the Python version declared in `requires-python`, `.python-version`,
`runtime.txt`, or existing CI. If none exists, choose a current stable version
compatible with dependencies.

## Coverage Configuration

Use `pytest-cov` or `coverage.py` with branch coverage and `fail_under = 100`.
Prefer `pyproject.toml` for new config:

```toml
[tool.pytest.ini_options]
addopts = "--cov --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=100"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["src"]

[tool.coverage.report]
fail_under = 100
show_missing = true
skip_covered = false
exclude_also = [
  "if TYPE_CHECKING:",
  "if __name__ == .__main__.:",
]
```

Adjust `source` for the actual first-party package layout. Avoid omitting
modules because they are hard to test.

## CI Gate

A typical `uv` pipeline:

```bash
uv sync --all-extras
uv run ruff check .
uv run mypy .
uv run pytest
uv run pip-audit --progress-spinner off
```

Use the repo's actual lint/type tools. If the repo has no lint/type tooling,
add the smallest conventional setup that fits the project, then enforce it in
the local `ci` gate and workflow.

## Test Development

Use coverage missing-branch output to drive tests. Add tests for:

- validation and error paths;
- file/network boundary failures using fakes;
- serialization/deserialization edge cases;
- CLI argument errors and exit codes;
- async cancellation/timeouts when relevant;
- configuration defaults and environment parsing.

When code is untestable due to import-time side effects or hardwired global I/O,
refactor behind small injectable functions and preserve behavior with tests.
