# Grade Loop Cleanup Contract

This contract applies at every iteration boundary and every terminal exit,
including an initial audit with no findings, successful completion, exhausted
pass budget, deferment, and a blocker. The durable run state lives outside all
checkouts and worktrees. Its immutable starting baseline is the authority for cleanup.

## Provider and state

Use only the API 1 Git inventory provider bundled with the required
`pr-delivery` skill. Resolve `pr-delivery` at startup and set
`PR_DELIVERY_SKILL_DIR` to that resolved directory. If API 1 cannot be loaded,
stop before changing repository state. Do not recreate the provider locally or
compare a reduced inventory.

Use grade-loop's `run_state.py` CLI for durable state. Initialize state and
capture the iteration-1 baseline before reserving or creating any branch or
worktree. The durable state stores artifacts outside every checkout and keeps
one stable repository root. Read [run-state-schema.md](run-state-schema.md) for the exact CLI and fields.

Reserve every owned resource before creation, including local and remote
branches, worktrees, reviewer resources, planning and audit resources, delivery
resources, and resources in companion repositories. Pass the run ID,
iteration, state path, state helper, and `iteration-baseline` policy to nested `pr-delivery`
work. The nested delivery workflow performs its normal safe cleanup; the outer
loop must still verify the entire baseline inventory afterward.

## Artifacts and safe cleanup

Each grade invocation writes a report and history. Before removing its audit
branch or worktree, archive both source files with the run-state archive command
using kinds `report` and `history`. Archive plans and supporting evidence with
their corresponding kinds before they can be lost. Run `run_state.py verify-artifacts --path <state-path>` before cleanup to
check archive hashes and confirm the latest copy of each source is current. The audit
record must cite the archived report and history, the source SHA, and phase
`initial` or `post`. Every delivered iteration requires a post audit.

Before removing audit resources, preserve the canonical report/history in a
permitted pre-existing checkout or authorized delivery without overwriting
unrelated edits or losing history. External archives alone do not replace
requested repository outputs. If safe preservation is unavailable, retain the
work and mark cleanup blocked; do not invent delivery authority.

After archival and canonical-output preservation, remove only resources reserved by this run and only when they
are safe to remove. Preserve dirty unrelated files and unrecognized resources.
Delete remote branches only with an expected-SHA lease after rechecking their
current tips. Remove loop-generated report/history files only after their
archives have been verified. Do not use broad destructive cleanup. If a resource
cannot be safely removed, record the exact resource and reason; do not claim
cleanup succeeded.

No resource may be converted or carried into a later pass. Clean up the
iteration's audit, planning, implementation, review, delivery, and companion
resources before advancing. The next iteration starts with a new audit branch
or worktree from the refreshed target branch.

## Verification and exits

At each iteration boundary and before every terminal exit, run
`run_state.py verify-cleanup --path <state-path>` and require whole-inventory
equality with the immutable starting baseline. Then run
`run_state.py validate --path <state-path>` and capture
`run_state.py summary --path <state-path>` for the final record. A successful
cleanup requires both state validation and inventory verification to pass.

Record complete/deferred status and any required `reason` via `replace` after cleanup
verification, then validate. Completion/deferral triggers another live check:

- `complete` when no major actionable finding remains;
- `deferred` when findings remain and work stops because of scope, evidence,
  product/operational choice, or exhausted pass budget;
- `blocked` when required work remains blocked: record a reason at the current
  stage without pretending cleanup has passed; this state is resumable.

For a blocked run, preserve resources that contain unresolved work when cleanup
would destroy it. Report each retained resource and the blocker, and do not
represent the run as a successful cleanup or completed remediation. If the
blocked state still permits safe cleanup without losing work, perform and
verify it. Do not initialize a new iteration unless the prior iteration's
cleanup is verified.

Never rerun `grade` only to recreate a lost report or history entry. If required
audit evidence cannot be recovered from its verified archive, mark the run
blocked and preserve available state. At pass-budget exhaustion, archive the
latest audit and selected deferred finding, record the reason, then perform the
same cleanup and validation required for any other terminal exit.
