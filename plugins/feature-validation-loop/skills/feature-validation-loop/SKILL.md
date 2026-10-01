---
name: feature-validation-loop
description: End-to-end product behavior validation loop for application repositories. Use when Codex is asked to discover user-facing features, create or maintain a canonical feature/test/defect spreadsheet, generate code-derived user stories and expected behavior, execute validation, document defects, fix functional or UX issues, retest, publish Prismatic Thread summaries, generate standalone validation HTML, or run a recursive QA validation loop.
---

# Feature Validation Loop

## Overview

The source of truth is a single CSV ledger; Markdown, JSON, and HTML outputs are
generated views.

Default ledger path:

```text
docs/feature-validation/feature-validation-ledger.csv
```

## Shared Loop Contract

Before delegated work or creating Git resources, resolve the `pr-delivery`
skill and read its [`references/loop-execution.md`](../../../pr-delivery/skills/pr-delivery/references/loop-execution.md)
and [`references/loop-run-state.md`](../../../pr-delivery/skills/pr-delivery/references/loop-run-state.md).
Set `PR_DELIVERY_SKILL_DIR` to the resolved skill directory for helper
invocations. Use its API 1 inventory provider and external durable state; if
the required helper is unavailable, stop before resource mutation instead of
creating a competing inventory implementation.

For a standalone run, initialize state after identifying the stable repository
root, target branch, and current target SHA, but before creating any branch or
worktree:

```bash
python3 "$PR_DELIVERY_SKILL_DIR/scripts/loop_state.py" init \
  --workflow feature-validation-loop --path <external-state-path> \
  --run-id <run-id> --repo-root <repo-root> \
  --target-branch <target-branch> --current-sha <target-sha>
```

The shared default is one complete pass. If the user explicitly requests a
recursive pass budget, pass that positive value as `--max-passes <N>` and honor
it. Keep state and archives outside every checkout/worktree. Archive canonical
CSV snapshots and required evidence through the helper, recording audit
references using the shared schema: phase `initial` or `post`, the live source
SHA, and a `report` reference to an archived report, plan, or evidence artifact.
History may be empty for this workflow. A clean outcome means the selected
validation pass meets its feature-validation acceptance criteria, not a grade
score. The CSV remains the canonical user-facing ledger; its external archive
is recovery evidence, never a replacement.

Nested runs inherit the caller's `state_helper`, `state_path`, `run_id`,
`iteration`, and `cleanup_policy: iteration-baseline`. Reuse that state and
baseline; do not create a nested run or absorb the caller's resources into a
new baseline. Return evidence to the caller without advancing its iteration or
completing its goal.

The shared audit schema above is for standalone runs. A nested workflow writes
only fields accepted by the caller's helper/schema. Settle its own resources
and return exact-resource absence evidence; do not append incompatible generic
audit records or call the caller's whole-run cleanup gate before parent-owned
resources have settled.

Strict read-only/no-files work does not initialize state or create resources.
The cleanup contract does not authorize a PR, merge, or external publication.
Generate local Prismatic Thread artifacts when requested and configured; send
or publish externally only when the current user request explicitly authorizes
it. If requested work cannot be safely cleaned without losing it or delivering
it without authorization, preserve it as blocked and resumable with the exact
reason.

## Resource Loading

- Read `references/discovery-guide.md` before starting feature discovery.
- Read `references/ledger-schema.md` before creating or changing ledger rows.
- Read `references/prismatic-thread.md` when `.prismatic-thread.yaml` exists or
  the user asks for Prismatic Thread integration.
- Use scripts from `scripts/` for deterministic ledger, HTML, and artifact work
  instead of hand-building generated files.
- Resolve `scripts/` and `references/` relative to this skill folder, the
  directory containing this `SKILL.md`. Do not run a target repository's own
  `scripts/ledger.py` by accident.

## Workflow

1. Preflight the repository.
   - Read repo instructions and active plans.
   - Capture branch, HEAD, dirty state, stack, routes, APIs, CLI entry points,
     config files, tests, and runtime requirements.
   - Preserve unrelated dirty work. Do not stage generated validation files
     without the user's delivery request.
   - Read the shared loop contracts and initialize standalone state after
     resolving the target branch/SHA, before creating any loop-owned resource.
2. Load or create the canonical ledger.
   - Run `ledger.py init` if the ledger does not exist.
   - Run `ledger.py validate` before and after updates.
   - Preserve every existing row, manual note, waiver, and reproduction record;
     make only evidence-backed edits required by this pass.
3. Discover code-derived features.
   - Inspect UI screens, routes, API endpoints, CLI commands, jobs, config
     switches, permissions, error states, empty/loading states, and integrations.
   - Record expected behavior based only on source code, tests, docs in the
     repo, or observed runtime behavior.
   - Cite source paths in every row. Mark uncertainty in `Assumptions`.
4. Generate tests in the ledger.
   - Cover happy path, error path, invalid input, permissions, persistence,
     performance notes, accessibility, and responsive behavior where relevant.
   - Store compact scenario IDs or readable scenario text in `Test Cases`.
5. Execute the selected pass.
   - Default to one complete bounded pass unless the user explicitly asks for a
     recursive budget.
   - Update each row immediately as `passed`, `failed`, `blocked`, or `waived`.
   - Record evidence commands, screenshots, requests, traces, or manual notes.
   - Record this pass's audit/evidence in shared state. Archive and verify
     required snapshots before removing any owned checkout or generated source.
     Preserve the requested CSV, HTML, and local integration outputs.
   - Use `initial` for the starting observation and `post` after completed
     remediation or delivery. A delivered pass requires a fresh post audit at
     the verified target SHA before cleanup.
6. Remediate verified defects.
   - Fix only reproducible functional, UX, workflow, validation, accessibility,
     data integrity, security, or clear performance defects.
   - Use the smallest safe code change and focused verification.
   - Do not implement speculative product preferences as defects.
   - Use bounded workers for independent source analysis, scenario/test
     additions, and implementation slices when available. Prefer `gpt-6-luna`
     or the cheapest suitable supported worker; escalate only when evidence
     shows a need for stronger architectural, security, or debugging skill.
     Workers may make local commits but never push, open PRs, merge, publish,
     edit the caller's operational ledger, or remove shared resources.
   - The coordinator verifies worker findings against current source, reviews
     every diff, integrates changes, and runs final checks on the combined
     final head. Worker results from earlier heads do not replace that review.
   - If this request explicitly authorizes PR delivery, group all compatible
     selected fixes and their tests into one reviewed PR for the pass. Split
     only for a concrete boundary such as distinct repositories, incompatible
     protection rules, required deployment/migration order, or a reviewed risk
     boundary. Internal phases and separate worker commits alone do not justify
     another PR. Without explicit delivery authorization, leave requested
     changes as local work product and do not push or merge.
7. Regress and publish.
   - Retest fixed and adjacent behavior.
   - Regenerate HTML and Prismatic Thread artifacts from the CSV.
   - Report coverage, defects found/fixed, open critical/high issues, waivers,
     confidence score, and blind spots.
   - “Publish” here means produce requested local artifacts. External publishing
     requires explicit authorization in the current request.

## Resource ownership and pass cleanup

The shared state ledger is the sole ownership record. Reserve every loop-created
branch, remote branch before its first push, worktree, worker/reviewer resource,
and companion-repository resource before creation. Preserve all resources in
the immutable initial baseline. Do not convert or carry a branch/worktree to a
later pass. At each pass boundary and every terminal exit—including an
initially clean result or exhausted budget—archive and verify required evidence,
settle workers, remove only safely removable owned resources, and run the
shared collaborator-tolerant cleanup gate: every owned resource verifiably gone
(ledger flags alone are not proof) and the primary checkout restored. Other
collaborators' branches and worktrees are reported, never cleaned or treated as
failures. Before finishing, settle our own forgotten resources listed by
`loop_state.py stale`.

The inventory check covers Git resources, not the desired ledger or generated
reports. Keep the canonical CSV and requested HTML/Prismatic artifacts as user
outputs. Do not remove or rewrite user changes to make cleanup pass. If a dirty,
unmerged, or otherwise unique resource cannot be safely removed without losing
requested work, retain it as blocked/resumable, state the exact cleanup blocker,
and do not report successful cleanup. Do not imply PR/merge authority to clean
it up.

For local-only validation, prefer the permitted pre-existing checkout so desired
CSV/HTML updates remain as user work product without a temporary branch. If an
isolated worktree is needed, bring requested outputs back to the permitted
checkout before removing the owned worktree. Do not delete requested artifacts
to satisfy the Git inventory check.

When a later pass is explicitly budgeted, advance only after the current pass
has passed cleanup verification. Refresh target SHA and audit evidence if the
target moved; when it did not move, the unchanged-target archived audit may be
reused as allowed by the shared contract. Do not repeat a full code inventory
solely to reconstruct lost evidence.

## Script Commands

Create or validate the ledger:

```bash
python3 <skill-dir>/scripts/ledger.py init --ledger docs/feature-validation/feature-validation-ledger.csv
python3 <skill-dir>/scripts/ledger.py validate --ledger docs/feature-validation/feature-validation-ledger.csv
python3 <skill-dir>/scripts/ledger.py summary --ledger docs/feature-validation/feature-validation-ledger.csv --json
```

Upsert one or more rows from JSON:

```bash
python3 <skill-dir>/scripts/ledger.py upsert \
  --ledger docs/feature-validation/feature-validation-ledger.csv \
  --row-json /tmp/features.json \
  --source-commit "$(git rev-parse --short HEAD)"
```

Generate the standalone HTML spreadsheet view:

```bash
python3 <skill-dir>/scripts/html_report.py \
  --ledger docs/feature-validation/feature-validation-ledger.csv \
  --output docs/feature-validation/feature-validation-ledger.html
```

Generate Prismatic Thread artifacts when configured:

```bash
python3 <skill-dir>/scripts/prismatic_artifact.py \
  --ledger docs/feature-validation/feature-validation-ledger.csv \
  --repo-root . \
  --write-html
```

## Ledger Rules

- Keep the CSV as the only canonical state in v1.
- Preserve existing rows by `Feature ID`, not by row order.
- Use stable IDs such as `FEAT-WEB-001`, `FEAT-API-001`, `FEAT-CLI-001`,
  `FEAT-CFG-001`, `FEAT-JOB-001`, and `FEAT-INT-001`.
- Preserve manual notes, waivers, and reproduction evidence unless the new
  evidence explicitly supersedes them.
- Sort rows deterministically by surface and feature ID.
- Keep generated HTML and Prismatic artifacts reproducible from the CSV.

## Completion Guardrails

- Never claim absolute full-product completeness unless every route, surface,
  permission level, runtime dependency, test-data path, and external integration
  was actually inspected or exercised.
- Prefer: `No undocumented features were found in the inspected source surfaces
  for this pass. Confidence: N%. Remaining blind spots: ...`
- Waive or block defects explicitly with reasons; do not silently drop them.
- If fixing defects, rerun the relevant tests and regenerate the derived
  artifacts after the final ledger update.
- A standalone run is complete only when the selected pass meets its full
  ledger, execution, defect disposition, regression, and requested local-output
  criteria and every owned Git resource is gone. Leave remaining
  findings deferred with a reason at budget end; blocked cleanup stays
  resumable and is not successful completion.
