---
name: codex-review
description: "Codex code review closeout: local dirty changes, PR branch vs main, parallel tests."
---

# Codex Review

Run Codex's built-in code review as a closeout check. This is code review (`codex review`), not Guardian `auto_review` approval routing.

Use when:
- user asks for Codex review / autoreview / second-model review
- after non-trivial code edits, before final/commit/ship
- reviewing a local branch or PR branch after fixes

## Contract

- Treat review output as advisory. Never blindly apply it.
- Verify every finding by reading the real code path and adjacent files.
- Read dependency docs/source/types when the finding depends on external behavior.
- Reject unrealistic edge cases, speculative risks, broad rewrites, and fixes that over-complicate the codebase.
- Prefer small fixes at the right ownership boundary; no refactor unless it clearly improves the bug class.
- Keep going until Codex review returns no verified/actionable findings.
- If a review-triggered fix changes code, rerun focused tests and rerun Codex review.
- Never switch or override the review model. If the review hits model capacity, retry the same command a few times with the same model. If it hits sandbox/permission limits, use the helper's `--full-access` option instead of changing models.
- Stop as soon as the review command/helper exits 0 with no verified/actionable findings. Do not run an extra direct `codex review` just to get a nicer "clean" line, a second opinion, or clearer closeout wording.
- Treat the helper's successful exit plus absence of `[P0]`-`[P3]` priority markers as the clean review result, even if the underlying Codex CLI output is terse.
- If rejecting a finding as intentional/not worth fixing, add a brief inline code comment only when it explains a real invariant or ownership decision that future reviewers should know.
- Do not push just to review. Push only when the user requested push/ship/PR update.

## Pick Target

Dirty local work:

```bash
codex review --uncommitted
```

Use this only when the patch is actually unstaged/staged/untracked in the
current checkout and that local patch is the review target. For committed,
pushed, or PR work, review the branch against its base instead. A clean
`--uncommitted` review only proves there is no local patch.

Branch/PR work:

```bash
git fetch origin
codex review --base origin/main
```

Do not pass an inline prompt with `--base`; current CLI rejects `--base` + `[PROMPT]` even though help text is ambiguous. If custom instructions are needed, run the plain base review first, then do a local/manual follow-up pass.

For the bundled helper, prefer explicit branch mode for committed PR/branch work:

```bash
${CLAUDE_SKILL_DIR}/scripts/codex-review --mode branch
```

Helper `auto` mode also prefers branch review on non-main branches, even when
task notes or generated files are locally dirty. It prints a warning in that
case; run `--mode local` only when the uncommitted patch itself is the target.

If an open PR exists, use its actual base:

```bash
base=$(gh pr view --json baseRefName --jq .baseRefName)
codex review --base "origin/$base"
```

Committed single change:

```bash
codex review --commit HEAD
```

## Parallel Closeout

Format first if formatting can change line locations. Then it is OK to run tests and review in parallel:

```bash
${CLAUDE_SKILL_DIR}/scripts/codex-review --parallel-tests "<focused test command>"
```

For safer argument handling, prefer the argv form when the test command is not
shell syntax:

```bash
${CLAUDE_SKILL_DIR}/scripts/codex-review -- npm test -- --runInBand
```

Tradeoff: tests may force code changes that stale the review. If tests or review lead to code edits, rerun the affected tests and rerun review until no verified/actionable findings remain.

## Context Efficiency

Codex review is usually noisy. When subagents are available and allowed by the active instructions, use a subagent filter. Ask it to run the review and return only:
- actionable findings it accepts
- findings it rejects, with one-line reason
- exact files/tests to rerun

Run inline only for tiny changes or when subagents are unavailable.

## Helper

Bundled helper:

```bash
${CLAUDE_SKILL_DIR}/scripts/codex-review --help
```

If the helper is not executable after install, run it through `bash` or fix the
local mode with `chmod +x "${CLAUDE_SKILL_DIR}/scripts/codex-review"`.

The helper:
- chooses branch review first on non-main branches
- chooses dirty `--uncommitted` on main or detached checkouts when local changes exist
- otherwise uses current PR base if `gh pr view` works
- otherwise uses `origin/main` for non-main branches
- should be left in `--mode auto` or forced to `--mode branch` for committed/PR work; do not force `--mode local` after committing
- writes only to stdout unless `--output` or `CODEX_REVIEW_OUTPUT` is set
- supports `--dry-run`, `--parallel-tests`, and `-- <command> [args...]`
- supports `--full-access` for nested review runs that need localhost bind/listen tests
- treats `[P0]`-`[P3]` priority markers as a reason to stop and verify the output
- prints `codex-review clean: no [P0]-[P3] priority markers detected` when the selected review command exits 0 without priority markers

## Final Report

Include:
- review command used
- tests/proof run
- findings accepted/rejected, briefly why
- the clean review result from the final helper/review run, or why a remaining finding was consciously rejected
