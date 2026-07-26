# Run-State Schema

Use `scripts/run_state.py` to initialize, validate, summarize, and atomically replace this JSON document. Do not edit the live state file in place.
Initialization and replacement use a sibling lock file to prevent concurrent lost updates.

## Contents

- Top-level fields
- Finding
- Plan
- Pull request
- Deployment
- Owned resource
- Coverage passes

## Top-level fields

- Identity: `schemaVersion`, monotonic `revision`, `runId`, absolute `repoRoot`, `targetBranch`, `originalScope`, `severityThreshold`.
- Controls: `deploymentPolicy`, nullable `maxIterations`,
  `containersRunningAtStart`, and nullable `containersRunningAtCloseout`.
- Progress: `status`, `stage`, `iteration`, `baselineSha`, `currentSha`.
- Evidence arrays: `findings`, `plans`, `pullRequests`, `deployments`, `resources`, `verificationCommands`, `coveragePasses`.
- Timestamps: `createdAt`, `updatedAt`.

The validator treats identity, scope, target, threshold, and creation timestamp
as immutable during atomic replacement. Replacement rejects a stale revision
and increments it while holding the sibling state lock.

## Finding

```json
{
  "id": "repository-owner--lost-update",
  "fingerprint": "repository-owner|two-disjoint-updates|lost-update",
  "severity": "P1",
  "title": "Concurrent partial updates lose data",
  "owner": "src/lib/repository/example.ts",
  "trigger": "two disjoint updates overlap",
  "status": "confirmed",
  "attempts": 0,
  "attemptRecords": [],
  "firstSeenIteration": 1,
  "lastSeenIteration": 1,
  "disposition": null,
  "evidence": ["file:line", "focused reproduction"]
}
```

Use `confirmed`, `planned`, `remediating`, `resolved`, `blocked`, or
`rejected` for P0-P2. Use `backlog`, `resolved`, or `rejected` for P3.
`attempts` must equal the append-only `attemptRecords` count. Each record names
an exact plan path, plan commit SHA, and verified merge SHA. Resolution or
rejection requires a disposition.

## Plan

```json
{
  "path": "/absolute/path/to/plan.md",
  "repoRoot": "/absolute/plan/repository",
  "iteration": 1,
  "status": "reviewed",
  "reviewPasses": 2,
  "commitShas": [
    "2222222222222222222222222222222222222222",
    "5555555555555555555555555555555555555555"
  ],
  "implementationCommitSha": "2222222222222222222222222222222222222222",
  "implementationCommitShas": [
    "2222222222222222222222222222222222222222"
  ]
}
```

Plan status is `draft`, `reviewed`, `implementing`, `complete`, or
`superseded`. `commitShas` includes review and post-merge closeout revisions;
`implementationCommitShas` includes only converged revisions intended for
delivery. Completion requires verified delivery of the current
`implementationCommitSha`, not of a later documentation-only commit.

## Pull request

```json
{
  "number": 123,
  "url": "https://forge.example/repo/pulls/123",
  "iteration": 1,
  "planPath": "/absolute/path/to/plan.md",
  "targetBranch": "main",
  "state": "merged",
  "headSha": "0000000000000000000000000000000000000000",
  "headShas": [
    "3333333333333333333333333333333333333333",
    "0000000000000000000000000000000000000000"
  ],
  "planCommitSha": "2222222222222222222222222222222222222222",
  "planCommitShas": [
    "2222222222222222222222222222222222222222"
  ],
  "mergeSha": "1111111111111111111111111111111111111111",
  "mergeVerified": true,
  "targetCiVerified": true,
  "targetCiSha": "1111111111111111111111111111111111111111",
  "resolution": null
}
```

Merged PRs must have verified target ancestry and target-branch CI before run
completion. A closed unmerged PR requires a non-empty resolution. Open PRs may
append follow-up heads; the final head freezes after merge or closure.

## Deployment

```json
{
  "operationId": "deploy-iteration-2-final",
  "commit": "1111111111111111111111111111111111111111",
  "policy": "final",
  "status": "success",
  "attemptedAt": "2026-07-26T10:00:00Z",
  "completedAt": "2026-07-26T10:03:00Z",
  "healthVerified": true,
  "readinessVerified": true,
  "details": "repository deploy command completed"
}
```

Use `pending`, `uncertain`, `deferred`, `success`, `skipped`, or `failed`.
Persist `pending` before invoking a rebuild and update that same operation
after verification. A successful deployment
requires both verification fields. Final completion requires deployment-policy
evidence for `currentSha`, including an explicit `skipped` record when policy
or stopped containers intentionally prevent deployment.

## Owned resource

```json
{
  "kind": "worktree",
  "identifier": "/absolute/path/to/worktree",
  "owner": "bug-scrub-loop-run-id",
  "status": "active"
}
```

Resource status is `active`, `cleaned`, `preserved`, or `converted`.

## Coverage passes

See `scrub-coverage-contract.md` for `coveragePasses`.
