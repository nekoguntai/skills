---
name: scaffold
description: >-
  Portable repository scaffolding for new or existing projects that need a
  standardized CI pipeline, 100% test coverage, rigorous quality/security gates,
  and PR-only protected-branch merges. Use when Codex is asked to bootstrap,
  harden, standardize, or repair CI/CD for GitHub or Forgejo repositories;
  configure branch protection or required checks; block direct pushes; add or
  fix coverage gates; or keep looping on tests and CI until the repo reaches a
  green, merge-blocking pipeline.
---

# Scaffold

Use this skill to turn a repository into a protected, PR-driven project with a
portable CI pipeline and a hard 100% coverage gate. The work is not complete
until local verification is green, required CI checks exist, branch protection is
configured or explicitly blocked by missing credentials, and direct pushes to the
target branch should fail.

## Context Budget

Start with the inspector, then read only the references it names:

```bash
python3 <skill-dir>/scripts/inspect_repo.py --json
```

Resolve `<skill-dir>` relative to this `SKILL.md` directory; plugin installs may
provide it as `${CLAUDE_SKILL_DIR}`. Always read `references/ci-baseline.md`.
Read `references/hosts.md` for GitHub/Forgejo enforcement. Read
`references/node.md` or `references/python.md` only when that ecosystem is
present.

## Workflow

1. Preflight the repository.
   - Read repo instructions such as `AGENTS.md`, `CLAUDE.md`, and CI docs.
   - Run `git status --short --branch`, `git branch --show-current`, and
     `git show -s --format='%h %D %s' HEAD`.
   - Preserve unrelated dirty work. Create a task branch before edits if the
     current branch is the target branch.
   - Determine the remote host, default branch, package managers, existing test
     scripts, workflow directory, and coverage tooling from the inspector.

2. Establish the local contract before writing workflow YAML.
   - Add or repair package-level commands so one stable command runs the full
     local gate, usually `ci`.
   - Add or repair a coverage command with 100% line, branch, function, and
     statement thresholds for every first-party package.
   - Keep exclusions narrow and defensible: generated files, type declarations,
     vendored code, migrations that cannot execute, and explicit platform
     shims. Do not exclude hard-to-test production code to satisfy the gate.

3. Run the 100% coverage loop until it passes.
   - Run the coverage command.
   - Read the missing-lines/branches report.
   - Add behavior-focused tests for the highest-value uncovered paths.
   - Refactor only when needed to make code testable without changing behavior.
   - Repeat until the 100% gate passes. Do not stop after one failed run unless
     an external blocker prevents meaningful progress.

4. Scaffold CI around the proven local contract.
   - Add or update `.github/workflows/ci.yml` for GitHub or
     `.forgejo/workflows/ci.yml` for Forgejo.
   - Include PR, protected-branch push, scheduled, and manual triggers where the
     host supports them.
   - Make skipped lanes still report success if their status check is required.
   - Include deterministic install, lint, typecheck, coverage, build, dependency
     audit, secret scan, and relevant smoke/e2e/container gates.

5. Verify locally.
   - Run the full local gate and all focused commands changed by the scaffold.
   - Run workflow syntax checks when available (`actionlint`, repo scripts, or
     host-specific validators).
   - Fix failures and rerun. Treat this as the same convergence loop as
     coverage.

6. Enforce PR-only merges.
   - Configure branch protection or rulesets for the target branch:
     required PR, required green status checks, stale-review handling, no force
     pushes, no deletions, and no bypass for normal writers.
   - Verify the live protection state through the host API or CLI. If credentials
     are unavailable, stop with exact host, branch, required checks, and the
     commands/UI settings needed; do not claim push blocking is done.
   - If the user asked to commit, push, open a PR, merge, or deliver the result,
     use `pr-delivery` after local verification.

## Done Criteria

The scaffold is complete only when:

- 100% coverage passes locally for all first-party code.
- The full local `ci` gate passes.
- The workflow exists for the detected host and exercises the same gate.
- Branch protection is verified live, or the final response identifies the
  precise missing permission/API blocker.
- Direct target-branch work has been avoided; changes are ready for a PR or have
  gone through `pr-delivery` when delivery was requested.
