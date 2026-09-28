---
name: frontend-pr-loop
description: End-to-end autonomous frontend/UI improvement and PR delivery loop for application repositories, with stale-context resets at startup and between PR passes. Use when Codex is asked to run $frontend-pr-loop, run a frontend PR loop, analyze frontend/UI usability or visual navigation, make recommendations without changes, turn recommendations into a plan, implement a UI plan, triage an open frontend PR, deliver/merge a PR, rebuild/verify running containers after merged frontend work, or rerun a frontend loop check. A bare $frontend-pr-loop is an explicit request to inspect, choose a bounded improvement, implement it, verify it, open/update a PR, monitor checks, merge safely, verify target-branch post-merge CI, rebuild already-running localhost app containers, run a bounded post-closeout frontend reinspection, and report the result unless the user says recommendations/plan/no changes only.
---

# Frontend PR Loop

Use this skill to run the recurring loop cleanly. A bare `$frontend-pr-loop` or "run the frontend PR loop" means autonomous delivery mode: inspect the frontend, choose a bounded improvement, make a short working plan, implement it, verify it, run a pre-delivery adversarial implementation review, use PR delivery through merge, verify target-branch post-merge CI, rebuild already-running localhost app containers, rerun a bounded frontend inspection, and clear stale context at startup and between PR passes without asking the user to proceed between phases.

Only stop after analysis when the user explicitly asks for recommendations, ideas, analysis, a review, a plan, or no changes.

## Decision Flow

1. Read repo instructions first: `AGENTS.md`, `CLAUDE.md`, `docs/`, and active `docs/plans/` notes when present.
2. Classify the request:
   - **Autonomous loop / bare invocation:** for `$frontend-pr-loop`, `/frontend-pr-loop`, "run the frontend PR loop", "frontend PR loop", or equivalent, do the full loop end to end. Do not stop at recommendations or ask "should I proceed?" Choose one coherent, bounded frontend improvement if the user did not name a specific target. Clear stale context at startup, implement, verify, run a pre-delivery adversarial implementation review, commit, push, open/update the PR, monitor checks/reviews, merge safely, verify merge ancestry, verify target-branch post-merge CI, rebuild already-running localhost app containers, rerun a bounded frontend inspection from refreshed target-branch state, and report. This mode is explicit PR delivery and merge authorization for the work created by this loop only.
   - **Recommend / analyze / no changes:** inspect only and do not edit files when the user explicitly asks for recommendations, ideas, analysis, review, or no changes.
   - **Plan:** write or update a checkable plan, usually under `docs/plans/`, when the user explicitly asks for a plan; use `$recursive-plan-review` when invoked or when the user asks to make the plan complete.
   - **Implement only:** apply the reviewed plan or the user's chosen recommendation in focused slices, update the plan if scope changes, and verify. Stop after local verification unless the request also includes PR/delivery/merge language or came from autonomous loop mode.
   - **Triage open PR / merge / deliver:** use `$pr-delivery` directly only for existing PR work with no new local implementation. If the request includes implementation plus delivery, complete the Pre-Delivery Adversarial Review gate before `$pr-delivery`. In autonomous loop mode, this is already authorized; otherwise do not merge unless the user explicitly requested delivery/merge.
   - **Rebuild running containers:** after any delivered autonomous loop merge, rebuild only app containers that are already running locally. For standalone rebuild requests, rebuild only when explicitly requested.
3. Preserve unrelated dirty work. Stage only task files. Never revert unrelated user changes.

For autonomous, planning, implementation, or delivery work, resolve the
`pr-delivery` skill and read its `references/loop-execution.md` and
`references/loop-run-state.md` before delegating work, changing repository
files, or creating Git resources. Follow the cheap-worker/strong-coordinator
rules, API 1 inventory provider, and shared state helper. If required tooling is
unavailable, stop before resource or repository mutation and report the
blocker. Pure read-only recommendation/no-files requests do not initialize
state, write reports/plans, or create cleanup work.

## Run State And Cleanup Baseline

For an authorized request that will write a plan, change code, create Git
resources, or deliver changes, initialize one durable run outside every
checkout and worktree before those writes or resource creation. Keep `repo_root`
stable and capture the primary and any companion repository baselines first:

```text
python3 <pr-delivery-dir>/scripts/loop_state.py init --workflow frontend-pr-loop \
  --path <state-path> --run-id <run-id> --repo-root <repo-root> \
  --target-branch <target-branch> --current-sha <current-sha> \
  --max-passes 2 [--companion-repo <repo-root> ...]
```

Read `loop-run-state.md` for the full schema and command forms. Use the helper's
`replace`, `archive`, `verify-artifacts`, and `verify-cleanup` operations for
state changes. Record each frontend inspection in the run's audit records with
source SHA, outcome, and archived report/evidence; non-grade observations may
have empty history. When invoked by an outer loop, inherit its `run_id`, `iteration`,
`state_path`, `state_helper`, and `cleanup_policy: iteration-baseline`; never
initialize a nested baseline or complete the caller's goal. Return
exact-resource absence evidence to the caller, which owns whole-pass cleanup
verification. Reserve every owned branch/worktree before creation, including
worker, review, audit, delivery, and companion resources. Archive the inspected
report/evidence, plan revisions, screenshots, and other evidence before
removing their worktree; verify archive bytes and the latest source copy before
cleanup. The helper records ownership but does not delete resources. Restore
the original checkout assignment and require exact baseline equality before
advancing, finishing, or deferring. Reuse the archived frontend inspection
when the target SHA is unchanged; refresh it when the target advances.

Apply the same live target-SHA and inventory gate after an initially clean
inspection, after each delivery, and at pass-budget or scope deferral. No
converted branch/worktree or leftover counts as successful cleanup. If cleanup
would erase requested work or require a merge the request did not authorize,
preserve the work and report a resumable cleanup blocker. When no resources were
created, do not issue deletion commands or manufacture an ownership sweep.

Local-only implementation and explicit plan requests preserve their desired
edits in the permitted checkout and do not gain PR/merge authority. An external
archive is recovery evidence, not a substitute for the requested plan, code,
report, or screenshot output.

## Worker Delegation And Delivery Grouping

Use the larger capable model as coordinator. Delegate bounded frontend
investigations, implementation slices, tests, and independent verification to
cheaper suitable workers, preferring `gpt-6-luna` where available. Give each
worker non-overlapping ownership, relevant source/plan SHA, constraints, and
acceptance evidence. The coordinator confirms findings, inspects actual diffs,
runs final verification on the integrated tree, and owns scope, state, delivery,
and cleanup. Workers never push, open or merge PRs, edit the operational ledger,
or delete shared resources. Reserve and settle worker resources before cleanup.
Keep the adversarial reviewer independent from the implementation author; its
single review gate does not limit other bounded delegation.

Group all compatible changes selected for one pass into one reviewed delivery
group and one PR where possible. Workers may produce separate local commits;
the coordinator integrates them on one delivery branch, reviews the combined
diff, and runs final combined gates. Split only for distinct repositories,
incompatible permissions/protection, required deployment or migration
sequencing, or a reviewed dependency/risk boundary. Record split reasons and
order; internal phases and separate commits alone do not justify extra PRs.

If the loop finds no credible frontend improvement worth making, archive the
inspection evidence, record the clean result, and pass the shared live
target-SHA and cleanup gate before finishing. Do not manufacture a PR.

## Pass Budget

Run at most two autonomous delivery passes by default, with a post-closeout
frontend inspection after each delivery. The durable `maxPasses` value is the
bound. An initially clean inspection needs no delivery.

After the autonomous follow-up budget is exhausted, report the next selected finding and stop with a deferral instead of opening an unbounded sequence of PRs.

## Branch And Worktree Ownership

The shared durable run state is the only ownership ledger. Use distinctive
names such as `codex/frontend-pr-loop/<issue-slug>` and reserve each owned
branch/worktree before creation. Preserve unrelated dirty work and never infer
ownership from a branch prefix. Do not convert resources between passes or
report leftovers as successful cleanup. After each delivery group and at final
closeout, remove only safe resources proven to belong to this run and verify
that original branch names and worktree assignments are restored exactly.
Ordinary plan or code edits that create no Git resources may remain in a
permitted pre-existing checkout as requested output; archive required evidence
and preserve unrelated changes.

## Autonomous Loop Mode

In autonomous loop mode, run these phases without pausing for permission:

1. Inspect the repo and current dirty state.
2. Identify a small set of frontend findings with file references.
3. Pick a bounded set of compatible findings for one delivery group. Use the
   shared coordinator/worker rules rather than concentrating routine analysis
   and implementation on the coordinator.
4. State the working plan briefly in commentary. If the slice is broad, changes shared primitives, or creates/updates a plan file, run `$recursive-plan-review` on the plan and apply verified comments before implementation.
5. Run focused verification first, then broader checks based on blast radius.
6. Run the pre-delivery adversarial implementation review and resolve verified findings.
7. Integrate compatible worker changes on one owned delivery branch. Run final
   combined verification, then use `$pr-delivery` for one PR for this pass
   where possible: commit only relevant files, push, open/update, monitor
   CI/reviews, fix failures, merge safely, verify target-branch ancestry and
   post-merge CI, then clean up.
8. Rebuild already-running localhost app containers after the verified merge and green target-branch CI.
9. Reconcile the target SHA, then reuse the archived inspection if it is still
   for that exact SHA; otherwise run a fresh bounded inspection on the refreshed
   target. Archive and register the post-closeout evidence, settle its workers
   and any owned resources, then verify exact baseline restoration before a
   clean exit, deferral, or pass advance. If a major actionable item remains
   and the budget allows it, advance durable state and start a fresh pass from
   new owned resources.

Do not ask the user to choose among recommendations in autonomous mode. If several improvements are viable, pick the most defensible one and leave the rest as follow-up notes after delivery.

## Context Reset Discipline

At startup and after each delivered PR before post-closeout inspection or another pass, clear stale context:

1. Treat prior conversation analysis, branch-local observations, screenshots, and subagent conclusions as stale unless confirmed by the current request, merged code, plan files, PR state, CI output, or a fresh source read.
2. Finish PR delivery cleanup first: verify the platform-reported merge commit is reachable from the target branch, verify target-branch CI, fetch the target branch, and ensure no PR monitoring or long-running command sessions remain active.
3. Re-read repository instructions, relevant plans, current frontend source, current dirty state, default branch HEAD, CI state, and running app/container state before rebuild, post-closeout inspection, or another pass.
4. Classify any dirty files discovered after the merge before editing again; preserve unrelated work and never treat generated loop-check dirt as canonical unless it is intentionally carried into the next pass.
5. Start post-closeout inspection and any follow-up pass from the refreshed target-branch state, not from the merged PR branch, original findings list, or unverified local assumptions.

This reset is context hygiene, not destructive cleanup: do not discard unrelated work, reset the worktree, restart services, or rebuild stopped containers unless repository instructions or the user require it.

## Read-Only Frontend Analysis

For recommendation-only work, gather evidence without changing files.

Use commands like:

```bash
git status --short --branch
find src/components -maxdepth 2 -type f \( -name '*.tsx' -o -name '*.ts' \) -print | xargs wc -l | sort -nr | head -40
rg -n 'role="tablist"|<Tabs|useUrlTabState|DataList empty=""|renderWhenEmpty|systemViews|QuickLinks|sectionQuick' src/components src/test
rg -n 'TODO|FIXME|owner-section|migration|override|tabs|nav|sidebar|metric|panel' src/app/styles.css docs
```

Inspect these surfaces before recommending:

- App shell, routing, topbar/search, status/sidebar, theme, and bootstrap/mutation coordination.
- `PageFrame`, section registry/group metadata, quick links, and command/search navigation.
- `Tabs`, URL tab state, segmented controls, `DataTable` system views, `DataList`, and empty states.
- Largest page containers and mixed model/layout/form files.
- CSS ownership, late migration blocks, hard-coded colors, responsive overrides, and section accent rules.
- Existing tests around the touched primitives and page surfaces.

Return prioritized recommendations with file references. If the user said "no changes", do not create a report file unless they explicitly ask for one.

## Planning Mode

Create a plan that is executable, not aspirational:

- State goal, non-goals, assumptions, phases, dependencies, verification gates, acceptance criteria, and backout notes.
- Keep UI direction quiet, dense, and work-focused unless the user asks for redesign.
- Separate visual changes from mechanical refactors unless the visual change is the point.
- For broad UI work, include screenshot or Playwright verification only when rendered behavior materially changes.
- Use `$recursive-plan-review` on the plan when invoked, when completeness is requested, or when autonomous mode creates/updates a non-trivial plan. Apply verified comments and repeat until no actionable comments remain.

## Implementation Mode

Implement conservatively:

- In autonomous loop mode, do not return recommendations and wait. Once there is enough evidence, choose a bounded slice and execute it.
- Prefer existing primitives and local patterns over new abstractions.
- Extract pure model builders and focused panels before changing visual behavior in large containers.
- Add or update tests near the changed primitive/page.
- Keep plan evidence current when the implementation diverges from the plan.
- Avoid direct DB/browser commands when the repo provides guarded wrappers.

Useful verification ladder:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
npm run css:tokens
npm run ci:static
npm run test:e2e:ci
git diff --check
git diff --cached --check
```

Use focused tests first, then broaden based on risk.

## Pre-Delivery Adversarial Review

Before using `$pr-delivery` for implementation work, run this gate after local
verification and before staging for commit. The loop invocation authorizes one
independent reviewer for this gate. That reviewer remains separate from the
implementation author; this gate does not limit other bounded worker delegation
under the shared execution contract.

Spawn one fresh reviewer subagent and give it the minimum useful context:

- selected issue, plan path when present, and non-goals;
- current diff, changed files, and any screenshots or rendered-state evidence
  for user-facing visual changes;
- focused and broad verification commands already run, with failures or skips.

Ask the reviewer to find high-confidence bugs, regressions, accessibility or
responsive layout problems, plan drift, missing tests, scope creep,
verification gaps, and PR delivery blockers. Do not ask it to edit files,
stage, commit, push, or run delivery.

Do not load or run `$pr-delivery` until verified reviewer findings that could
affect correctness, UX, tests, or delivery are fixed or explicitly documented
as non-blocking. Rerun focused verification after fixes, and rerun the reviewer
only when the fixes materially change the implementation or the first review
found a blocker. Include the review outcome and any deferred findings in the PR
body or final response.

If any later delivery, CI-fix, review-fix, or post-merge recovery step requires
new implementation changes, return to this gate before continuing PR delivery
or opening the fix PR.

## PR Triage And Delivery

Use `$pr-delivery` whenever the user asks to open, deliver, merge, monitor, or clean up a PR. For requests that include new implementation work, this section starts only after the Pre-Delivery Adversarial Review gate is complete.

Autonomous loop mode counts as an explicit request to open/update, deliver, and merge the PR for this loop. Load and follow the `pr-delivery` skill; do not ask for another confirmation before PR creation or merge unless a blocker creates new risk outside the requested loop.

Required delivery checks:

- Identify the forge and default branch from the remote, not assumptions.
- Confirm unrelated dirty files are excluded.
- Push the branch, open or update the PR, and include summary plus verification.
- Monitor CI, required statuses, and reviews until mergeable.
- Fix failures with real changes and local reproduction before retrying.
- Merge only after required checks are green and review blockers are absent.
- Verify the platform-reported merge commit exists and is reachable from the target branch.
- After ancestry verification, wait for the target-branch CI workflow triggered by the merge commit to finish. Treat a failing, missing, or cancelled required target-branch run as a loop failure to diagnose before rebuild or post-closeout analysis. Inspect run/job output or reproduce locally, fix with a new PR when the failure is caused by the delivered work, then verify that new merge commit's target-branch CI is green.
- Clean up branches only after merge ancestry verification.

## Post-Merge Target-Branch CI

After the PR merge commit is verified reachable from the target branch, the autonomous loop is still not complete. Wait for the CI run triggered on the target branch by that exact merge commit or squash merge commit.

Provider guidance:

- **Forgejo:** query recent Actions runs filtered by the merge commit SHA when available; otherwise query recent target-branch `push` runs and match the head SHA/title. Confirm the required aggregate status and relevant jobs are `success`.
- **GitHub:** use `gh run list --branch <target-branch> --commit <merge-sha>` and `gh run view` or equivalent check-rollup commands. Confirm required post-merge checks are complete and successful.

If post-merge target-branch CI fails:

- Do not start another autonomous loop pass or merge another PR.
- Inspect diagnostics first, including infrastructure causes such as runner capacity, Docker availability, Compose collisions, stale generated files, browser setup, missing statuses, registry/network issues, or known flaky signatures.
- Reproduce the failing command locally when logs are unavailable or inconclusive.
- If the delivered work caused the failure, fix it in a new PR after rerunning the Pre-Delivery Adversarial Review gate for the fix, use `$pr-delivery`, merge it, and verify the target-branch CI for the new merge commit.
- If the failure is unrelated infrastructure or pre-existing drift, report the evidence and stop instead of claiming a clean closeout.

## Post-Merge Rebuild

After an autonomous loop merge with green target-branch CI, rebuild only app containers that are already running locally. Do not start stopped services only to satisfy this step. For non-autonomous requests, rebuild when the user explicitly asked for rebuild/runtime verification.

Detection:

- Inspect `docker compose ps` when the repo has a Compose file.
- Inspect `docker ps` for containers bound to localhost ports when Compose is absent or ambiguous.
- Use repo instructions to identify app services and health endpoints.

When matching app services are already running, rebuild from the merged target branch and verify runtime health:

```bash
git switch <target-branch>
git pull --ff-only origin <target-branch>
docker compose up -d --build app worker
docker compose ps
curl http://127.0.0.1:13000/api/health
curl http://127.0.0.1:13000/api/ready
```

If no matching localhost app containers are running, report that rebuild was skipped.

## Post-Closeout Frontend Loop Check

After merge verification and any required localhost rebuild/health checks,
reconcile the live target SHA. If the latest archived frontend inspection is
still for this exact SHA, reuse it; do not repeat the same inspection.
Otherwise run a fresh bounded frontend inspection from the synced target
branch. Archive and register its report/evidence and audit record before cleanup. Use an owned
worktree only when the inspection or report mutates repository files. Settle
workers and owned resources, then verify exact baseline restoration before any
pass advance, clean exit, or deferral.

Use the same selection standard as autonomous mode:

- If no credible major frontend improvement remains, record that result,
  preserve requested output, and complete the shared cleanup gate before
  finishing.
- If a major actionable frontend item remains, is feasible in another bounded
  PR, and the pass budget allows another autonomous delivery, verify cleanup
  and advance durable state before reserving fresh resources for the next pass.
  Group compatible selected changes into one reviewed PR where possible.
- If remaining issues are too broad, speculative, blocked by product decisions,
  or intentionally deferred, record the blocker or deferral, archive required
  evidence, and pass the shared cleanup gate. If cleanup is unsafe, retain the
  work and report a resumable blocker instead of forcing an unsafe PR.
- If a major actionable item remains after the pass budget is exhausted, record
  it as the next deferred phase, archive it, and pass the same shared live
  cleanup gate before stopping rather than opening another PR.

Do not keep looping indefinitely on low-evidence recommendations, purely aesthetic preferences, or previously rejected/deferred findings.

## Final Response

Report concisely:

- selected frontend issue and any deferred findings;
- plan path and recursive-plan-review pass count when a plan file was used;
- adversarial review outcome and any fixes or deferred findings from it;
- implementation changes and verification commands;
- PR number/link, forge type, merge commit, and ancestry verification;
- target-branch post-merge CI run and result;
- whether every pass restored the original branch and worktree inventory;
- container rebuild command and health/readiness results, or why rebuild was skipped;
- post-closeout frontend loop result and whether another pass was skipped, deferred, or completed;
- pass budget used and residual risks.
