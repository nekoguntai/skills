# CI Baseline

Use this reference for every scaffold run. Keep the implementation portable and
repo-specific; prefer existing scripts and conventions over a generic template.

## Required Pipeline Shape

- Trigger on pull requests and pushes to the protected/default branch.
- Add `workflow_dispatch` for manual verification.
- Add a scheduled run for drift, dependency, and flaky-test visibility.
- Add `merge_group` only for GitHub repos that use merge queue.
- Set least-privilege permissions, usually `contents: read`.
- Add concurrency that cancels in-progress PR runs without canceling protected
  branch or scheduled runs.
- Use deterministic installs: `npm ci`, `pnpm install --frozen-lockfile`,
  `yarn install --immutable`, `bun install --frozen-lockfile`, `uv sync`, or the
  repo's established equivalent.

## Blocking Gates

Prefer one required job named `ci` for small repos. Split into named jobs for
larger repos, but require all jobs that protect correctness.

- lint/static policy checks;
- typecheck/compile;
- unit tests with 100% coverage;
- production build/package;
- dependency audit at a severity appropriate to the package manager;
- secret scan, usually gitleaks or an existing repo-owned scanner;
- workflow/config syntax validation;
- browser/e2e smoke when the repo has a browser app;
- container build and runtime smoke when Dockerfiles or Compose files are part
  of the supported product.

If a job is skipped by path classification, the job itself must still finish
successfully so required status checks do not disappear.

## Coverage Gate

Treat 100% coverage as an acceptance criterion, not a report. Enforce all four
coverage dimensions where the tool supports them: lines, branches, functions,
and statements.

Do:

- add tests for uncovered behavior and edge cases;
- use coverage reports to choose the next test;
- aggregate coverage across workspaces/packages before applying the threshold;
- keep generated/vendor/declaration exclusions explicit and minimal;
- document any impossible-to-execute exclusion in code or config.

Do not:

- lower thresholds;
- mark broad directories ignored because they are inconvenient;
- replace behavior tests with assertion-free import tests;
- accept 100% line coverage while branch/function coverage is below 100%;
- rely on CI-only environment behavior that cannot be reproduced locally.

## Convergence Loop

Use the same loop for coverage and CI:

1. Run the failing gate.
2. Extract the smallest actionable failure.
3. Fix source, tests, or config according to repo patterns.
4. Rerun the focused gate.
5. Rerun the full local gate after focused failures are gone.
6. Continue until green or until an external dependency, missing credential, or
   product decision blocks progress.

Report blockers with exact evidence and the command that failed.

## Branch Protection Requirements

The protected/default branch must require PR-based changes and passing CI before
merge. Configure:

- required pull request before merge;
- required status checks matching the CI workflow/job names;
- strict/up-to-date branch checks when supported;
- stale approval dismissal or equivalent review freshness;
- conversation resolution when supported;
- force pushes disabled;
- branch deletion disabled;
- no bypass for normal writers.

Branch protection is not complete until the live host configuration has been
read back and matches the expected policy.
