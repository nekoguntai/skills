---
name: frontend-pr-loop
description: End-to-end autonomous frontend/UI improvement and PR delivery loop for application repositories. Use when the user asks Claude to run /frontend-pr-loop:frontend-pr-loop, run a frontend PR loop, analyze frontend/UI usability or visual navigation, make recommendations without changes, turn recommendations into a plan, implement a UI plan, triage an open frontend PR, deliver/merge a PR, or rebuild/verify running containers after merged frontend work. A bare /frontend-pr-loop:frontend-pr-loop or frontend PR loop request is explicit authorization to inspect, choose a bounded improvement, implement it, verify it, open/update a PR, monitor checks, merge safely, and report the result unless the user says recommendations/plan/no changes only.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# Frontend PR Loop

Use this skill to run the recurring frontend loop cleanly. A bare `/frontend-pr-loop:frontend-pr-loop`, `$frontend-pr-loop`, or "run the frontend PR loop" means autonomous delivery mode: inspect the frontend, choose a bounded improvement, make a short working plan, implement it, verify it, and use PR delivery through merge without asking the user to proceed between phases.

Only stop after analysis when the user explicitly asks for recommendations, ideas, analysis, a review, a plan, or no changes.

## Decision Flow

1. Read repo instructions first: `AGENTS.md`, `CLAUDE.md`, `docs/`, and active `docs/plans/` notes when present.
2. Classify the request:
   - **Autonomous loop / bare invocation:** for `/frontend-pr-loop:frontend-pr-loop`, `$frontend-pr-loop`, "run the frontend PR loop", "frontend PR loop", or equivalent, do the full loop end to end. Do not stop at recommendations or ask "should I proceed?" Choose one coherent, bounded frontend improvement if the user did not name a specific target. Implement, verify, commit, push, open/update the PR, monitor checks/reviews, merge safely, verify merge ancestry, and report. This mode is explicit PR delivery and merge authorization for the work created by this loop only.
   - **Recommend / analyze / no changes:** inspect only and do not edit files when the user explicitly asks for recommendations, ideas, analysis, review, or no changes.
   - **Plan:** write or update a checkable plan, usually under `docs/plans/`, when the user explicitly asks for a plan.
   - **Implement only:** apply the reviewed plan or the user's chosen recommendation in focused slices, update the plan if scope changes, and verify. Stop after local verification unless the request also includes PR/delivery/merge language or came from autonomous loop mode.
   - **Triage open PR / merge / deliver:** use `/pr-delivery:pr-delivery`. In autonomous loop mode, this is already authorized; otherwise do not merge unless the user explicitly requested delivery/merge.
   - **Rebuild running containers:** do this only when explicitly requested or after a delivered merge that requested it.
3. Preserve unrelated dirty work. Stage only task files. Never revert unrelated user changes.

If the loop finds no credible frontend improvement worth making, report that with evidence and do not manufacture a PR.

## Autonomous Loop Mode

In autonomous loop mode, run these phases without pausing for permission:

1. Inspect the repo and current dirty state.
2. Identify a small set of frontend findings with file references.
3. Pick the highest-value bounded slice that can be completed safely in the current repo state.
4. State the working plan briefly, then implement it.
5. Run focused verification first, then broader checks based on blast radius.
6. Use `/pr-delivery:pr-delivery` to commit only relevant files, push, open/update the PR, monitor CI/reviews, fix failures, merge safely, verify target-branch ancestry, and clean up.
7. Rebuild running containers only if the user explicitly requested it or the loop request included rebuild/runtime verification.

Do not ask the user to choose among recommendations in autonomous mode. If several improvements are viable, pick the most defensible one and leave the rest as follow-up notes after delivery.

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
- Apply verified plan-review comments and repeat until no actionable comments remain when the user asks for recursive review or completeness.

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

## PR Triage And Delivery

Use `/pr-delivery:pr-delivery` whenever the user asks to open, deliver, merge, monitor, or clean up a PR.

Autonomous loop mode counts as an explicit request to open/update, deliver, and merge the PR for this loop. Load and follow the `pr-delivery` skill; do not ask for another confirmation before PR creation or merge unless a blocker creates new risk outside the requested loop.

Required delivery checks:

- Identify the forge and default branch from the remote, not assumptions.
- Confirm unrelated dirty files are excluded.
- Push the branch, open or update the PR, and include summary plus verification.
- Monitor CI, required statuses, and reviews until mergeable.
- Fix failures with real changes and local reproduction before retrying.
- Merge only after required checks are green and review blockers are absent.
- Verify the platform-reported merge commit exists and is reachable from the target branch.
- Clean up branches only after merge ancestry verification.

## Post-Merge Rebuild

When requested, rebuild from the merged target branch and verify runtime health:

```bash
git switch <target-branch>
git pull --ff-only origin <target-branch>
docker compose up -d --build app worker
docker compose ps
curl http://127.0.0.1:13000/api/health
curl http://127.0.0.1:13000/api/ready
```

Report what was verified and what was not. Mention any unrelated dirty files left untouched.
