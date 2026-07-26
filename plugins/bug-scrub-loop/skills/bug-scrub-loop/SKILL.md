---
name: bug-scrub-loop
description: Autonomous evidence-driven remediation loop with durable run state and measurable scrub coverage. Runs a fresh bug scrub, creates and recursively reviews an executable fix plan for every confirmed P0-P2 finding, implements and merges that exact plan through implement-merge, then rescrubs the locked scope until a complete pass finds no P0, P1, or P2 bugs. Use when the user invokes $bug-scrub-loop, asks to scrub-plan-fix-merge repeatedly, wants resumable bug remediation through merged PRs, or requests dry-run or deployment-controlled bug-loop execution.
---

# Bug Scrub Loop

Drive one repository from evidence-backed bug discovery to a verified clean
P0-P2 termination gate. Preserve `$bug-scrub` as the analysis primitive and
use this skill only for the autonomous orchestration layer.

## Invocation Contract

Treat a bare `$bug-scrub-loop` invocation as explicit authorization to:

- run read-only repository scrubs;
- create and edit remediation plans in repository-approved locations;
- implement the reviewed plans;
- commit, push, open, monitor, and merge owned PRs;
- verify target-branch CI and clean owned branches/worktrees; and
- apply the selected deployment policy only to an already-running relevant
  local stack through the repository's documented command.

Use bounded read-only subagents for scrub shards and independent plan or
implementation review when available. Do not infer authority for production
data repair, destructive migrations, branch-protection changes, unrelated
cleanup, or changes outside the requested repository/scope.

P0, P1, and P2 findings block completion. Preserve P3 findings as non-blocking
backlog unless the user explicitly expands the remediation threshold.

## Invocation Options

Parse only these options; stop on unknown or conflicting input:

- `--scope <path-or-domain>`: lock the original scrub scope. Default to the
  whole repository.
- `--resume <run-id>`: resume exactly one durable run. Reject mismatched repo,
  target, scope, or ownership provenance.
- `--dry-run`: perform one scrub, coverage pass, plan synthesis, and recursive
  plan review using temporary files only. Do not create a goal, durable state,
  repo files, branches, PRs, merges, or container changes.
- `--max-iterations <positive-integer>`: stop before starting an iteration
  beyond the limit. If blocking findings remain, mark workflow state
  `incomplete`, leave the goal unfinished, and report how to resume.
- `--deploy final|each-plan|never`: default to `final`.
  - `final` defers nested rebuilds and rebuilds once after the clean pass.
  - `each-plan` rebuilds after every completed remediation plan.
  - `never` never rebuilds or starts containers.

A bare invocation uses whole-repository scope, no iteration limit, and
`--deploy final`.

On `--resume`, inherit the stored scope and deployment policy. Reject an
explicit `--scope` or `--deploy`, reject `--dry-run`, and allow
`--max-iterations` only when it raises an existing finite limit. Reject
`--dry-run` combined with `--resume`, `--max-iterations`, or `--deploy`.

## Required Skill Composition

Read and follow these skills at the stage where each becomes active:

1. `$bug-scrub` for every discovery pass.
2. `$recursive-plan-review` for every non-empty remediation plan.
3. `$implement-merge` for every reviewed plan selected for execution.
4. `$pr-delivery` through `$implement-merge` for each mergeable phase.

Pass the exact plan path to `$recursive-plan-review` and `$implement-merge`.
Never rely on "newest plan" discovery when this loop already owns a plan.

Before mutating anything, resolve and inspect `$bug-scrub`,
`$recursive-plan-review`, `$implement-merge`, and `$pr-delivery`. Verify the
state helper is executable, reports schema version 1 through a successfully
validated initialized document, and that `$implement-merge` supports:

- a caller-owned active goal;
- explicit nested `rebuild_policy` values `after-plan`, `defer`, and `never`;
- PR and target-branch CI verification; and
- owned branch/worktree cleanup.

Stop on a missing capability instead of silently using an older or
plugin-cached implementation.

Reconcile goal state during Initial Context Reset before creating anything.
Resume a matching unfinished loop goal with its existing stable run identifier.
Create one active goal only when no unfinished goal exists. Include the
original scrub scope, target branch, stable run identifier, P0-P2 termination
gate, and plan-to-merge cycle in the objective.
The loop owns goal completion: when `$implement-merge` runs as a nested stage,
use its caller-owned-goal contract. It must reuse but neither replace nor
complete the outer goal. Complete it only after the final fresh scrub satisfies
the termination gate.

## Durable Run State

Read `references/run-state-schema.md` before first use. Execute
`scripts/run_state.py` without loading its source unless troubleshooting or
patching it. Store non-secret state outside the application repository. Resolve
its exact default path with the helper; it derives a collision-resistant
repository key from the canonical origin identity plus resolved checkout root
and writes under
`~/.codex/state/bug-scrub-loop/<repo-key>/<run-id>.json`:

```bash
python3 <skill-dir>/scripts/run_state.py state-path \
  --repo-root <absolute-repo-root> --run-id <stable-run-id>
```

Use a repository-named private operational ledger instead when instructions
require one.

Initialize with:

```bash
python3 <skill-dir>/scripts/run_state.py init \
  --path <state.json> \
  --run-id <stable-run-id> \
  --repo-root <absolute-repo-root> \
  --target-branch <branch> \
  --scope <locked-scope> \
  --baseline-sha <full-sha> \
  --deploy <final|each-plan|never> \
  [--max-iterations <n>] \
  [--containers-running]
```

For every transition, construct a complete candidate JSON document, validate
it, and atomically replace state:

```bash
python3 <skill-dir>/scripts/run_state.py validate --path <candidate.json>
python3 <skill-dir>/scripts/run_state.py replace \
  --path <state.json> --candidate <candidate.json>
```

Record the current stage, iteration, target SHA, coverage passes, every finding,
plan provenance, PR and merge evidence, deployment evidence, and owned
resources. Keep stable finding identifiers across iterations. Record unresolved
P3 findings with `status: "backlog"` so later runs deduplicate them. Never put
credentials, secrets, private payloads, or raw sensitive logs in run state.
Use `upsert-finding` for finding updates so recurring fingerprints retain one
stable history:

```bash
python3 <skill-dir>/scripts/run_state.py upsert-finding \
  --path <state.json> --finding '<complete-finding-json>'
```

## Initial Context Reset

Before iteration 1:

1. Re-read repository instructions and relevant test, deployment, planning,
   branch, worktree, and private-data guidance.
2. Refresh the remote target branch and inspect HEAD, branch, dirty state,
   worktrees, open loop-owned PRs, CI, and running containers.
3. Resolve the scrub scope from the user's request. Default to the whole
   repository when no narrower scope is named.
4. Recover interrupted loop state before creating a goal or starting a new
   iteration:
   - call the host goal inspection mechanism and inventory durable run states,
     loop-named plans, cleanup ledgers, branches, worktrees, and open PRs;
   - validate every candidate run state with `scripts/run_state.py`;
   - resume an exact single match only when its run identifier, plan path,
     scope, target branch, and ownership provenance agree;
   - finish verification or safe cleanup for that run before continuing; and
   - stop on ambiguous, dirty, unowned, or conflicting state instead of
     creating a duplicate plan or PR.
5. If an unfinished goal exists but does not match this loop, stop and request
   direction. If none exists, create the loop goal with a new stable run
   identifier.
6. Initialize or resume durable run state. Record the target branch, starting
   SHA, locked scope, guarded verification commands, deployment policy, and
   whether a relevant local stack was already running.
7. Preserve unrelated dirty work. Create task branches/worktrees only through
   repository-approved ownership and cleanup mechanisms.

Do not deploy during preflight or between discovery and planning.

For `--dry-run`, skip goal and durable-state creation. Use an isolated temporary
directory for the plan and coverage artifacts, remove it after reporting, and
stop after recursive plan review.

## Iteration Loop

Repeat the following stages without an arbitrary iteration cap.

### 1. Run a Fresh Scrub

Reset stale context and invoke `$bug-scrub` in read-only mode against the full
original scope.

- Read `references/scrub-coverage-contract.md` and build one coverage manifest
  for the current target SHA.
- Rebuild inventories from the current target-branch source.
- For large repositories, shard real domains across at most four read-only
  subagents when concurrency is available. Keep scopes non-overlapping and
  treat their output as leads.
- Include recent merged changes as a risk domain, but do not reduce a
  whole-repository request to a diff-only review.
- Reconfirm every candidate from current source, callers, tests, and contracts.
- Assign each accepted finding a stable identifier based on behavior and owner,
  not only a line number.
- Record severity, evidence, failure path, expected versus actual behavior,
  regression-test direction, and smallest verification.
- Deduplicate current findings against earlier iterations. A recurring finding
  remains blocking evidence; it is not a new success condition.
- For non-dry runs, upsert every accepted finding by stable identifier and
  fingerprint, then append the completed coverage manifest before applying the
  severity gate. Update `lastSeenIteration`, status, and additive
  evidence for recurrences; never mint a new ID for the same behavior. Keep the
  same structure only in the temporary dry-run artifact otherwise.
- Escalate severity when stronger evidence warrants it; never downgrade a
  finding to terminate the loop. A resolved or rejected finding requires an
  explicit disposition. For an external/upstream resolution, prefix the
  disposition with `external:` and attach current verification evidence.

Require coverage accounting for the requested scope. If a material domain
cannot be inspected, report the exact gap and treat the run as blocked rather
than clean. A zero-finding pass is eligible for closeout only when the
run-state validator accepts a complete coverage manifest for the current SHA.

### 2. Apply the Severity Gate

Partition confirmed findings into:

- **Blocking:** P0, P1, and P2.
- **Non-blocking:** P3 backlog and rejected candidates that were not confirmed
  as bugs.

If the blocking set is empty, proceed to Final Clean Closeout. Do not create an
empty plan or invoke `$implement-merge`.

A confirmed P0-P2 remains blocking even when remediation is deferred for
authority, policy, credentials, safety, or external-state reasons. In that
case, terminate the run as blocked and preserve the evidence; never classify
the run as clean.

If a P0 exists, plan and deliver it before unrelated lower-severity work unless
atomicity requires a combined change.

Persist P3 evidence, fingerprint, owner, trigger, first/last seen iteration,
and disposition in run state. Never repeatedly report the same unchanged P3 as
a new finding.

### 3. Create an Executable Remediation Plan

Refresh finding evidence immediately before writing. Create a new checkable
plan in the location required by repository instructions. Use a private
companion repository when findings or operations are not safe for the
application repository.

Treat a private companion repository as in scope only when repository
instructions explicitly designate it. Otherwise stop before writing private
details. In a designated companion repository:

- follow its branch, worktree, review, delivery, and cleanup rules;
- keep the plan on an owned companion branch or other documented durable path;
- retain append-only plan commit history; separately mark each converged
  reviewed implementation revision in `implementationCommitShas` and record
  that exact revision with each application PR/merge. Post-merge progress and
  closeout commits remain in `commitShas` but do not require impossible
  retroactive delivery;
- commit plan progress separately from application code; and
- never stage or commit cross-repository plan files in an application PR.

The plan must include:

- iteration number, source target-branch SHA, scope, and finding identifiers;
- goal, non-goals, assumptions, and evidence for every blocking finding;
- dependency-ordered, independently mergeable phases;
- concrete production files, callers, contracts, and data boundaries to touch;
- a failing non-regression test or equivalent proof for every finding;
- migration, rollback, compatibility, cache, concurrency, and cleanup concerns
  when relevant;
- focused and broad verification commands using guarded entry points;
- per-phase acceptance criteria and final completion criteria;
- delivery boundaries, expected PR sequence, and container/deployment behavior;
  and
- an explicit statement that P3 backlog is outside the blocking fix set.

Group only findings that share an implementation boundary or must land
atomically. Do not hide unrelated refactors, speculative hardening, or product
policy decisions inside the plan.

Persist every new plan in run state as `draft` before review. A new reviewed
implementation commit must increase `reviewPasses` before the plan may advance
to implementation or completion.

### 4. Review the Plan to Convergence

Invoke `$recursive-plan-review` on the exact plan file until a complete pass
finds no verified actionable comments.

After convergence:

1. Refresh target-branch HEAD and dirty state.
2. Revalidate each planned finding against current source.
3. Update or remove stale findings and rerun plan review if the plan changes
   materially.
4. If no blocking findings remain because upstream changes resolved them, skip
   implementation and begin a fresh scrub.

Do not implement a plan that still has unresolved sequencing, ownership,
verification, safety, or product-policy questions.

### 5. Implement and Merge the Exact Plan

Reset stale context and invoke `$implement-merge` with the exact reviewed plan
path.

- Keep the outer loop goal active through `$implement-merge`'s
  caller-owned-goal contract.
- Pass the nested rebuild policy derived from invocation:
  - `--deploy final` -> `rebuild_policy: defer`;
  - `--deploy each-plan` -> `rebuild_policy: defer`, then let this outer loop
    perform the crash-safe rebuild immediately after the plan completes;
  - `--deploy never` -> `rebuild_policy: never`.
- Implement in the plan's smallest mergeable phases.
- Require behavioral regression tests and adversarial implementation review.
- Use `$pr-delivery` for each phase and wait for required PR and target-branch
  checks.
- Persist each newly opened PR as `open` before later head, merge, target-CI,
  and closure transitions.
- Never weaken protection, bypass red checks, or use unrelated dirty changes.
- Update the plan with completed tasks, verified divergences, PRs, and merge
  SHAs.
- Preserve append-only PR head-SHA history across follow-up pushes; freeze the
  final head after merge or closure. Preserve the same append-only history for
  plan revisions used by that PR and freeze the final plan revision at close.
- Record `$implement-merge` completion, merge, cleanup, target-CI, running
  container, and rebuild/deferral evidence in durable run state.

If implementation exposes a new blocking bug within the same boundary, add it
to the active plan when that preserves a coherent delivery. Otherwise record it
for the next iteration; never silently drop it.

### 6. Reset and Rescrub

After the entire plan is merged, target-branch CI is verified, owned resources
are cleaned, and the selected nested rebuild/deferral is complete:

1. Settle phase-specific agents and command sessions.
2. Re-read repository instructions from disk.
3. Refresh the target branch and record its new SHA.
4. Verify canonical branch/worktree hygiene and deployment state required by
   the repository.
5. Start the next iteration with a fresh scrub of the full original scope,
   explicitly including the repaired seams and recent changes.
6. Before starting, enforce `--max-iterations`. If the next iteration exceeds
   the limit, keep the current iteration at the limit, set run status to
   `incomplete`, preserve remaining blockers, and yield without claiming a
   clean result.

Do not declare success from implementation tests, a diff review, or the absence
of the previous finding alone. Only a new complete scrub can close the loop.

## Recurrence and Progress Rules

- If the same blocking finding survives a remediation, treat that as a failed
  fix. Reopen or amend the prior plan with failure analysis instead of creating
  duplicate plans.
- Stop further writes and mark the workflow as stagnated when the same stable
  finding survives two consecutive remediation attempts with materially
  unchanged trigger and failure evidence. Preserve evidence and request a new
  design, missing product decision, or user direction before attempting it
  again. Change the host goal status to `blocked` only when the host's
  independent repeated-blocker threshold is satisfied; otherwise leave the
  goal active while yielding for direction.
- Increment a finding's remediation `attempts` only after verified merged
  delivery. Append one immutable `attemptRecords` entry containing the exact
  plan path, reviewed plan commit, and merge SHA; the validator ties each count
  to that delivered revision. Scrub sightings alone never increment attempts.
  A recurring finding may reopen the same completed plan with a new reviewed
  commit and delivery record.
- Require meaningful progress between iterations: the blocking set shrinks,
  failure behavior changes with evidence, or a newly proven external blocker
  explains why work cannot continue. A new target-branch SHA alone is not
  progress for a recurring finding.
- Do not downgrade or relabel findings merely to terminate.
- Do not stop because the loop is long. Stop only at the clean gate or a
  genuine blocker requiring user authority, product policy, credentials, or an
  external-state change.
- Preserve evidence from prior iterations in plans and merged artifacts, but
  never trust it without reconfirming current source.

## Final Clean Closeout

Declare the loop clean only when a fresh, complete scrub of the current
target-branch SHA finds zero confirmed P0, P1, and P2 bugs in the requested
scope and the run-state validator accepts the final coverage pass.

Before completing the goal:

1. Verify target-branch ancestry and required CI for the last merge.
2. Verify all loop-owned PRs are settled and every loop-owned branch/worktree
   is cleaned. A preserved or converted resource is an exact closeout blocker,
   not a successful completion state.
3. Run repository custody/hygiene checks when available.
4. Apply the final deployment policy:
   - `final`: if the relevant stack was running at startup, rebuild it through
     repository instructions to converge on the clean SHA and verify deployed
     build identity, health, and readiness;
   - `each-plan`: do not duplicate the last rebuild; verify the running commit
     and rebuild only if the clean SHA has not actually been deployed;
   - `never`: do not touch containers and report deployment as intentionally
     skipped.
5. Record deployment evidence in durable run state.
6. Record remaining P3 findings and evidence gaps without presenting them as
   blocking defects.
7. Set run status and stage to `complete`, validate the final state, and only
   then complete the host goal.

Report:

- every scrub iteration and target-branch SHA;
- blocking findings selected and findings rejected/deferred;
- plan paths and recursive-review results;
- merged PRs and verified merge commits;
- local, CI, database, browser, and deployment verification;
- final zero-P0/P1/P2 termination evidence;
- durable state path, final coverage manifest, residual P3 backlog, or
  uninspected areas; and
- any preserved unrelated or loop-owned resources.

Mark the active goal complete only after this closeout succeeds.

For every rebuild, including `each-plan`, make deployment state crash-safe:

1. Recheck whether the relevant stack is currently running; never touch a
   stack that was not running at loop startup, and never start a stopped stack.
   At final closeout record the current observation as
   `containersRunningAtCloseout`.
2. Before invoking the documented rebuild command, append a unique deployment
   operation with `status: "pending"`, the intended commit, policy, and
   `attemptedAt`; persist it.
3. After the command and identity/health/readiness checks, update that same
   operation to `success` or `failed`, add `completedAt`, and persist it. If
   command outcome cannot be proven, use `uncertain`.
4. On resume, reconcile every `pending` or `uncertain` operation by inspecting
   the deployed commit, operation/build marker when the app exposes one, and
   health/readiness. Mark it `success` when that operation is proven, `failed`
   when disproven, or keep it `uncertain` and stop when the running build cannot
   distinguish a completed attempt from a command that never began. Do not
   blindly repeat a possibly completed rebuild.
5. When deployment is intentionally omitted, persist a terminal `skipped`
   operation with the exact policy or stopped-stack reason.
