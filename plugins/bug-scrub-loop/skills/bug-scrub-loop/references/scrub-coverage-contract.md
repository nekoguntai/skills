# Scrub Coverage Contract

Use this contract for every discovery pass. A zero-finding result is not a
clean pass unless the corresponding coverage pass validates.

## Required domains

Record exactly these domains:

- `trust-boundaries`: authentication, authorization, tenancy, uploads,
  downloads, secrets, environment parsing, and untrusted input.
- `persistence`: repositories, transactions, migrations, concurrency,
  idempotency, retention, nullability, and destructive state transitions.
- `api-contracts`: schemas, status codes, pagination, sorting, dates, money,
  rounding, serialization, and caller/version drift.
- `async-lifecycle`: queues, workers, retries, cancellation, timers, cleanup,
  webhooks, and resource ownership.
- `frontend-state`: forms, optimistic state, cache refresh, loading/disabled
  behavior, URL state, empty/error states, navigation, and blocked workflows.
- `error-handling`: swallowed errors, unsafe details, partial failure,
  compensation, retry storms, and missing observability.
- `tests-ci`: isolation, fixtures, unsafe entry points, flaky setup, missing
  regression ownership, and workflow contract drift.
- `recent-changes`: merged changes since the prior clean baseline, impacted
  callers, compatibility seams, and generated artifacts.

Mark a domain `inspected`, `excluded`, or `blocked`.

- `inspected` requires concrete paths and evidence such as searches, source
  reads, focused tests, logs, or caller traces.
- `excluded` requires a repository-specific reason showing the domain is not
  present or is outside the user-locked scope.
- `blocked` requires the exact missing access, artifact, policy, or runtime
  dependency. A blocked domain prevents a clean pass.

## Pass manifest

Append one `coveragePasses` entry to the run-state ledger:

```json
{
  "iteration": 1,
  "sha": "0000000000000000000000000000000000000000",
  "kind": "initial",
  "complete": false,
  "acceptedFindingIds": ["repository-owner--lost-update"],
  "acceptedFindingSeverities": {
    "repository-owner--lost-update": "P1"
  },
  "blockingFindingIds": ["repository-owner--lost-update"],
  "domains": [
    {
      "name": "trust-boundaries",
      "status": "inspected",
      "paths": ["src/app/api", "src/lib/security.ts"],
      "evidence": ["rg auth/permission/upload inventory", "route caller review"],
      "reason": null
    }
  ],
  "gaps": []
}
```

Include all eight domains exactly once. Set `complete: true` only when:

- every domain is inspected or validly excluded;
- no material evidence gap remains;
- every accepted P0-P2 candidate was reconfirmed by the coordinator;
- every shard result has been deduplicated and reconciled; and
- the manifest SHA equals the target-branch SHA actually scrubbed.

Use `kind: "initial"` for the first pass and `kind: "rescrub"` afterward.
Accepted IDs must reference findings already upserted in state. Snapshot each
accepted finding's severity in `acceptedFindingSeverities`; its keys must equal
the accepted IDs. Blocking IDs must equal the accepted IDs whose pass-local
severity is P0-P2. The final clean pass must match the run's current iteration
and SHA and cannot accept a P0-P2 finding.

The run-state validator enforces the structural portion of this contract.
