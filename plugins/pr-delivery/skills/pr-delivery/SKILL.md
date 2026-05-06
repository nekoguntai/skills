---
name: pr-delivery
description: End-to-end pull request delivery workflow for committing local changes, pushing a branch, opening a PR, monitoring CI/reviews, fixing failures, merging safely, and cleaning up branches/worktrees afterward. Use when the user explicitly asks to ship, deliver, open-and-merge, monitor checks, address PR feedback, merge through queue/protected branch flow, or clean up a PR worktree after merge.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# PR Delivery

Use this skill to take a branch from local changes to a merged PR with verified cleanup. The job is not done when the PR opens; it is done only after checks/reviews are handled, the merge is verified on the target branch, and local/remote/worktree cleanup is safe.

## Guardrails

- Do not run this workflow unless the user explicitly requested commit/push/PR/merge/delivery.
- Never revert unrelated user changes. If unrelated dirty files exist, leave them alone or move the task to an isolated worktree.
- Do not use broad destructive approvals. For cleanup commands that remove branches or worktrees, request exact one-off approval when the environment requires it.
- **Never combine `gh pr merge --auto --delete-branch` on a merge-queue repo** — the CLI will close the PR without merging and delete the branch as cleanup. See the "Common pitfalls" section under step 6 for the exact recovery procedure. On merge-queue repos, only ever use `gh pr merge <num> --auto` with no extra flags.
- Do not delete a merge-queue PR branch before the queue merge has landed and been verified.
- Prefer stable plain `gh ...` commands. Avoid disposable env prefixes unless a command actually fails without them.

## Workflow

1. Preflight the repo.
   - Run `git status --short`, `git branch --show-current`, `git show -s --format='%h %D %s' HEAD`, and inspect the diff.
   - Confirm the branch is not `main`/protected unless the user specifically asked to release from it.
   - Identify unrelated dirty files. If present, do not stage them.
   - Review project instructions and task tracker requirements when the repo has them.

2. Verify before committing.
   - Run focused tests/typechecks for the touched area.
   - For broad/frontend/backend/shared changes, run the package-level gate the repo expects before pushing.
   - If a test fails, fix root cause locally, rerun the focused check, and broaden only as needed.

3. Commit cleanly.
   - Stage only files belonging to the task.
   - Re-read `git diff --cached` before committing.
   - Use a concrete commit message that names the behavior changed.
   - If hooks or pre-commit agents edit files, inspect those changes, run relevant checks again, then amend or make a follow-up commit intentionally.

4. Push and open the PR.
   - Push the current branch to `origin`.
   - Open a PR with a concise title/body including summary and verification.
   - If a PR already exists for the branch, update/continue it instead of opening a duplicate.
   - Capture the PR number and URL.

5. Monitor and address everything.
   - Poll `gh pr checks <number>` and `gh pr view <number> --json mergeStateStatus,statusCheckRollup,reviewDecision,reviews,comments`.
   - If a workflow is still running but looks inconsistent, inspect runs/jobs directly with `gh run list` and `gh run view <run-id> --json jobs`.
   - For failed jobs, fetch logs, identify the local repro command, fix locally, run the local gate, commit, push, and repeat.
   - Address review comments or requested changes with code/docs/tests, not just replies, unless the comment is answered by evidence.
   - Keep monitoring until required checks and review state are mergeable, or clearly report a blocker.

6. Merge safely.
   - Confirm required checks are green and the PR is mergeable.
   - Default to scheduled auto-merge when the user has asked you to deliver/merge the PR and the forge supports it. This is still an explicit delivery action, not permission to auto-merge unrelated PRs.
   - Do not schedule auto-merge for draft PRs, stacked/non-default-base PRs, unresolved review/requested-change states, conflicts, failing checks, missing required checks, branch-outdated blockers, release/candidate PRs that need a manual gate, or when the user asks to hold.
   - If the repo uses merge queue, run the queue command without branch deletion; then continue monitoring until `mergedAt` is non-null and `origin/main` contains the merged commit.
   - If the repo uses direct protected-branch merge, use the allowed merge method and verify the resulting target-branch commit.
   - Do not treat "queued" or "merge requested" as complete.

   ### gh CLI command reference

   **Detect which mode the target branch uses** (run once per repo, cache the result):

   ```bash
   # Returns "true" when a merge queue is active for the branch.
   gh api repos/:owner/:repo/branches/main/protection --jq '.required_status_checks // empty | length > 0' 2>/dev/null
   gh api repos/:owner/:repo/rules/branches/main 2>/dev/null | jq '.[] | select(.type=="merge_queue") | .type' | head -1
   ```

   **Merge-queue repos — use these exact commands:**

   ```bash
   # Enable auto-merge (queue picks the strategy itself; do NOT pass --squash/--merge/--rebase, do NOT pass --delete-branch).
   gh pr merge <num> --auto

   # Verify it took:
   gh pr view <num> --json autoMergeRequest -q '.autoMergeRequest.mergeMethod'   # non-null = queued
   ```

   **Non-queue protected-branch repos — explicit strategy + delete-branch is fine:**

   ```bash
   gh pr merge <num> --auto --squash --delete-branch
   ```

   ### Forgejo API command reference

   Forgejo supports per-PR scheduled auto-merge through the merge endpoint. Use this by default after the delivery request when checks are still pending but the PR is otherwise mergeable:

   ```json
   {
     "Do": "squash",
     "MergeTitleField": "<merge title>",
     "MergeMessageField": "",
     "delete_branch_after_merge": false,
     "merge_when_checks_succeed": true
   }
   ```

   If the PR is already green, the same endpoint may merge immediately. After scheduling or merging, keep monitoring until the PR is actually closed/merged and the target branch contains the resulting merge commit. Cancel scheduled auto-merge with `DELETE /api/v1/repos/{owner}/{repo}/pulls/{index}/merge` if new failures, review blockers, or user instructions require a hold.

   **Verify completion (both modes):**

   ```bash
   gh pr view <num> --json state,mergedAt,mergeCommit -q '"state=" + .state + " mergedAt=" + (.mergedAt // "null")'
   git -C <repo> fetch origin main && git -C <repo> log origin/main --oneline | grep -F "$(gh pr view <num> --json mergeCommit -q '.mergeCommit.oid // ""' | cut -c1-7)"
   ```

   ### Common pitfalls

   - **Never combine `--auto --delete-branch` on a merge-queue repo.** The gh CLI will close the PR (or attempt to merge directly, conflicting with the queue) and run the `--delete-branch` cleanup as if the merge had succeeded. The PR ends up CLOSED with `mergedAt: null` and the remote branch deleted. Recovery: `git push -u origin <branch>` to restore, then `gh pr reopen <num>`, then `gh pr merge <num> --auto` (no `--delete-branch`).
   - **Force-push during auto-merge resets the auto-merge state.** After any `git push --force-with-lease`, re-run `gh pr merge <num> --auto`.
   - **Stacked PRs (base ≠ default branch) cannot use auto-merge** — branch protection is only on the default branch. Wait for the parent PR to land, then `gh pr edit <num> --base main` before queueing.
   - **`mergeStateStatus: BLOCKED` is normal** during CI runs (just waiting on required checks). It only indicates a real failure when paired with FAILURE checks; verify with `gh pr checks <num> | grep -E 'fail|FAIL'`.
   - **`gh-readonly-queue/main/pr-<num>-<sha>` branches** are the merge queue's test branches — failures there mean the PR's checks fail when run against the latest main, not when run on the PR's own commit. Investigate the queue branch's runs, not the PR's runs, to debug queue rejections.
   - **`autoMergeRequest: null` does not mean "not queued"** in merge-queue repos. The merge queue tracks PRs separately from auto-merge. Verify queue membership with the GraphQL API: `gh api graphql -f query='query { repository(owner: "<owner>", name: "<repo>") { mergeQueue { entries(first: 10) { nodes { pullRequest { number } position state estimatedTimeToMerge } } } } }'`. A PR is genuinely queued when it appears in the entries list with a `state` like `AWAITING_CHECKS` or `MERGEABLE`.

7. Verify post-merge state.
   - Fetch `origin`.
   - Confirm the target branch contains the PR head or merge commit.
   - Confirm the PR is closed/merged with `gh pr view <number> --json state,mergedAt,mergeCommit`.
   - Sync the local target branch only when doing so will not overwrite unrelated local work.

8. Clean up only after verification.
   - Check `git status --short` in the PR worktree.
   - Delete the remote PR branch only after the merge is verified.
   - Delete the local branch only after switching away from it and confirming the merged commit is reachable from the target branch.
   - Remove temporary worktrees only after confirming they have no uncommitted changes.
   - Use exact cleanup commands; do not request persistent destructive approvals.

## Final Response

Report:

- PR number/link and merge commit.
- Checks or review failures encountered and how they were fixed.
- Verification commands run locally and in CI.
- Branch/worktree cleanup completed or intentionally left pending.
- Any residual risk or follow-up.
