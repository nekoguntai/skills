# Iteration cleanup contract

Read before initialization and each delivery closeout. Cleanup is a mandatory
iteration boundary, including iterations skipped because upstream fixed the
findings. The final clean discovery pass must also pass this gate, after any
final deployment. A successful run restores the initial local branch names,
actual remote branch names, and worktree paths/branch assignments in every
participating repository. Commit SHAs may advance. Equal counts alone do not
prove preservation.

## Provider

The inventory and ownership implementation is shared with grade-loop through
pr-delivery's API 1 `scripts/loop_cleanup` package. Set `PR_DELIVERY_SKILL_DIR`
to the resolved pr-delivery skill directory before calling the state helper.
The local `git_inventory.py` is a compatibility CLI/API wrapper, not a duplicate
collector. Existing schema-2 state needs no migration for this extraction.

## Capture before creation

Schema 2 `run_state.py init` captures the primary repository and each repeated
`--companion-repo <absolute-root>` before any loop-owned Git resource exists.
Declare all participating repositories up front. Baselines are immutable across
replacement and resume. Use a stable pre-existing checkout as `repoRoot`, never
a worktree the run will remove. The inventory includes shared Git directory
identity, local branch names, every configured remote's fetch/push endpoint
fingerprint and actual `ls-remote --heads` names, and worktree assignments.
Remote failures block initialization/verification; cached tracking refs are not
a substitute. Raw remote URLs and credentials are not persisted.

Existing branches and worktrees are protected, including unrelated dirty work.
Do not borrow a pre-existing topic branch for loop delivery. If using the
primary checkout for an owned branch, restore its original branch assignment
without disturbing unrelated changes before verification. Read-only discovery
runs from an existing checkout of the verified target SHA. If temporary scrub
or review worktrees are needed, register and clean them in the same iteration.

Schema 1 remains readable for historical inspection, but cannot advance through
the new gates: it has no historical Git baseline. Never snapshot today's leaked
resources as an alleged pre-run baseline. Recover trustworthy pre-run inventory
and per-iteration evidence before an explicitly reviewed migration; otherwise
report the missing evidence and retain the unfinished run. This version does
not automate legacy migration.

## Shared ownership ledger

Before creating a branch or worktree, append an `active` resource with exact
`owner: <runId>`, `repoRoot`, `iteration`, `kind`, `identifier`, and `remote`.
Use `local-branch`, `remote-branch`, or `worktree`; branch identifiers are short
branch names, worktree identifiers are absolute paths, and `remote` is null
except for remote branches. Reserve the remote branch before its first push.
Use distinct resource names per iteration. The validator rejects ownership of
a baseline resource, duplicates, and an earlier iteration's unfinished resource.

Pass `run_id`, `iteration`, `state_path`, and `cleanup_policy: iteration-baseline`
to every nested implementation/delivery stage. Register planning, companion,
implementation, review, and agent resources in this same ledger, not only the
PR's head branch. A nested stage must return resource-level cleanup evidence;
`preserved`, `converted`, or a missing report cannot satisfy this policy.

## Execute cleanup safely

1. Finish plan delivery (or mark an obsolete skipped plan `superseded`), verify the real platform-reported merge commit on the
   target and exact target CI through `pr-delivery`. Settle agents and commands.
2. Preserve plans and evidence before removing their checkout. Deliver companion
   plan history through its repository rules or use a documented durable archive
   outside disposable worktrees. Verify the archive is readable and contains any
   unique history before deletion. A PR merge does not prove later plan/progress
   commits are preserved. Keep original plan paths as provenance and record the
   durable lookup location in verification evidence.
3. Reinspect exact ownership, current branch tips, worktree assignments, and
   tracked/untracked dirt immediately before each deletion. Refuse changed tips,
   dirty work, unpreserved commits, locked/in-use worktrees, and ambiguous owners.
   Follow the repository's exact one-off permission requirements. This contract
   does not expand deletion authority or authorize force-removing dirty work.
4. From a surviving checkout, remove clean owned worktrees before their local
   branches; delete owned remote branches only after delivery verification.
   Use the verified squash-merge cleanup path in `pr-delivery` when needed;
   ordinary head ancestry is insufficient for squash merges. Guard remote deletion
   against a changed head with an explicit expected-SHA lease. Never use a broad
   branch sweep, global prune, or branch-name prefix as ownership proof.
5. Persist each successful deletion as `cleaned` after verifying absence. On a
   crash, re-inspect and reconcile already absent registered resources; absence
   is idempotent success, not an excuse to repeat destructive commands. Retain
   other resources with exact blocker evidence. Stop before the next scrub.
6. In the current iteration, while still at `implementation`, `scrub`, or
   `closeout`, run:

   ```bash
   python3 <skill-dir>/scripts/run_state.py verify-cleanup --path <state.json>
   ```

   This requires settled plans/PRs, verified merges/CI, cleaned resources, and
   live inventory equality. It records a cleanup check atomically. Run it once
   at iteration 0 before advancing to iteration 1, too.
7. Reload state before constructing the next candidate (the revision may have
   advanced). `replace` performs a fresh live check on every iteration increment,
   transition into `rescrub`, and completion. A stale receipt or manually marked
   `cleaned` resource cannot bypass an actual branch/worktree leak. Increment by
   one in a separate transition before reserving next-iteration resources.
   `rescrub` denotes the cleaned boundary of the finished iteration; when
   incrementing the iteration, set `stage: scrub` for the new discovery pass.

No resource is carried across iteration boundaries, including an orchestration
or companion worktree. Deferred deployment must use a pre-existing deployment
checkout, or temporary resources that are registered and cleaned before final
verification. At an iteration limit or requested stop boundary, complete safe
cleanup first and report incomplete discovery separately from cleanup status.

## Unexpected changes and final report

Inventory mismatch is evidence to investigate, never deletion authorization.
Preserve unregistered additions and missing baseline-resource evidence. If
concurrent work changes the baseline inventory, report that conflict without
resetting the baseline, deleting another owner's resources, or claiming exact
restoration. Git and remote reads are observational rather than a global lock;
the exact restoration guarantee assumes no concurrent resource mutations.

Report starting/final counts separately for local branches, each remote endpoint,
and worktrees, together with exact set equality and zero remaining owned
resources. A blocked/interrupted run may retain recoverable work; it must never
report successful cleanup or clean-loop completion.
