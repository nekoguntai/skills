---
name: recursive-plan-review
description: Iterative plan-file critique and refinement. Use when the user invokes /recursive-plan-review or $recursive-plan-review, provides a plan file for review, asks to recurse on a plan until no comments remain, or wants a planning document repeatedly challenged and improved before implementation.
---

# Recursive Plan Review

This is plan review, not code review. Do not run `codex review` unless the user separately asks for code-diff review.

## Inputs

- Require a concrete plan file path. If the user gives none and there is exactly one obvious active plan, use it; otherwise ask for the path.
- Preserve the user's stated goal and scope. Do not turn plan review into implementation unless explicitly asked.
- Read adjacent source, docs, tickets, logs, or task notes only as needed to verify whether a plan comment is real.

## Review Loop

Repeat these steps until the stopping rule is met:

1. Read the whole plan file and identify its goal, assumptions, phases, dependencies, verification steps, and completion criteria.
2. Verify likely weak spots against source evidence when available. Prefer `rg`, focused file reads, tests, docs, and existing project instructions over speculation.
3. Produce candidate comments covering stale facts, missing prerequisites, unsafe sequencing, scope creep, vague acceptance criteria, weak verification, hidden migration/backout needs, and avoidable complexity.
4. Filter candidates. Accept only comments that are actionable, evidence-backed, and improve correctness, clarity, risk handling, sequencing, or verifiability.
5. Edit the plan file directly for accepted comments when editing is allowed. Keep changes minimal, preserve useful structure, and avoid unrelated rewriting.
6. Record rejected comments briefly when they are plausible but not worth applying, especially when they are preference-only, speculative, already covered, contradicted by evidence, or outside scope.
7. Re-read the updated plan and begin the next pass.

## Stopping Rule

Stop only after a complete pass over the current plan yields no verified actionable improvements.

Treat the plan as clean when:

- There are no accepted comments left to apply.
- Remaining comments are explicitly rejected as non-actionable, subjective, duplicate, outside scope, or blocked by missing requirements.
- The plan has concrete verification steps that would prove the planned work.

If the loop repeats the same subjective or contradictory suggestions without new evidence, stop the churn, mark those suggestions rejected, and report why they were not actionable. If convergence depends on unknown product requirements, ask the user for that missing decision instead of inventing it.

## Quality Bar

Prefer improvements that make the plan easier to execute safely:

- Clear goal, non-goals, assumptions, and acceptance criteria.
- Ordered phases with dependencies and rollback/backout notes where relevant.
- Explicit verification for each risky behavior change.
- Source-backed corrections for stale claims or missing work.
- Smaller, simpler slices when the current plan bundles unrelated risks.

Avoid:

- Cosmetic rewriting that does not change execution quality.
- Broad architecture expansion without evidence that the plan needs it.
- Replacing project-specific conventions with generic process advice.
- Marking the review clean before re-reading the final plan.

## Final Report

Report:

- Plan file reviewed.
- Number of review passes.
- Accepted improvements applied, grouped briefly.
- Rejected or deferred comments, with short reasons.
- Verification run, such as `git diff --check`, docs lint, focused tests, or source reads.
- Final clean result: no verified actionable plan comments remain, or the exact blocker preventing convergence.
