# Shared loop execution contract

Read this contract before delegated work or Git resource creation in a loop.
It supplies model routing, delivery grouping, and resource custody; the caller
retains its scope, review gates, pass budget, success predicate, and permissions.
It applies to bug-scrub, grade, rationalize, frontend, feature-validation, and
implementation loops, and to resource-owning release, scaffold, and recursive
plan-review work. Pure read-only requests remain read-only.

## Cheaper workers, stronger coordinator

Use the larger capable model as coordinator. Delegate bounded source discovery,
focused investigations, implementation slices, test additions, and independent
verification to cheaper worker models. Prefer `gpt-6-luna` where available; if
unavailable, select the cheapest suitable supported worker instead of repeatedly
retrying an unavailable model or silently doing every slice on the coordinator.
Use a minimal fresh context with explicit model selection when the host requires
it; inherited full-history forks must not accidentally use the expensive model.

The coordinator must:

- define a bounded task, non-overlapping ownership, relevant source/plan SHA,
  constraints, and concrete acceptance evidence for each worker;
- parallelize only independent slices with isolated mutable inputs; serialize
  overlapping writes, generated-client/tool setup, shared database/runtime work,
  and integration;
- inspect workers' actual diffs and current source, reconfirm findings and
  claims, and run or inspect the smallest convincing verification against the
  integrated final tree; a worker's summary or green assertion is not proof;
- assign independent review to someone other than the author, then verify each
  accepted issue rather than accepting review conclusions automatically;
- retain architecture/product decisions, scope, state transitions, final
  integration, protected delivery, and exact owned-resource cleanup;
- escalate a bounded task only when evidence shows the cheaper worker lacks
  the capability needed (e.g. unresolved architecture, high-risk security,
  repeated reproducible reasoning failures). Keep routine work delegated.

If delegation is unavailable, record that limitation and continue the authorized
work with the same verification gates. Workers do not push branches, open PRs,
merge, publish, edit the parent's operational ledger, or delete shared resources.
The coordinator reserves worker resources before creation and settles workers
before cleanup. Model routing never expands operational authorization.

## One PR per pass where possible

Before implementation, group all compatible changes selected for this pass into
one reviewed delivery group. Workers may produce separate local commits and
regression evidence. The coordinator integrates them on one owned delivery
branch, reviews the combined diff, runs final combined gates, and opens one PR
for that pass. Avoid a push/PR for every worker, finding, or internal plan phase.
This default does not add unrelated backlog to the pass or bypass plan review.

Split only for a concrete constraint: distinct repositories, incompatible
permission/protection rules, required deployment/migration sequencing, or a
reviewed dependency/risk boundary that prevents safe combined delivery. Record
the reason and group order in the plan. Internal phases and separate commits
alone do not justify separate PRs. Keep required CI and final-head review;
worker tests at earlier heads do not replace combined verification.

For dependent groups, deliver serially, revalidate only the next group's base,
and preserve any already completed verification that remains applicable.
Companion documentation may need its own repository delivery; never mix private
files into a public PR to force a single-PR count. Local-only, analysis, plan,
and validation requests do not acquire PR/merge authority from this policy.

## One baseline and one resource owner

Use the shared API 1 inventory/ownership provider in pr-delivery. Resolve this
skill directory and set `PR_DELIVERY_SKILL_DIR` for adapter invocations.
Missing/incompatible helpers block resource mutation, not license a weaker
collector. See [loop-run-state.md](loop-run-state.md) for generic state/CLI.
Bug-scrub retains its stricter domain-specific state adapter; grade has a thin
profile wrapper. Both use the same inventory implementation.

Capture the immutable starting local branch names, actual remote branch names,
and worktree paths/assignments before creating resources. Include companion
repositories, preserve pre-existing resources, and keep operational state outside
all worktrees. Never recapture leaks as a new baseline on resume. Register exact
local/remote branches and worktrees before creation/push, including audit,
reviewer, worker, planning, delivery, and companion resources.

Nested skills inherit `run_id`, `iteration`, `state_path`, `state_helper`, and
`cleanup_policy: iteration-baseline`. They update the caller's ledger through
its helper and return evidence for their exact resources. Do not initialize a
nested run that treats the parent's temporary resources as permanent baseline,
complete the parent's goal, or delete resources still in use by other phases.
After a nested delivery group, remove its safe owned resources and return
verified absence to the coordinator. Whole-run equality is checked by the outer
owner after all resources for its pass are settled; a nested group must not
claim that the parent is clean while other parent resources remain.

## Artifacts, boundaries, and exits

Archive reports, plan revisions, canonical ledger snapshots, history, screenshots,
and other required evidence outside disposable worktrees before cleanup. Verify
archive bytes and recheck the latest source version before removing generated
files. Preserve desired canonical reports/CSV/code in the repository or through
authorized delivery; an external archive is recovery evidence, not a replacement
for requested user-facing output. Preserve unique commits/history separately
when copying files is insufficient.

After verified merge ancestry and required exact target CI, settle agents and
commands, reinspect branch tips/ownership/dirt, restore the original checkout
assignment without overwriting unrelated work, remove clean owned worktrees,
and delete owned branches. Remote deletion uses an explicit expected-SHA lease.
Repository-specific exact one-off permissions still apply. Never infer ownership
from a branch prefix, use broad cleanup, or force-remove dirty/unique work.

Before advancing a pass, finishing, or declaring a budget/scope deferral, verify
live inventory equals the original baseline in every participating repository.
Check live target SHA before consuming an audit and at completion. Preserve
archives and assert zero remaining owned resources. Equal counts alone are
insufficient; original branch names and worktree assignments must survive.
Reusing a current archived audit at an unchanged target avoids redundant full
inspection, but never reuses stale code, build, browser, or test evidence.

Apply the same cleanup gate to an initially clean/no-op pass, a final audit,
budget exhaustion, and explicitly stopped work. No converted worktrees or
leftovers count as successful cleanup. An interrupted or blocked run may retain
unfinished work with an exact reason; mark it resumable and do not claim success.
A local-only request may leave desired edits in a pre-existing permitted checkout
without changing the Git inventory. If safe restoration would require an
unauthorized merge or erase requested work, preserve the work and report the
cleanup blocker; do not invent delivery authority or silently archive it away.

Do not initialize durable state or create resources for strict no-files/no-changes
analysis. Inspect the starting and ending inventory read-only if needed. A nested
read-only/review worker uses its caller's custody instead of creating a competing
ledger. Ordinary in-place plan edits with no new Git resources need no disposable
worktree; preserve the requested plan as the final output.
