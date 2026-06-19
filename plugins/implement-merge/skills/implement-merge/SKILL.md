---
name: implement-merge
description: >-
  Implement the most recently created plan end to end, clearing stale context first,
  creating an explicit goal for the plan, executing the plan in mergeable phases,
  using $pr-delivery for each phase that must be committed, pushed, reviewed, and
  merged, then rebuilding any already-running local containers after the complete
  plan has landed. Use when the user invokes $implement-merge, asks to implement
  and merge a plan, says to execute the latest plan through PRs, or wants an
  autonomous plan-to-merge delivery loop.
---

# Implement Merge

Use this skill to turn the newest applicable plan into merged production code. The workflow is goal-driven and phase-oriented: establish the plan, implement one bounded phase at a time, merge it with `$pr-delivery`, then continue until the whole plan is complete.

## Startup

1. Clear stale working context before acting.
   - Treat previous conversation analysis as untrusted unless it is repeated in the current request, active goal, or repository artifacts.
   - Re-read repository instructions and the relevant plan file from disk.
   - Re-discover current git, CI, container, and app state instead of relying on old status.
2. Find the most recently created plan.
   - Prefer a plan path named by the user.
   - Otherwise inspect the repository's documented plan locations, such as `docs/plans/`, private companion planning repositories, or project-specific instructions.
   - Use file creation metadata where available; if unavailable or ambiguous, use the newest plan by modification time and verify from its title/body that it is an implementation plan rather than an unrelated note.
   - If multiple recent plans plausibly qualify, ask one concise clarification before editing code.
3. Create or update the active goal.
   - Set the goal objective to implement the selected plan completely.
   - Include the plan path and the intended phase sequence in the objective when possible.
   - If an active goal already exists, continue only if it matches the selected plan; otherwise ask before replacing direction.

## Implementation Loop

For each plan phase:

1. Read the phase tasks, acceptance criteria, and verification gates.
2. Inspect the current code before editing; preserve unrelated dirty work.
3. Implement the smallest coherent phase that can be reviewed and merged independently.
4. Run the smallest convincing local verification for that phase, broadening when risk or repository instructions require it.
5. Update the plan file as tasks are completed or if the implementation intentionally diverges.
6. Invoke `$pr-delivery` to commit, push, open or update the PR, monitor checks and reviews, merge safely, verify target-branch ancestry, verify target-branch CI when required, and clean up only after verification.
7. After the phase merge is verified, refresh local repository state from the target branch before starting the next phase.

Do not batch unrelated phases into one PR unless the plan explicitly requires atomic delivery or separating them would create an invalid intermediate state.

## Completion

When all phases and acceptance criteria are complete:

1. Mark the active goal complete only after every required phase is merged and verified.
2. Check whether containers are currently running on the system.
   - Use a non-destructive container listing command, such as `docker ps` or the repository's documented compose status command.
   - If no containers are running, do not start new long-running services just for this skill.
3. If containers are running, rebuild only the already-running relevant stack using the repository's documented command.
   - Prefer project instructions, for example `docker compose up -d --build app worker` when that is the documented deployed app stack.
   - Verify the rebuilt services with the repository's documented health or readiness checks.
4. Report the selected plan, merged PRs, merge commits, verification performed, container rebuild result, and any residual follow-up.

## Guardrails

- Always read and follow `$pr-delivery` before performing delivery actions.
- Do not weaken branch protection, bypass required checks, or merge through red required checks.
- Do not delete branches, worktrees, data, or containers unless the relevant delivery workflow has verified it is safe and repository instructions allow it.
- Do not mutate local running application databases or file storage while verifying tests; use the repository's guarded test entry points.
- Stop and ask the user if the newest plan contains private operational details but only a public repository location is available for plan updates.
