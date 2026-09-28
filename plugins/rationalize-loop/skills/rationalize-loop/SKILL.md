---
name: rationalize-loop
description: End-to-end convergence remediation loop for a repository, with stale-context resets at startup and between convergence passes. Use when the user invokes $rationalize-loop, asks Codex to identify divergent paths, choose or recommend canonical paths, review a convergence plan, implement a bounded converge/remove phase, deliver and merge the PR, verify target-branch post-merge CI, rebuild any already-running localhost app containers, and rerun rationalize to decide whether another convergence pass is needed.
---

# Rationalize Loop

Use this skill to take a repository from divergence inventory to merged
convergence remediation, green target-branch post-merge CI, and post-closeout
loop checking. Clear stale context at startup and between convergence passes.
This is an execution loop, not a chat-only report.

## Required Skill Order

Use these skills in order:

1. `rationalize` for the initial divergence inventory, canonical-path decisions,
   convergence plan, and post-closeout loop check.
2. `recursive-plan-review` for the convergence plan file before implementation.
3. Cheap bounded workers for independent discovery, implementation, and test
   slices; coordinator-owned integration and verification.
4. One independent adversarial implementation review after local verification
   and before `pr-delivery`.
5. `pr-delivery` for commit, PR, CI monitoring, merge verification,
   target-branch post-merge CI verification, and cleanup.

Use `grade` only as supporting evidence when it helps prove quality movement,
such as `$grade --diff <base>` for changed convergence work or full `$grade`
when the convergence touched broad shared behavior.

Open each referenced skill's `SKILL.md` when reaching that phase and follow its
rules. Do not substitute a lighter workflow when the user asked for the loop.
Before delegating work or creating any Git resource, resolve the `pr-delivery`
skill and read its `references/loop-execution.md` and
`references/loop-run-state.md`. Follow their cheap-worker/strong-coordinator
rules, API 1 inventory provider, and shared state helper. If required tooling is
unavailable, stop before creating resources or changing repository files and
report the blocker.

## Run State And Cleanup Baseline

For an authorized loop that will write a plan, create Git resources, or deliver
changes, initialize one durable run outside every checkout and worktree before
any such write or resource creation. Keep `repo_root` stable and capture the
primary and companion repository baselines before reserving resources:

```text
python3 <pr-delivery-dir>/scripts/loop_state.py init --workflow rationalize-loop \
  --path <state-path> --run-id <run-id> --repo-root <repo-root> \
  --target-branch <target-branch> --current-sha <current-sha> \
  --max-passes 2 [--companion-repo <repo-root> ...]
```

Read `loop-run-state.md` for supported fields and command forms. Use only the
helper's `replace`, `archive`, `verify-artifacts`, and `verify-cleanup`
operations to update state and evidence. Record each rationalization observation
with its source SHA, outcome, and archived plan/report or evidence; non-grade
observations may have empty history. When invoked by an outer loop, inherit
its `run_id`, `iteration`, `state_path`, `state_helper`, and
`cleanup_policy: iteration-baseline`; never initialize a nested baseline or
complete the caller's goal. Return exact-resource absence evidence to the
caller, which owns whole-pass cleanup verification. Reserve every owned branch and
worktree before creation, including worker, review, audit, delivery, and
companion resources. Archive every plan revision and any report, history,
screen capture, or other evidence needed after its worktree is removed. Verify
archive bytes and the latest source copy before cleanup. The helper does not
delete resources; follow the shared cleanup contract and let the coordinator
restore the original branch and worktree assignments and verify exact baseline
equality.

Run the live target-SHA and whole-inventory gates before consuming a rationalize
result, advancing a pass, and any clean, deferred, or no-actionable exit. A
no-actionable initial result and pass-budget deferral require the same cleanup
gate as a merged pass. Preserve an unchanged-target archived rationalization
result for a follow-up instead of repeating the full inspection. If the target
SHA changed, refresh the inspection before making a new plan decision.
Unfinished unsafe cleanup is blocked with its exact reason; converted resources
or leftovers are not successful cleanup.

Strict read-only recommendation requests and explicit no-files/no-changes
requests do not initialize state, write reports or plans, or create cleanup
work. A standalone plan request preserves its requested plan output but does not
gain PR or merge authority. Local-only implementation likewise does not gain
PR/merge authority; preserve desired edits in the permitted checkout. If
restoring resources safely would erase requested work or require unauthorized
delivery, retain it and report a cleanup blocker.

## Worker Delegation And Delivery Grouping

Use the larger capable model as coordinator and delegate bounded discovery,
focused investigations, implementation slices, tests, and independent
verification to cheaper suitable workers, preferring `gpt-6-luna` where
available. Give each worker non-overlapping ownership, the relevant source and
plan SHA, constraints, and acceptance evidence. The coordinator confirms
findings, inspects actual diffs, runs final verification on the integrated tree,
and owns state transitions, delivery, and cleanup. Workers do not push, open or
merge PRs, edit the operational ledger, or delete shared resources. Settle all
worker resources before cleanup. The adversarial reviewer remains independent
from the implementation author and is limited to that review gate; that limit
does not restrict other bounded worker delegation.

Group all compatible selected changes into one reviewed delivery group and one
PR per pass where possible. Workers may provide separate commits; the
coordinator integrates and verifies the combined result. Split only for
distinct repositories, incompatible permissions/protection rules, required
deployment or migration sequencing, or a reviewed dependency/risk boundary.
Record the reason and order for each split. A companion private-plans
repository remains a separate delivery where required.

## Preflight

1. Read repo instructions such as `AGENTS.md`, `CLAUDE.md`, project docs, and
   active planning notes when present.
2. Run `git status --short --branch`, `git branch --show-current`, and
   `git show -s --format='%h %D %s' HEAD`.
3. Preserve unrelated dirty work. If unrelated local changes exist, either leave
   them unstaged or create an isolated branch/worktree before implementation.
4. Determine the target branch from the remote default branch or existing PR.
5. If already on the target branch, create a task branch before source edits
   unless the user explicitly requested direct target-branch work.
6. Repeat this preflight before every additional implementation pass. Never
   begin source edits for a second pass directly on the synced target branch.

## Branch And Worktree Ownership

The shared durable run state is the only ownership ledger. Use distinctive
names such as `codex/rationalize-loop/<area-slug>` and
`codex/rationalize-loop-check/<area-slug>`; reserve each owned branch and
worktree in the state before creation. Keep plans and inspection outputs in the
owned branch or worktree when they mutate repository files. Preserve unrelated
dirty work and never infer ownership from a branch prefix. Do not convert
resources between passes or report leftovers as successful cleanup. At every
pass boundary and closeout, remove only safe resources proven to belong to this
run and verify the original branch names and worktree assignments are restored
exactly. Ordinary in-place plan edits that create no Git resources may remain
in the permitted checkout as requested output; archive the plan and preserve
unrelated changes.

## Context Reset Discipline

At startup and after each delivered PR before rebuild, post-closeout
rationalizing, or another convergence pass, clear stale context:

1. Treat prior conversation analysis, branch-local observations, generated
   plans, canonical-path assumptions, and subagent conclusions as stale unless
   confirmed by the current request, merged code, rationalization plans, PR
   state, CI output, or a fresh source read.
2. Finish PR delivery cleanup first: verify the platform-reported merge commit
   is reachable from the target branch, verify target-branch CI, fetch the
   target branch, and ensure no PR monitoring or long-running command sessions
   remain active.
3. Re-read repository instructions, the current rationalization plan, dirty
   state, default branch HEAD, CI state, and running app/container state before
   rebuild, loop-check rationalizing, or another implementation pass.
4. Classify any dirty files discovered after the merge before editing again;
   preserve unrelated work and do not treat generated loop-check plan changes
   as canonical unless they are intentionally carried into the next pass.
5. Start post-closeout rationalize checks and any follow-up pass from the
   refreshed target-branch state, not from the merged PR branch, original
   divergence inventory, or stale canonical-path assumptions.

This reset is context hygiene, not destructive cleanup: do not discard unrelated
work, reset the worktree, restart services, or rebuild stopped containers unless
repository instructions or the user require it.

## Pass Budget

Run at most two delivery passes by default, with a post-closeout rationalize
check after each delivery. The durable `maxPasses` value is the bound. An
initial clean result needs no delivery.

After the autonomous follow-up budget is exhausted, report the next selected
finding and stop with a deferral instead of opening an unbounded sequence of
PRs.

## Phase 1 - Rationalize

Run the `rationalize` skill for the requested scope. If the user gives no
scope, use repo-wide scope but focus on the highest-risk, highest-evidence
divergence candidates.

Let it write or update a plan file, defaulting to
`docs/plans/rationalization-plan.md` unless repo instructions name a better
location. If the plan contains private operational details, use the repo's
private-plans location when documented.

After rationalizing, archive the plan/report evidence and extract only major
actionable convergence items:

- `remove` items with no callers or clearly retired support first;
- then `converge` items where drift risk, repeated change cost, or trust-boundary
  duplicate contracts are backed by source evidence;
- then high-impact plan phases feasible in one PR;
- exclude `keep separate`, `watch`, speculative, low-evidence, and broad
  cleanup recommendations.

If no major actionable converge/remove item exists, record the result, preserve
the requested canonical plan, and complete the same live target-SHA and
whole-inventory cleanup gate required by a delivered pass. Then stop without
manufacturing a PR.

If the next step requires a product, compatibility, data-retention, or external
client decision that cannot be inferred from source or project docs, record the
decision point and stop rather than inventing policy.

## Phase 2 - Bounded Convergence Plan

Use the rationalization plan from Phase 1 as the source plan by default. If the
rationalization plan is broad, add an implementation section or companion plan
that clearly selects the smallest coherent high-impact phase for this loop.

The reviewed plan must include:

- source rationalization plan path, date, commit, scope, and selected findings;
- canonical path decision or explicit decision blocker;
- objective and non-goals;
- paths to keep, wrap, converge, or remove;
- compatibility, migration, rollback, and backout notes;
- phases ordered by dependency and risk;
- focused verification commands and final closeout gates;
- acceptance criteria proving drift risk or repeated change cost was reduced;
- explicit deferred findings with reasons.

Keep the pass bounded, and group all compatible selected findings into one
reviewed delivery group and one PR where possible. Split only for distinct
repositories, incompatible permission/protection rules, required deployment or
migration sequencing, or a reviewed dependency/risk boundary. Record the reason
and order for each split; defer unrelated backlog explicitly.

## Phase 3 - Recursive Plan Review

Run `recursive-plan-review` on the convergence plan file. Apply accepted
improvements directly and repeat until the review reports no verified
actionable comments remain.

Do not proceed to implementation while the plan still has unresolved canonical
path, compatibility, or migration decisions.

## Phase 4 - Implement

Implement the reviewed convergence phase exactly as scoped.

1. Update the plan statuses as work completes or if implementation must diverge.
2. Preserve public compatibility unless the reviewed plan explicitly retires it.
3. Prefer existing repository patterns and helper APIs.
4. Add or update contract, drift, behavior, or migration tests before deleting
   duplicate behavior.
5. Keep adapters at real system boundaries instead of hiding provider/platform
   differences behind broad shared helpers.
6. Remove dead paths only after proving no callers remain or after the migration
   gate passes.
7. Do a simplification/self-review pass before verification.
8. Run focused verification first, then broader repo gates proportional to the
   blast radius.
9. Run `$grade --diff <base>` or full `$grade` when it provides meaningful
   evidence that convergence did not regress quality.

## Phase 4.5 - Adversarial Implementation Review

Before using `pr-delivery`, run this gate after local verification and before
staging for commit. Use one independent adversarial reviewer for this gate.
This reviewer-specific gate does not restrict the bounded worker delegation
defined by the shared execution contract.

Spawn one fresh independent reviewer for this gate, following shared worker
routing, and give it the minimum useful context:

- rationalization plan path, selected converge/remove decisions, and non-goals;
- current diff, changed files, and any updated plan statuses;
- caller/dead-path evidence, compatibility or migration notes, and adapter
  boundary decisions;
- focused and broad verification commands already run, with failures or skips;
- optional `grade` evidence when it was run.

Ask the reviewer to find high-confidence correctness regressions, canonical
path drift, compatibility or migration gaps, unproved dead-path removals,
missing contract/drift tests, boundary abstraction mistakes, verification gaps,
and PR delivery blockers. Do not ask it to edit files, stage, commit, push, or
run delivery.

Do not load or run `pr-delivery` until verified reviewer findings that could
affect correctness, compatibility, tests, convergence integrity, or delivery
are fixed or explicitly documented as non-blocking. Rerun focused verification
after fixes, and rerun the reviewer only when the fixes materially change the
implementation or the first review found a blocker. Include the review outcome
and any deferred findings in the PR body or final response.

If any later delivery, CI-fix, review-fix, or post-merge recovery step requires
new implementation changes, return to this gate before continuing PR delivery
or opening the fix PR.

Do not continue to PR delivery with known failing required local checks unless
the failure is unrelated, documented, and the repo's delivery rules permit it.

## Phase 5 - PR Delivery

Use `pr-delivery` for the full delivery path:

1. Stage only task-related files.
2. Run `git diff --cached --check`.
3. Commit with a concrete behavior-focused message.
4. Push the branch and open or update a PR.
5. Monitor CI and reviews until required checks are green and the PR is
   mergeable.
6. Fix CI failures with code/docs/tests, rerun local repros, commit, push, and
   repeat.
7. Merge safely through the forge, verify the platform-reported merge commit is
   reachable from the target branch, verify the target-branch CI run for that
   merge commit is complete and successful, and clean up local/remote PR
   branches only after those verifications pass.

Never weaken branch protection, bypass red checks, or treat platform "merged"
state alone as proof.

## Phase 5.5 - Target-Branch Post-Merge CI

After ancestry verification, wait for the CI run triggered on the target branch
by the exact merge commit or squash merge commit. The loop is not complete while
that run is pending, missing, failed, or cancelled.

Provider guidance:

- Forgejo: query recent Actions runs filtered by merge commit SHA when possible;
  otherwise query recent target-branch `push` runs and match the head SHA/title.
  Confirm the required aggregate status and relevant jobs are `success`.
- GitHub: use `gh run list --branch <target-branch> --commit <merge-sha>` and
  `gh run view`, or equivalent check-rollup commands.

If target-branch CI fails, inspect run/job diagnostics before forming a
hypothesis. Enumerate infrastructure causes such as Docker daemon availability,
Compose collisions, stale generated files, browser setup drift, missing
statuses, registry/network issues, or runner capacity. Reproduce locally when
logs are unavailable or inconclusive. If the delivered work caused the failure,
fix it in a new PR after rerunning the adversarial implementation review gate
for the fix, merge it, and verify the new merge commit's target-branch CI before
continuing to rebuild or the post-closeout rationalize check. If the failure is
unrelated or infrastructural, report the evidence and stop instead of claiming a
clean closeout.

## Phase 6 - Rebuild Running Localhost Containers

After the PR merge and target-branch CI are verified and the local target
branch is synced, rebuild only app containers that are already running locally.

Detection:

- Inspect `docker compose ps` when the repo has a Compose file.
- Inspect `docker ps` for containers bound to localhost ports when Compose is
  absent or ambiguous.
- Use repo instructions to identify app services and health endpoints.

Rebuild:

- If app services are already running, rebuild them in place with the repo's
  documented command, such as `docker compose up -d --build app worker`.
- Do not start stopped services only to satisfy this step.
- If no matching localhost app containers are running, report that rebuild was
  skipped.

Verify:

- Run `docker compose ps` or equivalent status command.
- Curl documented health/readiness endpoints when present.
- If rebuild or health fails, inspect logs, fix issues caused by the PR when
  possible, and redeliver if a code fix is required.

## Phase 7 - Post-Closeout Rationalize Loop Check

After merge verification and any required localhost rebuild/health checks,
settle delivery resources and verify the target SHA. If a post-closeout
rationalize inspection will mutate the plan, reserve a fresh owned branch or
worktree from the synced target branch before running it; never run a
plan-mutating inspection directly on the target branch. If the latest archived
rationalization result is still for this exact target SHA, reuse it rather than
repeating the full inspection.

If the chosen rationalization plan lives in a companion private-plans repo, use
the same branch/worktree and cleanup discipline there before letting the
post-closeout check modify that plan.

Archive the resulting plan/report evidence and inspect the refreshed plan for
major actionable `converge` or `remove` items using the same selection rules
from Phase 1. Verify the shared cleanup gate before any advance or exit:

- If no major actionable converge/remove item remains, record the result,
  preserve the requested plan, complete the shared cleanup gate, and finish.
- If a major actionable item remains, is feasible in another bounded PR, and the
  pass budget allows another autonomous delivery, complete the current cleanup
  gate and advance durable state with `replace`, then reserve a fresh
  pass branch/worktree from the synced target. Never carry or rename the
  loop-check branch into the next pass. Start Phase 2 using the updated plan
  when the target SHA is unchanged; refresh rationalization evidence first if
  it advanced.
- If remaining convergence depends on user/product/compatibility decisions,
  broad rewrites, low-evidence assumptions, or intentionally separate paths,
  record the blocker or deferral and archive required evidence. A deliberate
  budget/scope deferral passes the shared live cleanup gate; unsafe cleanup
  remains blocked with its exact reason. Stop instead of forcing an unsafe PR.
- If a major actionable item remains after the pass budget is exhausted, record
  it as the next deferred phase and stop rather than opening another PR.

Before cleanup, archive and verify every plan/report revision. Preserve the
canonical plan in the repository or its authorized companion delivery; an
external archive is recovery evidence, not a replacement for requested output.
Remove only files and Git resources owned by this run when safe. If restoring
the original checkout assignment would overwrite unrelated or requested work,
preserve it and report a cleanup blocker rather than erasing it.

Do not keep looping indefinitely on `watch`, `keep separate`, or previously
rejected/deferred findings. Each additional pass must select a concrete,
evidence-backed convergence slice that can be implemented and delivered safely.

## Final Response

Report concisely:

- rationalization plan path and selected converge/remove decisions;
- recursive-plan-review pass count;
- adversarial review outcome and any fixes or deferred findings from it;
- implementation changes and compatibility policy applied;
- local verification commands and CI result;
- optional grade evidence if run;
- PR number/link, forge type, merge commit, and ancestry verification;
- target-branch post-merge CI run and result;
- branch/worktree cleanup;
- container rebuild command and health/readiness results, or why rebuild was
  skipped;
- post-closeout rationalize-loop result and whether another pass was skipped,
  deferred, or completed;
- pass budget used and whether each pass restored the original inventory;
- deferred/watch/keep-separate findings and decisions still needing user input.
