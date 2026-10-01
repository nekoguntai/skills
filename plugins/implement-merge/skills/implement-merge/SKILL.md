---
name: implement-merge
description: "Implement the most recently created plan end to end, clearing stale context at startup and pass boundaries, tracking durable state, grouping compatible work into one reviewed PR per pass, and rebuilding already-running local containers after the plan lands. Use when the user invokes $implement-merge, asks to implement and merge a plan, says to execute the latest plan through PRs, or wants an autonomous plan-to-merge delivery loop."
---

# Implement Merge

Use this skill to turn the newest applicable plan into merged production code. The workflow is goal-driven and pass-oriented: establish the plan, implement compatible plan work as one reviewed delivery group, and continue from a refreshed target branch until all plan acceptance criteria pass.

## Shared Loop Contract

Before delegated work or creating Git resources, resolve the `pr-delivery`
skill and read its [`references/loop-execution.md`](../../../pr-delivery/skills/pr-delivery/references/loop-execution.md)
and [`references/loop-run-state.md`](../../../pr-delivery/skills/pr-delivery/references/loop-run-state.md).
Set `PR_DELIVERY_SKILL_DIR` to the resolved skill directory for every shared
state helper invocation. These contracts define worker routing, the shared
inventory provider, state schema, artifact handling, and cleanup gates; this
skill supplies the implementation-specific success predicate and rebuild
policy. If the required API 1 provider or state helper is unavailable, stop
before Git resource mutation. Do not create a duplicate inventory or state
implementation.

### Durable state and pass budget

For a standalone run, determine the stable repository root, target branch, and
current target SHA, then initialize durable state outside all checkouts and
worktrees before creating a branch or worktree:

```bash
python3 "$PR_DELIVERY_SKILL_DIR/scripts/loop_state.py" init \
  --workflow implement-merge --path <external-state-path> \
  --run-id <run-id> --repo-root <repo-root> \
  --target-branch <target-branch> --current-sha <target-sha>
```

The standalone default pass budget is unbounded by count and ends only when the
full plan acceptance criteria are met. Pass `--max-passes <N>` only when the
user or caller explicitly sets a pass budget. Preserve companion repositories
in the initial baseline with the shared helper's companion-repository option.
Use the shared helper to archive plan revisions and required evidence, record
audit references using the shared schema, validate state, and verify cleanup.
Plan completion is determined by the plan's full acceptance criteria, not by a
grade score.

Those shared audit records apply to standalone runs. When nested under a
compatible caller, reuse the exact `state_helper`,
`state_path`, `run_id`, and `iteration` it supplies. Apply
`cleanup_policy: iteration-baseline`; do not initialize nested state, recapture
a baseline that absorbs caller resources, advance the caller's iteration, or
complete the caller's goal. Write progress and resource records only through the
caller's helper and in its schema. If the caller uses a domain-specific schema,
do not append generic shared audit fields it does not support. A nested run
settles its own resources and returns exact-resource absence evidence; do not
run the caller's whole-run cleanup gate while the caller still owns resources.
Return phase, delivery, verification, and cleanup evidence to the caller.

Strict no-files/no-changes analysis does not initialize durable state or create
resources. Cleanup requirements do not grant authority to push, merge, or
publish; use `$pr-delivery` only when the current user request or caller
explicitly authorizes delivery. If work cannot be safely removed without losing
requested changes or performing unauthorized delivery, preserve it as blocked
and resumable rather than claiming cleanup success.

## Startup

1. Clear stale working context before acting.
   - Treat previous conversation analysis as untrusted unless it is repeated in the current request, active goal, or repository artifacts.
   - Re-read repository instructions and the relevant plan file from disk.
   - Re-discover current git, CI, container, and app state instead of relying on old status.
   - Read the shared loop contracts. Do not initialize state or create
     resources for strict no-files/no-changes analysis.
2. Find the most recently created plan.
   - Prefer a plan path named by the user.
   - Otherwise inspect the repository's documented plan locations, such as `docs/plans/`, private companion planning repositories, or project-specific instructions.
   - Use file creation metadata where available; if unavailable or ambiguous, use the newest plan by modification time and verify from its title/body that it is an implementation plan rather than an unrelated note.
   - If multiple recent plans plausibly qualify, ask one concise clarification before editing code.
3. Resolve the target branch and current target SHA, then initialize or resume
   standalone durable state outside every checkout and worktree. Do this before
   creating a branch or worktree. Nested runs reuse the caller's state.
4. Create or update the active goal.
   - Set the goal objective to implement the selected plan completely.
   - Include the plan path and the intended phase sequence in the objective when possible.
   - If an active goal already exists, continue only if it matches the selected plan; otherwise ask before replacing direction.
   - When a caller skill owns an active compatible goal and passes the exact
     plan path as a nested stage, reuse that goal without creating, replacing,
     or completing it. Record phase, PR, merge, verification, cleanup, and
     rebuild evidence for the caller. The caller owns final goal status.
   - Accept a nested `rebuild_policy` of `after-plan`, `defer`, or `never`.
     Default standalone runs to `after-plan`. Require a nested caller to pass
     the policy explicitly.

## Caller-Owned Iteration Cleanup

When a caller supplies `cleanup_policy: iteration-baseline`, inherit its
`run_id`, `iteration`, `state_path`, and `state_helper`. Reserve every local branch, remote
branch (before first push), and worktree in the caller's durable ledger before
creation, including agent/review and companion resources. Never claim a resource
from the caller's protected baseline. Return verified absence evidence for each
owned resource after safe cleanup. Do not create a nested baseline that treats
the caller's temporary resources as permanent. Do not convert resources between
phases or claim nested completion while any of the nested resources remain.
Preserve unique plan/progress history durably first, and recheck current branch
tips before deleting; remote deletion must use an explicit expected-SHA lease.
The outer caller runs the collaborator-tolerant cleanup gate after all pass
resources are settled. Existing deletion permissions and merge/CI gates still apply.

## Branch And Worktree Ownership

The shared durable state is the sole ownership ledger. Follow its schema rather
than adding a second cleanup ledger or inventing state fields.

- Use distinctive names for loop-created branches, such as
  `codex/implement-merge/<plan-or-phase-slug>`. If a temporary worktree is
  needed, use the same slug in the path.
- Prefer a normal task branch in the current repo. Create an isolated worktree
  only to protect unrelated dirty work or to keep independent phases from
  blocking each other.
- Reserve each local/remote branch, worktree, worker/reviewer, and companion
  resource in the shared ledger before creation or first push. Never claim a
  resource present in the original baseline.
- After delivery and exact target CI, remove only safe resources owned by this
  pass, then run the collaborator-tolerant cleanup gate (pr-delivery
  `references/loop-execution.md`): owned resources verifiably gone and the
  primary checkout restored. Branches and worktrees other collaborators added or
  removed are reported, never cleaned or treated as failures. Dirty, unmerged,
  or unrecognized resources must be preserved and reported; no converted
  branch/worktree or owned leftover counts as successful cleanup.
- Before finishing, run `loop_state.py stale --repo-root <root>` and settle our
  own forgotten resources from earlier runs (for example after a context
  compaction) with the same merge, CI, and clean-tree checks, plus any merged
  entries in a repository custody ledger.
- For nested runs, return scoped absence evidence to the caller instead of
  invoking its whole-run gate; the outer owner runs the gate after all caller
  resources settle.

## Implementation Loop

Before implementation, group all compatible selected plan work into one
reviewed delivery group. The default is one PR for the full compatible plan
scope in this pass, even if the plan has several internal phases. Work through
those phases in dependency order on the same delivery branch. Create separate
passes/PRs only for a concrete boundary such as distinct repositories,
incompatible protection rules, required deployment or migration sequencing, or
a reviewed risk boundary that prevents safe combined delivery. Record that
reason and group order in the plan. Separate worker commits and internal plan
phases alone are not grounds for additional PRs.

For each delivery group, use the steps below for standalone state. Nested runs
translate progress into their caller's schema and return scoped cleanup evidence;
the outer caller performs whole-run audit and inventory gates.

1. Read the phase tasks, acceptance criteria, and verification gates.
2. Inspect the current code before editing; preserve unrelated dirty work.
3. Archive the plan revision and current source/acceptance evidence, then record
   an `initial` audit that references those artifacts (`history` may be empty).
   Persist state stages through the shared helper (`planning`,
   `implementation`, `delivery`, `post-audit`, `cleanup`). Construct candidates
   from freshly read state and never edit live JSON directly.
4. Implement plan work in bounded slices, integrating compatible slices on the
   same owned delivery branch.
5. Run focused verification for each slice, then inspect the combined diff and
   run final tests and acceptance checks against the integrated final head.
6. Update and archive the plan as tasks complete or intentionally diverge.
7. Invoke `$pr-delivery` once for the delivery group to commit, open/update one
   PR, monitor required checks/reviews, merge safely when authorized, verify
   ancestry and exact target-branch CI, and clean up delivery resources.
8. Record a `post` audit at the verified target SHA after delivery. Archive and
   verify required artifacts before cleaning generated sources.
9. Pass the cleanup gate (owned resources gone, primary checkout restored,
   collaborator changes reported) before advancing or terminating. Run the
   between-pass context reset before starting another delivery group.

### Worker roles

Use bounded workers for independent source analysis, implementation slices,
test additions, and focused verification. Prefer `gpt-6-luna` when available;
if unavailable, use the cheapest suitable supported worker. Escalate only when
evidence shows the task needs stronger architecture, security, or debugging
capability. Give each worker a non-overlapping area, source/plan SHA, explicit
constraints, and acceptance evidence. Workers may make separate local commits,
but they do not push, open PRs, merge, publish, edit the parent's operational
ledger, or remove shared resources.

The coordinator owns scope and architecture decisions, checks worker evidence
against current source, inspects and integrates every diff, resolves conflicts,
runs the combined test suite at the final head, performs final review, and owns
delivery and cleanup. Worker tests on earlier heads do not replace final
integrated verification. Reserve worker branches/worktrees before creation and
settle workers before cleanup.

Do not add unrelated backlog to a delivery group. Split selected plan work only
for the concrete constraints above; an internal phase or a worker commit alone
does not justify another PR.

## Between-Pass Context Reset

After each delivery group is merged and target-branch CI is verified, clear stale context before continuing:

1. Finish delivery cleanup first.
   - Verify the platform-reported merge commit is reachable from the target branch.
   - Refresh local repository state from the target branch.
   - Delete only branches/worktrees that `$pr-delivery` has verified are safe to delete, and record the result in shared state.
   - Ensure no PR monitoring or long-running command sessions remain active.
2. Close or settle phase-specific subagents.
   - Close completed review or worker agents that are no longer needed.
   - Do not carry subagent conclusions forward unless the conclusion is reflected in merged code, the plan file, CI output, or a fresh source read.
3. Rebuild context from source artifacts.
   - Re-read repository instructions and the selected plan file from disk.
   - Re-check `git status`, current branch, target-branch HEAD, open dirty files, CI state, and relevant app/container state.
   - Treat previous conversation analysis, branch-local observations, and unmerged diffs as stale unless confirmed by these artifacts.
4. Update execution state.
   - Update the task plan from the plan file's current status.
   - Record the merged PR and merge commit in the working notes or final report context.
   - Choose the next required delivery group from full-plan acceptance and the refreshed repository state.
   - Start the next pass from the refreshed target-branch state, never from a merged PR branch or stale phase list.
   - If target SHA is unchanged, reuse the still-current archived audit where
     permitted by the shared state contract. If it moved, refresh audit
     evidence before entering planning; never consume old evidence at a new SHA.

This reset is lightweight context hygiene, not destructive cleanup: do not reset the worktree, discard unrelated dirty files, rebuild containers, or restart services unless the user or repository instructions require it.

## Rebuild Policy

Apply the selected policy only after every required delivery group is merged
and verified:

- `after-plan`: inspect running containers and rebuild the already-running
  relevant stack through repository instructions.
- `defer`: do not rebuild. Return whether relevant containers were running,
  their current commit when discoverable, and the exact documented rebuild and
  health/readiness commands so the caller can perform one later rebuild.
- `never`: do not rebuild or start containers. Report that deployment
  verification was intentionally skipped.

Repository instructions or an acceptance gate that requires deployed-runtime
verification may override `defer` or `never`; stop and report the conflict
before deployment unless the caller already authorized that override.

## Completion

Complete a standalone run only after all plan acceptance criteria are met,
required deployment/target-CI checks are verified, configured rebuild work is
done, owned resources are cleaned and the stale sweep has settled our own
forgotten resources, regardless of collaborators' concurrent work. An
initially clean plan or exhausted pass budget still goes through the same
cleanup gate; record `deferred` with a reason when acceptance remains
incomplete. A deferred plan is not a completed goal.

When all plan acceptance criteria are complete:

1. Check whether containers are currently running on the system unless the
   policy is `never`.
   - Use a non-destructive container listing command, such as `docker ps` or the repository's documented compose status command.
   - If no containers are running, do not start new long-running services just for this skill.
2. If containers are running and the policy is `after-plan`, rebuild only the
   already-running relevant stack using the repository's documented command.
   - Prefer project instructions, for example `docker compose up -d --build app worker` when that is the documented deployed app stack.
   - Verify the rebuilt services with the repository's documented health or readiness checks.
3. For `defer`, return the running-state and deferred rebuild evidence to the
   caller without mutating containers.
4. After required delivery, exact target CI, rebuild policy, and acceptance
   checks are settled, run the final cleanup gate and record standalone state as
   complete. Mark a standalone active goal complete only after that gate passes.
   If nested under a caller-owned goal, leave its status unchanged and return
   completion evidence to the caller.
5. Report the selected plan, merged PRs, merge commits, verification performed,
   container rebuild result or deferral, cleanup evidence, and residual follow-up.

## Guardrails

- Always read and follow `$pr-delivery` before performing delivery actions.
- Do not weaken branch protection, bypass required checks, or merge through red required checks.
- Do not delete branches, worktrees, data, or containers unless the relevant delivery workflow has verified it is safe and repository instructions allow it.
- Do not mutate local running application databases or file storage while verifying tests; use the repository's guarded test entry points.
- Stop and ask the user if the newest plan contains private operational details but only a public repository location is available for plan updates.
