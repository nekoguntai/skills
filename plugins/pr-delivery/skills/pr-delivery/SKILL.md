---
name: pr-delivery
description: End-to-end pull request delivery workflow for GitHub or Forgejo repositories: commit local changes, push a branch, open/update a PR, monitor CI/reviews, fix failures, merge safely, verify target-branch ancestry, and clean up branches/worktrees afterward. Use when the user explicitly asks Claude to ship, deliver, open-and-merge, monitor checks, address PR feedback, merge through queue/protected branch flow, or clean up a PR worktree after merge.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# PR Delivery

Use this skill to take a branch from local changes to a merged PR with verified cleanup. The job is not done when the PR opens; it is done only after checks/reviews are handled, the merge is verified on the target branch, and local/remote/worktree cleanup is safe.

This workflow supports two forge families:

- **GitHub:** use `gh` for PRs, checks, reviews, merge queue, and protected-branch merges.
- **Forgejo:** use the instance REST API under `/api/v1`; do not assume GitHub-only `gh pr ...` commands work unless the repo has explicitly configured and tested a compatible CLI.

## Guardrails

- Do not run this workflow unless the user explicitly requested commit/push/PR/merge/delivery.
- Detect the target forge before opening, monitoring, or merging. Pick the provider that matches `git remote get-url origin`.
- Never revert unrelated user changes. If unrelated dirty files exist, leave them alone or move the task to an isolated worktree.
- Do not use broad destructive approvals. For cleanup commands that remove branches or worktrees, request exact one-off approval when the environment requires it.
- Verify the merge by checking that the platform-reported merge commit is a real git object reachable from the target branch. Platform state such as `merged: true`, `mergedAt`, or `closed` is evidence, not proof.
- For squash merges, verify the merge commit SHA, not the PR head SHA. The PR head SHA does not land on the target branch after a squash merge.
- On Forgejo, keep `delete_branch_after_merge: false` in API merge payloads. Delete branches yourself only after git ancestry verification passes.
- **Never combine `gh pr merge --auto --delete-branch` on a GitHub merge-queue repo**. The CLI can close the PR without merging and delete the branch as cleanup. On merge-queue repos, only ever use `gh pr merge <num> --auto` with no extra flags.
- Do not delete a merge-queue PR branch before the queue merge has landed and been verified.
- Prefer stable plain `gh ...` and `curl ...` commands. Avoid disposable env prefixes unless a command actually fails without them.

## Workflow

1. Preflight the repo.
   - Run `git status --short`, `git branch --show-current`, `git show -s --format='%h %D %s' HEAD`, and inspect the diff.
   - Determine the target branch from the existing PR, the user's request, or the remote default branch. Do not hard-code `main` if the repo uses a different default.
   - Confirm the current branch is not the target/protected branch unless the user specifically asked to release from it.
   - Identify unrelated dirty files. If present, do not stage them.
   - Review project instructions and task tracker requirements when the repo has them.
   - Detect the forge:

     ```bash
     git remote get-url origin
     gh repo view --json nameWithOwner,url,defaultBranchRef 2>/dev/null
     curl -fsS "$FORGEJO_URL/api/v1/version" 2>/dev/null
     ```

   - For Forgejo, set or derive `FORGEJO_URL`, `FORGEJO_OWNER`, `FORGEJO_REPO`, and `FORGEJO_TOKEN`. Confirm the instance API exposes the endpoints this workflow needs:

     ```bash
     curl -fsS "$FORGEJO_URL/swagger.v1.json" \
       | jq -r '.paths | keys[] | select(test("pulls|statuses|actions/runs"))'
     ```

2. Verify before committing.
   - Run focused tests/typechecks for the touched area.
   - For broad/frontend/backend/shared changes, run the package-level gate the repo expects before pushing.
   - If a test fails, fix root cause locally, rerun the focused check, and broaden only as needed.

3. Commit cleanly.
   - Stage only files belonging to the task.
   - Re-read `git diff --cached` before committing.
   - Use a concrete commit message that names the behavior changed.
   - If hooks or pre-commit agents edit files, inspect those changes, run relevant checks again, then amend or make a follow-up commit intentionally.

4. Push and open or update the PR.
   - Push the current branch to `origin`.
   - Open a PR with a concise title/body including summary and verification.
   - If a PR already exists for the branch, update/continue it instead of opening a duplicate.
   - Capture the PR number and URL.

   **GitHub:**

   ```bash
   gh pr view --head "$BRANCH" --json number,url,state,title,baseRefName 2>/dev/null
   gh pr create --base "$BASE_BRANCH" --head "$BRANCH" --title "$TITLE" --body "$BODY"
   gh pr edit <num> --title "$TITLE" --body "$BODY"
   ```

   **Forgejo:**

   ```bash
   FORGEJO_API="${FORGEJO_URL%/}/api/v1"
   BRANCH="$(git branch --show-current)"

   # Find an existing open PR for this branch/base.
   curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls?state=open&limit=50" \
     | jq -r --arg branch "$BRANCH" --arg base "$BASE_BRANCH" \
       '.[] | select(.head.ref == $branch and .base.ref == $base) | "\(.number) \(.html_url)"'

   # Create a PR.
   jq -n --arg title "$TITLE" --arg head "$BRANCH" --arg base "$BASE_BRANCH" --arg body "$BODY" \
     '{title: $title, head: $head, base: $base, body: $body}' \
     | curl -fsS -X POST \
       -H "Authorization: token $FORGEJO_TOKEN" \
       -H "Content-Type: application/json" \
       --data-binary @- \
       "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls"

   # Update an existing PR title/body.
   jq -n --arg title "$TITLE" --arg body "$BODY" '{title: $title, body: $body}' \
     | curl -fsS -X PATCH \
       -H "Authorization: token $FORGEJO_TOKEN" \
       -H "Content-Type: application/json" \
       --data-binary @- \
       "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>"
   ```

5. Monitor and address everything.
   - Address review comments or requested changes with code/docs/tests, not just replies, unless the comment is answered by evidence.
   - For failed jobs, fetch logs when the forge exposes them, identify the local repro command, fix locally, run the local gate, commit, push, and repeat.
   - Keep monitoring until required checks and review state are mergeable, or clearly report a blocker.

   **GitHub:**

   ```bash
   gh pr checks <num>
   gh pr view <num> --json mergeStateStatus,statusCheckRollup,reviewDecision,reviews,comments
   gh run list --branch "$BRANCH"
   gh run view <run-id> --json jobs
   ```

   **Forgejo:**

   ```bash
   PR_JSON=$(curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>")
   HEAD_SHA=$(printf '%s\n' "$PR_JSON" | jq -r '.head.sha')

   curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/commits/$HEAD_SHA/statuses" \
     | jq -r '.[] | [.status, .context, (.description // ""), (.target_url // "")] | @tsv'

   curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/actions/runs?head_sha=$HEAD_SHA&limit=50" \
     | jq -r '.workflow_runs[]? | [.id, .status, .event, .title, .html_url] | @tsv'

   curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>/reviews" \
     | jq -r '.[] | [.state, .user.login, (.body // "")] | @tsv'
   ```

   Forgejo API tokens may expose run/task metadata without step logs, depending on the instance. If `swagger.v1.json` has no log/artifact endpoint or the log endpoint redirects to login, reproduce the failing command locally or rely on repo-owned failure artifacts instead of asking for a broader token by default.

6. Merge safely.
   - Confirm required checks are green and the PR is mergeable.
   - Default to scheduled auto-merge only when the user has asked you to deliver/merge the PR and the forge supports it safely. This is an explicit delivery action, not permission to auto-merge unrelated PRs.
   - Do not schedule auto-merge for draft PRs, stacked/non-default-base PRs, unresolved review/requested-change states, conflicts, failing checks, missing required checks, branch-outdated blockers, release/candidate PRs that need a manual gate, or when the user asks to hold.
   - If the repo uses GitHub merge queue, run the queue command without branch deletion; then continue monitoring until `mergedAt` is non-null and the target branch contains the merge commit.
   - If the repo uses direct protected-branch merge, use the allowed merge method and verify the resulting target-branch commit.
   - On Forgejo instances that have shown unreliable `merge_when_checks_succeed` behavior, prefer waiting for green checks and then performing a direct merge. If scheduled auto-merge is used, keep branch deletion disabled and treat git ancestry verification as mandatory.
   - Do not treat "queued", "merge requested", "closed", or "merged" as complete until git verification passes.

   ### GitHub command reference

   **Detect whether the target branch uses merge queue** (run once per repo, cache the result):

   ```bash
   gh api repos/:owner/:repo/branches/"$BASE_BRANCH"/protection --jq '.required_status_checks // empty | length > 0' 2>/dev/null
   gh api repos/:owner/:repo/rules/branches/"$BASE_BRANCH" 2>/dev/null | jq '.[] | select(.type=="merge_queue") | .type' | head -1
   ```

   **Merge-queue repos:**

   ```bash
   # Enable auto-merge. Queue picks the strategy; do NOT pass --squash/--merge/--rebase and do NOT pass --delete-branch.
   gh pr merge <num> --auto

   # Verify the request registered. In some merge-queue repos this may be null; use GraphQL queue membership if needed.
   gh pr view <num> --json autoMergeRequest -q '.autoMergeRequest.mergeMethod'
   ```

   **Non-queue protected-branch repos:**

   ```bash
   gh pr merge <num> --auto --squash --delete-branch
   ```

   ### Forgejo command reference

   Forgejo mergeability and merge state:

   ```bash
   curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>" \
     | jq '{state, draft, merged, merged_at, mergeable, merge_commit_sha, base: .base.ref, head: .head.sha}'

   curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>/merge"
   ```

   Direct squash merge after checks are green:

   ```bash
   HEAD_SHA=$(curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>" \
     | jq -r '.head.sha')

   jq -n --arg title "$TITLE" --arg head "$HEAD_SHA" \
     '{Do: "squash", MergeTitleField: $title, MergeMessageField: "", delete_branch_after_merge: false, head_commit_id: $head}' \
     | curl -fsS -X POST \
       -H "Authorization: token $FORGEJO_TOKEN" \
       -H "Content-Type: application/json" \
       --data-binary @- \
       "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>/merge"
   ```

   Scheduled Forgejo auto-merge, only when pending checks are otherwise clean and the instance is trusted for this behavior:

   ```bash
   jq -n --arg title "$TITLE" --arg head "$HEAD_SHA" \
     '{Do: "squash", MergeTitleField: $title, MergeMessageField: "", delete_branch_after_merge: false, head_commit_id: $head, merge_when_checks_succeed: true}' \
     | curl -fsS -X POST \
       -H "Authorization: token $FORGEJO_TOKEN" \
       -H "Content-Type: application/json" \
       --data-binary @- \
       "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>/merge"
   ```

   Cancel scheduled Forgejo auto-merge if new failures, review blockers, or user instructions require a hold:

   ```bash
   curl -fsS -X DELETE -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>/merge"
   ```

   ### Verify completion

   GitHub:

   ```bash
   MERGE_SHA=$(gh pr view <num> --json mergeCommit -q '.mergeCommit.oid // ""')
   git -C <repo> fetch origin "$BASE_BRANCH"
   ```

   Forgejo:

   ```bash
   MERGE_SHA=$(curl -fsS -H "Authorization: token $FORGEJO_TOKEN" \
     "$FORGEJO_API/repos/$FORGEJO_OWNER/$FORGEJO_REPO/pulls/<num>" \
     | jq -r '.merge_commit_sha // ""')
   git -C <repo> fetch origin "$BASE_BRANCH"
   ```

   Both:

   ```bash
   if [ -z "$MERGE_SHA" ]; then
     echo "NOT-MERGED: platform reports no merge commit"
   elif ! git -C <repo> cat-file -e "$MERGE_SHA" 2>/dev/null; then
     echo "GHOST-MERGE: claimed $MERGE_SHA does not exist as a git object"
   elif git -C <repo> merge-base --is-ancestor "$MERGE_SHA" "origin/$BASE_BRANCH"; then
     echo "MERGED at $MERGE_SHA"
   else
     echo "NOT-IN-TARGET: $MERGE_SHA exists but is not on origin/$BASE_BRANCH"
   fi
   ```

   The `MERGED` branch is the only one that justifies cleanup.

   ### Common pitfalls

   - **GitHub merge queue:** never combine `--auto --delete-branch` on a merge-queue repo. Recovery: `git push -u origin <branch>` to restore, `gh pr reopen <num>`, then `gh pr merge <num> --auto` with no `--delete-branch`.
   - **Force-push during auto-merge resets auto-merge state.** After any `git push --force-with-lease`, re-run the GitHub or Forgejo auto-merge request if it is still appropriate.
   - **Stacked PRs (base not equal to the default branch) cannot use GitHub auto-merge safely.** Wait for the parent PR to land, then retarget before queueing.
   - **`mergeStateStatus: BLOCKED` is normal** during GitHub CI runs when required checks are pending. Pair it with actual check conclusions before treating it as a failure.
   - **`gh-readonly-queue/<base>/pr-<num>-<sha>` branches** are GitHub merge queue test branches. Failures there mean the PR fails against latest target branch.
   - **`autoMergeRequest: null` does not always mean "not queued"** in GitHub merge-queue repos. Verify queue membership with GraphQL when needed.
   - **Forgejo ghost merge:** if the API claims `merged: true` with a `merge_commit_sha` that `git cat-file -e` cannot find after fetching the target branch, the platform claim is false. Do not clean up. If the PR cannot be reopened, push any fix on top of the still-existing head branch and open a fresh PR.
   - **Forgejo missing logs:** run metadata and commit statuses may be available while step logs are not. Verify Swagger before assuming a log endpoint exists.

7. Verify post-merge state.
   - Fetch `origin`.
   - Confirm the target branch contains the platform-reported merge commit.
   - Confirm the PR is closed/merged in the forge API as supporting evidence.
   - For GitHub, use `gh pr view <num> --json state,mergedAt,mergeCommit`.
   - For Forgejo, use `GET /api/v1/repos/{owner}/{repo}/pulls/{index}` and inspect `state`, `merged`, `merged_at`, and `merge_commit_sha`.
   - Sync the local target branch only when doing so will not overwrite unrelated local work.

8. Clean up only after verification.
   - Check `git status --short` in the PR worktree.
   - Delete the remote PR branch only after the merge commit is verified reachable from the target branch.
   - Delete the local branch only after switching away from it and confirming the merge commit is reachable from the target branch.
   - Remove temporary worktrees only after confirming they have no uncommitted changes.
   - Use exact cleanup commands; do not request persistent destructive approvals.

## Final Response

Report:

- Forge type, PR number/link, and merge commit.
- Checks or review failures encountered and how they were fixed.
- Verification commands run locally and in CI.
- Post-merge ancestry verification result.
- Branch/worktree cleanup completed or intentionally left pending.
- Any residual risk or follow-up.
