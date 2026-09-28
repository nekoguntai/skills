---
name: grade-loop
description: "End-to-end quality remediation loop for a repository, with stale-context resets at startup and between remediation passes. Use when the user invokes $grade-loop, asks Codex to run a grade/audit, turn major findings into a reviewed remediation plan, implement that plan, deliver and merge the PR, verify target-branch post-merge CI, rebuild any already-running localhost app containers, and rerun grade to decide whether another remediation pass is needed."
---

# Grade Loop

Use this skill to take a repository from quality audit to merged remediation,
green target-branch post-merge CI, and post-merge local rebuild. Clear stale
context at startup and between remediation passes. This is an execution loop,
not a chat-only report.

## Worker Models And Delivery Groups

Before dispatching workers or creating resources, resolve `$pr-delivery` and
read its `references/loop-execution.md`. Use cheaper workers (prefer
`gpt-6-luna` when available) for bounded discovery, implementation, tests, and
independent review. The larger coordinator verifies source evidence, actual
diffs, and final combined tests, and owns integration, state, delivery, and
cleanup. Workers do not push or create PRs. Escalate only an evidence-backed
hard slice; do not default routine work to the coordinator's model.

Prefer one PR containing all compatible changes selected for a pass, retaining
separate worker commits and regression evidence. Internal phases/finding counts
do not require separate PRs. Split only for a documented repository, protection,
rollout/migration, or risk constraint. Preserve scope, review, CI, and permissions.

## Required Skill Order

Use these skills in order:

1. `grade` for the initial audit, pre-delivery quality evidence, and the
   post-closeout loop check.
2. `recursive-plan-review` for the remediation plan file.
3. One adversarial implementation review subagent after local verification and
   before `pr-delivery`.
4. `pr-delivery` for commit, PR, CI monitoring, merge verification,
   target-branch post-merge CI verification, and cleanup.

Open each referenced skill's `SKILL.md` when reaching that phase and follow its
rules. Do not substitute a lighter workflow when the user asked for the loop.

## Durable Run State And Baseline

The loop is iteration-scoped. Use the cleanup inventory provider shipped by
`pr-delivery`; do not implement a second inventory collector or cleanup
comparator here. Resolve the required `pr-delivery` skill at startup and set
`PR_DELIVERY_SKILL_DIR` to its resolved directory. The provider contract is API
version 1. If the skill or its API 1 provider is unavailable, stop before any
repository mutation and report the blocker. Never fall back to a duplicate
implementation.

Resolve and create the durable state location outside every checkout and
worktree, while keeping `repo_root` stable for the whole run. Initialize the
run state before creating any branch or worktree, with:

```text
run_state.py init --path <state-path> --run-id <run-id> --repo-root <repo-root> \
  --target-branch <target-branch> --current-sha <current-sha> --max-passes 2 \
  [--target-remote <remote-name>] [--companion-repo <repo-root> ...]
```

`max-passes` defaults to 2 and bounds delivery iterations. Initialization
captures the immutable run-wide inventory baseline. Verify that initialization
and baseline capture succeeded before reserving or creating the first audit resource.
Use `python3 <skill-dir>/scripts/run_state.py` for all state changes; read
[`references/run-state-schema.md`](references/run-state-schema.md) before use.
The required CLI is `init`, `replace --path --candidate`, `validate --path`,
`archive --path --source <file> --kind report|history|plan|evidence`,
`verify-artifacts --path`, `verify-cleanup --path`, and `summary --path`.
Archives copy files to external state/artifacts and register their hashes. Do not edit the state file directly
or add fields beyond the documented schema.

Required lifecycle values are status `active` while work is in progress;
stages `audit`, `planning`, `implementation`, `delivery`, `post-audit`,
`cleanup`, and `complete`; terminal statuses are `complete` and `deferred`.
`blocked` is resumable and requires a reason at the interrupted stage.
`complete` means no major actionable issue remains. `deferred`
means issues remain and the durable state records why work stops. `blocked`
means required work remains blocked; it must not be reported as successful
cleanup. Advance exactly one iteration only after that iteration's cleanup
verifies, set the next stage to `audit`, and clear `reason`.

Every invocation of `grade` writes reports and history. Therefore reserve and
create an owned audit branch/worktree before the initial grade invocation,
after durable initialization and baseline creation. Apply this to the initial
audit and every post-audit. Do not grade on the target branch. Before each
invocation, identify its report and history source files; archive both with
`run_state.py archive` and verify the copies are readable and their registered
hashes match before cleanup. Every audit record must refer to the archived
report and history plus source SHA, and identify phase `initial` or `post`.
Require a post audit whenever a delivery occurred.

Before follow-up decisions, check that the latest audit is fresh for the
current target-branch SHA and phase. Persist `stage: planning` before writing
a plan; the helper verifies the live target and archived evidence at planning
and implementation transitions. Start any follow-up from that fresh state
and archived evidence, on a newly owned branch/worktree. Never reuse or convert
the previous pass's delivery or audit branch into another pass. Never rerun
`grade` solely to reconstruct a report or history artifact that was lost; mark
the run blocked and preserve the available evidence instead.

Reserve every loop-owned resource in the durable ledger before creating it:
implementation, audit, planning, reviewer, delivery, and companion-repository
branches/worktrees, including remote branch names before first push. Keep all
state, archives, and artifacts outside every checkout. Follow the detailed
cleanup and terminal-exit contract in
[`references/cleanup-contract.md`](references/cleanup-contract.md).

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

The durable run-state ledger is authoritative for ownership and cleanup
provenance; follow its schema documentation rather than maintaining a second
ledger or inventing extra state fields.

- Use distinctive names: `codex/grade-loop/<finding-slug>` for implementation
  work and `codex/grade-loop-check/<finding-slug>` for post-closeout grade
  checks. Use the same slug in temporary worktree paths when worktrees are
  necessary.
- Prefer a normal task branch when the current worktree is clean enough. Use an
  isolated worktree only to protect unrelated dirty work or to keep a
  report-mutating loop check off the synced target branch.
- Before creating a new worktree, run `git worktree list --porcelain` and
  classify existing loop-owned worktrees. Remove only clean leftovers that are
  proven to belong to this loop and no longer needed within the current pass. Leave
  dirty, unmerged, or unrecognized worktrees in place and report them.
- Pass the run ID, iteration, state path, state helper, and iteration-baseline cleanup policy
  to `pr-delivery` during Phase 5. Its nested cleanup must satisfy its own gates;
  the outer loop still verifies full inventory equality.
- Conversion between passes is prohibited. Every pass's owned resources must
  be safely removed before another iteration begins.

## Context Reset Discipline

At startup and after each delivered PR before rebuild, post-closeout grading, or
another remediation pass, clear stale context:

1. Treat prior conversation analysis, branch-local observations, generated
   reports, plan statuses, and subagent conclusions as stale unless confirmed by
   the current request, merged code, plan files, grade reports, PR state, CI
   output, or a fresh source read.
2. Finish PR delivery cleanup first: verify the platform-reported merge commit
   is reachable from the target branch, verify target-branch CI, fetch the
   target branch, and ensure no PR monitoring or long-running command sessions
   remain active.
3. Re-read repository instructions, the archived current grade report and
   history, remediation plan, dirty state, target branch HEAD, CI state, and
   running app/container state
   before rebuild, loop-check grading, or another implementation pass.
4. Classify any dirty files discovered after the merge before editing again;
   preserve unrelated work and archive grade-generated report/history changes
   before cleaning them up.
5. Start post-closeout grade checks and any follow-up pass from the refreshed
   target-branch state and archived evidence. Each gets a new owned branch or
   worktree; never use the merged PR branch or an earlier pass's audit branch.

This reset is context hygiene, not destructive cleanup: do not discard unrelated
work, reset the worktree, restart services, or rebuild stopped containers unless
repository instructions or the user require it.

## Pass Budget

Run two delivery passes by default at most, with a post-closeout grade check
after each delivery. The `max-passes` durable run-state value is the bound. If
the audit finds no major actionable issues, finish without delivery.

When the budget is exhausted while major issues remain, archive and record the
selected next finding and a deferral reason, then terminate as `deferred`. Do
not open another PR or continue an unbounded sequence.

## Phase 1 - Grade

Run the `grade` skill in full mode unless the user explicitly asks for diff
mode. Let it update `docs/plans/codebase-health-assessment.md`.

After grading, extract only the major actionable issues:

- hard-fail blockers first;
- then top risks and fastest improvements with clear evidence;
- then roadmap items that are high impact and feasible in one PR;
- exclude purely speculative, low-evidence, or churn-heavy recommendations.

If the grade finds no major actionable issues, archive the report and history,
record the result, and terminate through the cleanup contract. This includes an
initial clean audit with no delivery. Preserve the canonical report and history
in a permitted pre-existing checkout or an already authorized delivery before
removing their audit resources. Copy only verified generated changes without
overwriting unrelated work; preserve repository history/append semantics.
External archives are recovery evidence, not the requested canonical output.
Do not create a documentation PR merely to clean up a no-op audit. If neither
preservation route is permitted and safe, retain the work and record the exact
cleanup blocker.

## Phase 2 - Remediation Plan

Write or update a plan file, defaulting to
`docs/plans/grade-loop-remediation-plan.md` unless repo instructions name a
better location. If the plan contains private operational details, use the
repo's private-plans location when documented.

The plan must include:

- source grade report path, date, commit, score, and selected findings;
- objective and non-goals;
- phases ordered by dependency and risk;
- concrete file areas to inspect or change;
- compatibility and rollback/backout notes for risky changes;
- verification commands for each phase and for final closeout;
- acceptance criteria proving each selected issue is fixed;
- explicit deferred findings with reasons.

Keep the selected pass bounded and combine its compatible fixes into one PR.
Use separate commits and finding-specific verification for independent slices.
Defer out-of-scope findings explicitly; split delivery only for a documented
constraint rather than repeating full PR/main CI for each worker's change.

## Phase 3 - Recursive Plan Review

Run `recursive-plan-review` on the plan file. Apply its accepted improvements
directly to the plan and repeat until the review reports no verified actionable
comments remain.

If plan review requires a product decision that cannot be inferred from source
or project docs, ask the user for that decision before implementation. Do not
invent policy.

## Phase 4 - Implement

Implement the reviewed plan exactly as scoped.

1. Update the plan statuses as work completes or if implementation must diverge.
2. Prefer existing repository patterns and helper APIs.
3. Add behavioral or drift tests for every contract, policy, or workflow change
   that could regress.
4. Do a simplification/self-review pass before verification.
5. Run the plan's focused verification first, then broader repo gates
   proportional to the blast radius.
6. Run a final `grade` or `grade --diff <base>` when it will provide meaningful
   evidence that the selected issues improved. Use full grade for broad shared
   changes or when the original finding was repo-wide.

## Phase 4.5 - Adversarial Implementation Review

Before using `pr-delivery`, run this gate after local verification and before
staging for commit. Use one fresh independent reviewer for this gate in addition to the bounded
worker delegation required above.

Spawn one fresh reviewer subagent and give it the minimum useful context:

- source grade report, remediation plan path, selected findings, and non-goals;
- current diff, changed files, and any updated plan statuses;
- focused and broad verification commands already run, with failures or skips;
- final `grade` or `grade --diff <base>` evidence when it was run.

Ask the reviewer to find high-confidence correctness regressions, missing or
weak tests, plan drift, unaddressed grade findings in the selected scope,
unnecessary complexity, boundary-case failures, verification gaps, and PR
delivery blockers. Do not ask it to edit files, stage, commit, push, or run
delivery.

Do not start PR delivery until verified reviewer findings that could
affect correctness, tests, maintainability, or delivery are fixed or explicitly
documented as non-blocking. Rerun focused verification after fixes, and rerun
the reviewer only when the fixes materially change the implementation or the
first review found a blocker. Include the review outcome and any deferred
findings in the PR body or final response.

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
continuing to rebuild or the post-closeout grade check. If the failure is
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

## Phase 7 - Post-Closeout Grade Loop Check

After merge verification and any required localhost rebuild/health checks,
create a fresh loop-check branch or temporary worktree from the synced target
branch, then rerun the `grade` skill there. Do not run a report-mutating
post-closeout grade pass directly on the target branch.

Use full mode unless the repository or user explicitly requires a diff-only
follow-up. Let it update `docs/plans/codebase-health-assessment.md` and trend
history again.

Then inspect the refreshed grade report for major actionable issues using the
same selection rules from Phase 1:

- If no major actionable issues remain, archive the report and history, record
  the result, capture final score/evidence, and clean up this iteration.
- If a major actionable issue remains, is feasible in another bounded PR, and
  the pass budget allows another autonomous delivery, finish and verify cleanup
  for the current iteration, then create a fresh iteration with
  `replace --path <state-path> --candidate <candidate.json>` before creating
  any new resources. If the target SHA is unchanged, start at Phase 2 using
  the preserved audit and selected findings; do not repeat the same full audit.
  If the target advanced, refresh audit evidence before deciding the next pass.
- If major issues remain but are too broad, speculative, require a
  product/operational decision, or exceed the remaining pass budget, record a
  deferral and reason, clean up generated audit changes, and stop. If required
  work is blocked, preserve required resources and record a resumable blocked
  state with the exact cleanup status.

For audit cleanup, archive and verify every grade-generated report/history
artifact first. Preserve the latest canonical report/history in a permitted
pre-existing checkout or authorized delivery as described in Phase 1. Then
remove disposable loop-generated copies after archival and only
when they are proven to belong to that iteration. Do not restore unrelated
files or remove a dirty worktree whose dirty state is not fully explained by
the current iteration.

Do not keep looping indefinitely on low-evidence recommendations or on the same
rejected/deferred findings. Each additional pass must select a concrete,
evidence-backed remediation slice that can be implemented and delivered safely.

## Cleanup And Terminal Exits

Follow [`references/cleanup-contract.md`](references/cleanup-contract.md) for
every pass boundary and every terminal exit, including an initially clean
audit, budget exhaustion, deferment, and blocker. A run is not terminal until
the durable state records the decision and the outer cleanup inventory matches
the reserved baseline, except that a blocked run may retain resources required
to preserve unresolved work and must report them explicitly. Never describe a
blocked run as cleanly completed.

## Final Response

Report concisely:

- initial and final grade evidence, including report path and score movement;
- post-closeout grade-loop result and whether another remediation pass was
  skipped, deferred, or completed;
- pass budget used and whether each iteration's resources were cleaned up;
- remediation plan path and recursive-plan-review pass count;
- adversarial review outcome and any fixes or deferred findings from it;
- main implementation changes;
- local verification commands and CI result;
- PR number/link, forge type, merge commit, and ancestry verification;
- target-branch post-merge CI run and result;
- branch/worktree cleanup;
- container rebuild command and health/readiness results, or why rebuild was
  skipped;
- deferred grade findings and residual risks.
- durable run-state summary and archived evidence locations.
