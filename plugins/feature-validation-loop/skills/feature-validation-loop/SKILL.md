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
2. Load or create the canonical ledger.
   - Run `ledger.py init` if the ledger does not exist.
   - Run `ledger.py validate` before and after updates.
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
6. Remediate verified defects.
   - Fix only reproducible functional, UX, workflow, validation, accessibility,
     data integrity, security, or clear performance defects.
   - Use the smallest safe code change and focused verification.
   - Do not implement speculative product preferences as defects.
7. Regress and publish.
   - Retest fixed and adjacent behavior.
   - Regenerate HTML and Prismatic Thread artifacts from the CSV.
   - Report coverage, defects found/fixed, open critical/high issues, waivers,
     confidence score, and blind spots.

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
