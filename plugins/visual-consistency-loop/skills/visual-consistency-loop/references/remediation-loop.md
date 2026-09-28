# Visual consistency remediation loop

## Scope and success

Run the audit procedure in `../SKILL.md` as the inspection primitive. Lock the
requested UI scope, route/journey matrix, themes, viewports, and relevant states
before the first pass. If unspecified, inventory the application's UI domains
and select a representative matrix covering them, recording sampling limits.
Preserve this coverage through follow-up passes; add newly affected surfaces
without silently narrowing scope to the last repaired component.

Completion requires a fresh, complete pass over that matrix at the current
verified target SHA with **zero confirmed P0, P1, or P2 findings**, successful
required verification, and settled runtime and cleanup gates. A finding blocked
by a product decision is still a finding. Do not relabel it P3, waive it, shrink
coverage, or call a partial/unrendered inspection clean to terminate the loop.
Retain P3 polish and intentional exceptions as non-blocking report entries.
Investigate unproven leads before promoting them; missing observations in the
required matrix prevent completion and must be reported as a coverage blocker.

There is no default pass cap. Each pass must make concrete, evidence-backed
progress. Stop resumably on unavailable evidence/tools, unresolved product
choices, permission barriers, or recurrence of the same finding after a failed
repair without a new supported diagnosis. Do not repeat identical fixes or
blind CI retries. A user-specified pass/time/scope bound stops further work with
an explicit incomplete result, never a clean claim. An initially clean audit
needs no implementation, PR, or rebuild.

## Shared state and resource custody

Before loop writes or resource creation, resolve the installed `pr-delivery`
and `recursive-plan-review` skills. Read pr-delivery's
`references/loop-execution.md` and `references/loop-run-state.md`. Use its API 1
inventory provider and `scripts/loop_state.py`; do not copy a collector or
invent a second ledger. Confirm the helper supports workflow
`visual-consistency-loop`, an uncapped default, and planning transition gates.
Missing dependencies block mutation rather than licensing weaker cleanup.

Initialize once, outside every checkout/worktree, before reserving resources:

```text
python3 <pr-delivery-dir>/scripts/loop_state.py init \
  --workflow visual-consistency-loop --path <external-state.json> \
  --run-id <unique-run-id> --repo-root <stable-repo-root> \
  --target-branch <target> --current-sha <full-live-target-sha> \
  [--target-remote <remote>] [--companion-repo <root> ...]
```

Omit `--max-passes` for the default `maxPasses: null`. Supply a positive value
only for a user-requested finite pass budget. Use the shared `replace`,
`archive`, `verify-artifacts`, `verify-cleanup`, `validate`, and `summary`
commands and documented schema; never manually edit live state. Store locked
scope, matrix, finding IDs/severities/dispositions, build identities, and pass
results in archived reports rather than adding unsupported state fields.
Non-grade audit records may have empty `history`; their `report` points to a
registered archive, with the exact source SHA and `initial` or `post` phase.
Keep every unresolved P0–P2 finding in the outcome, including those not selected
for this delivery group. Use `actionable` when more remediation is possible;
use `deferred` for a deliberate stop with findings or coverage blockers.

On resume validate the existing state, scope, live Git/PR/CI/runtime evidence,
and resource ownership. Keep the original baseline and immutable budget; do not
initialize a replacement that adopts leaked resources. Terminal deferred runs
are read-only under the shared schema; continuing after an exhausted finite
budget requires an explicitly requested new run after verified prior cleanup.
Blocked runs resume in place. An outer caller supplies `run_id`, `iteration`,
`state_path`, `state_helper`, and `cleanup_policy: iteration-baseline`; inherit
that custody, do not initialize nested state or complete its goal, and return
scoped results/absence evidence to the caller for whole-pass decisions.

Reserve every exact local/remote branch and worktree before creation or push,
including audit, plan, worker, review, delivery, and companion resources. Use
fresh resources per pass; no branch/worktree conversion or carryover. Follow
shared worker routing: bounded non-overlapping work on cheaper suitable workers,
independent review, and coordinator-owned integration, state, delivery, cleanup.
Prefer one reviewed PR for compatible findings per pass; document any split
required by repository, protection, rollout, dependency, or risk constraints.

## One iteration

1. **Refresh context.** Re-read repository instructions, dirty state, target
   SHA, current plans, shared UI owners, PR/CI status, and app build identity.
   Reconfirm prior conclusions against current source. Preserve unrelated work;
   never force-reset it. Use an owned branch/worktree based on the refreshed
   target for report-mutating audits and implementation, keeping these writes
   off the target branch. Strict standalone read-only modes need no ledger.
2. **Audit.** Follow the entrypoint's source and rendered inventory, rubric,
   semantic contract, report, and adversarial review. Record the locked coverage
   matrix and exclusions. Screenshots from an unknown/stale build cannot clear
   findings. Archive report, inventory, captures, and supporting evidence. If
   clean, proceed directly to final cleanup/completion; if blocked, preserve
   evidence and the exact reason without inventing a remediation plan.
3. **Plan and review.** Persist stage `planning`. Select bounded compatible
   major findings and write a checkable plan linking their IDs, source SHA,
   owners, contract, before/after evidence, regression checks, acceptance,
   non-goals, and backout boundaries. Keep remaining major findings visible.
   Run `recursive-plan-review` on the exact plan path until no verified
   actionable comments remain. Pass shared custody to nested plan review.
4. **Implement and verify.** Persist `implementation`, follow the reviewed
   plan and implementation playbook, characterize failures, repair shared
   owners, and preserve meaningful exceptions and navigation behavior. Run
   focused checks plus repository-required gates and rendered comparisons.
   Obtain an independent adversarial review of the integrated final diff and
   evidence before delivery. Resolve blockers and rerun affected verification;
   material later CI/review fixes return through this gate.
5. **Deliver.** Persist `delivery`. Invoke `pr-delivery` with the exact reviewed
   plan, required target-branch post-merge CI, and shared custody. Verify the
   platform-reported merge commit's ancestry and successful required CI for
   that exact target commit. Never bypass protection or treat a merged flag
   alone as proof. A failed/pending/missing target CI gate prevents closeout.
6. **Verify runtime.** After verified merge/CI, refresh context and identify the
   existing local app stack and its stable deployment checkout. Rebuild only
   already-running relevant services using documented commands, unless the
   user or outer caller forbids/defers rebuilds. Verify revision, health, and
   readiness; do not start stopped services. If rebuild is skipped or deferred,
   use an isolated current-build browser fixture for the audit and distinguish
   its verification from the unchanged live runtime. A required rebuild or
   health failure blocks completion; code repairs require reviewed redelivery.
7. **Re-audit.** Persist `post-audit`; inspect the original matrix on the fresh
   target source/build, including repaired flows and cross-family regressions.
   Do not limit the check to changed files or previously failing assertions.
   Archive a new `post` observation after every delivered iteration. Settle
   delivery resources before creating fresh audit resources when safe. A
   changed target invalidates earlier evidence: refresh before decisions.
8. **Clean and decide.** Complete the cleanup gate below. If major findings
   remain and work is feasible, advance exactly one iteration to active/audit
   through `replace`, then reserve fresh resources. Reuse the archived post
   audit for planning only when target SHA, build, and matrix remain current;
   each later delivery still requires its own post audit. Continue without a
   new permission question for already-authorized work.

## Cleanup and termination gate

Follow shared cleanup on every pass and exit, including an initially clean
inspection, final audit, requested stop, or budget exhaustion:

- Archive all report/plan revisions, inventory, screenshots, test/review/runtime
  evidence and unique history before removing disposable resources. Run
  `verify-artifacts` to verify bytes and the latest source copies. Preserve
  requested canonical outputs in a permitted checkout or authorized delivery;
  recovery archives alone do not replace those outputs.
- Settle owned agents, browser fixtures, test servers, monitoring sessions, and
  commands. Stop only temporary resources created by this run; retain the
  user's already-running app stack. Inventory ownership of non-Git resources
  in archived evidence as the Git helper does not track processes/containers.
- Recheck exact ownership, tips, dirt, merge ancestry, and target CI. Restore
  original checkout assignments without overwriting unrelated or requested
  work; remove only safe owned worktrees/branches. Remote deletion uses an
  expected-SHA lease. Honor repository one-off destructive-action permissions;
  loop authorization does not bypass them. No broad prune or forced cleanup.
- Run `verify-cleanup` and require actual local/remote branch and worktree
  inventory equality to the immutable baseline in every participating repo,
  plus zero owned leftovers. Counts or ledger flags alone are insufficient.
  A nested stage returns exact-resource absence to the outer owner, which
  performs whole-pass equality after all sibling resources are settled.
- Re-read state after helper updates. A fresh clean audit plus all gates permits
  `complete/complete`; remaining issues at a user limit or deliberate deferral
  require `deferred/complete` and a reason. If evidence, delivery, runtime, or
  cleanup cannot safely finish, preserve work as `blocked` at its current stage
  with exact retained resources and reason. Workflow status does not itself
  authorize changing a separately managed goal's status.
- Finish with `validate` and `summary`. If live target moved, refresh the audit
  before advancing or claiming completion. While still active, use `replace`
  to refresh `currentSha` and enter `audit` (or `post-audit` after delivery),
  append the new archived observation, then rerun `verify-cleanup`. Its live
  checks run again even when this iteration already has a cleanup receipt;
  do not delete the receipt or alter the baseline. Report any cleanup barrier honestly;
  do not erase unfinished work to make the inventory appear clean.
