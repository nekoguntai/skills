# Ledger Schema

The canonical ledger is:

```text
docs/feature-validation/feature-validation-ledger.csv
```

Generated JSON, Markdown, and HTML are derived from this CSV. Do not treat them
as source of truth.

## Required Columns

| Column | Purpose |
| --- | --- |
| `Feature ID` | Stable ID such as `FEAT-WEB-001`, `FEAT-API-001`, `FEAT-CLI-001`, `FEAT-CFG-001`, `FEAT-JOB-001`, or `FEAT-INT-001` |
| `Feature Name` | Short human-readable feature label |
| `Surface` | UI screen, route, API, CLI, config, workflow, job, integration, or business process |
| `Source Paths` | Semicolon-separated code paths used as evidence |
| `User Story` | User story derived from implemented behavior |
| `Expected Behavior` | Expected behavior based solely on current code implementation |
| `Edge Cases` | Null, empty, boundary, permission, error, and responsive cases |
| `Validation Rules` | Input rules, auth rules, state guards, schema constraints, or business rules |
| `Dependencies` | Services, stores, DB tables, env vars, permissions, flags, jobs, or external APIs |
| `Assumptions` | Explicit uncertainty or inferred behavior |
| `Test Cases` | Compact scenario list or IDs for generated tests |
| `Execution Status` | One of `not_run`, `running`, `passed`, `failed`, `blocked`, `waived` |
| `Current Status` | One of `discovered`, `test_designed`, `testing`, `passed`, `failed`, `fixing`, `fixed_pending_retest`, `waived`, `blocked`, `complete` |
| `Defect IDs` | Stable defect IDs such as `DEF-FEAT-WEB-001-001` |
| `Defect Count` | Count of linked defects |
| `Max Severity` | One of `critical`, `high`, `medium`, `low`, `ux`, `none` |
| `Reproduction Notes` | Current failing repro or reason blocked |
| `Fix Status` | One of `none`, `planned`, `in_progress`, `fixed`, `deferred`, `waived` |
| `Verification Notes` | Commands, screenshots, API calls, or manual evidence |
| `Last Tested Date` | ISO date for latest execution |
| `Last Source Commit` | Short SHA used for last update |
| `Confidence` | `high`, `medium`, or `low` coverage confidence for the row |
| `Notes` | Additional review notes |

## ID Rules

- Allocate by surface prefix: web/UI = `WEB`, API = `API`, CLI = `CLI`,
  config/env = `CFG`, jobs = `JOB`, integrations = `INT`, workflows = `WF`,
  unknown = `GEN`.
- Preserve existing IDs once assigned.
- Use `ledger.py allocate-id --surface <surface>` when choosing a new ID.
- Use stable defect IDs that include the feature ID, for example
  `DEF-FEAT-WEB-001-001`.

## Update Rules

- Upsert by `Feature ID`; never rely on row order.
- Preserve manual notes, waivers, and evidence unless new evidence explicitly
  supersedes them.
- Keep `Defect Count` consistent with `Defect IDs`.
- Use `waived` only with a reason in `Notes` or `Reproduction Notes`.
- Use `blocked` only with the missing dependency, credential, service, or test
  data recorded.
- Sort deterministically by surface and feature ID.

## Script Examples

Initialize:

```bash
python3 <skill-dir>/scripts/ledger.py init --ledger docs/feature-validation/feature-validation-ledger.csv
```

Upsert:

```json
[
  {
    "Feature Name": "Project validation summary",
    "Surface": "web project detail",
    "Source Paths": "apps/web/app/project-detail.tsx",
    "User Story": "As an operator, I can see validation status for a project.",
    "Expected Behavior": "Project detail shows validation metrics when a validation artifact exists.",
    "Current Status": "discovered",
    "Execution Status": "not_run",
    "Max Severity": "none",
    "Confidence": "medium"
  }
]
```

```bash
python3 <skill-dir>/scripts/ledger.py upsert --row-json /tmp/features.json --source-commit "$(git rev-parse --short HEAD)"
```
