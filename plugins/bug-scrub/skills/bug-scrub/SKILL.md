---
name: bug-scrub
description: Evidence-driven bug scrub for a repository or diff. Use when the user asks Codex to hunt for bugs, scrub a codebase for defects, find high-confidence correctness issues, inspect a large codebase for likely failures, or produce a bug-focused triage report before fixing selected issues.
---

# Bug Scrub

Use this skill to find likely real bugs, not style issues or broad refactors.
Default to read-only analysis unless the user explicitly asks to fix, deliver,
or open a PR.

## Operating Principles

- Prioritize bugs that can change behavior: crashes, data loss, security or
  authorization failures, incorrect calculations, broken contracts, races,
  missing validation, resource leaks, flaky lifecycle behavior, and user-visible
  UI state errors.
- Every finding needs concrete evidence: file and line, failure path, why the
  current behavior is wrong, and the smallest convincing verification.
- Prefer fewer high-confidence findings over a long speculative list.
- Do not report formatting, naming, dead code, or architecture preferences
  unless they directly create a bug.
- Preserve unrelated dirty work. Do not edit files in read-only mode.

## Request Modes

- **Read-only scrub:** bug hunt, bug scrub, find bugs, audit for defects, review
  for correctness. Analyze and report; do not change files.
- **Diff scrub:** if the user names a PR, branch, commit, or `--diff`, focus on
  changed files plus impacted callers and contracts.
- **Large-codebase scrub:** if the user explicitly authorizes subagents,
  delegation, or parallel agent work, use bounded subagent sharding in the
  analysis phase when the tool is available. If the user only says the repo is
  large, analyze locally in priority order or ask before spawning.
- **Fix mode:** if the user asks to fix selected bugs, implement only the
  selected bounded slice, add regression tests, run focused verification, and
  stop unless delivery/merge was also requested.
- **Delivery mode:** if the user asks to open, deliver, merge, or monitor a PR,
  use `pr-delivery` after local verification and after an adversarial
  implementation review for any code changes.

## Preflight

1. Read repo instructions such as `AGENTS.md`, `CLAUDE.md`, project docs, and
   relevant active plans.
2. Run `git status --short --branch`, `git branch --show-current`, and
   `git show -s --format='%h %D %s' HEAD`.
3. Identify the stack and guarded test commands from local docs and scripts.
4. If DB-backed, browser, lifecycle, or integration tests are relevant, read the
   repo's test-isolation docs before running them.
5. Determine analysis scope: whole repo, diff, named subsystem, or suspected
   bug class.

## Baseline Inventory

Use fast mechanical signals to map the codebase before deep reading:

```bash
rg --files -g '!node_modules' -g '!vendor' -g '!dist' -g '!build' -g '!coverage'
git diff --name-only
git diff --stat
git diff --name-only <base>...HEAD
git diff --stat <base>...HEAD
rg -n 'TODO|FIXME|HACK|throw new Error|catch \(|Promise\.all|setTimeout|setInterval|Date\(|Math\.round|parseFloat|parseInt|JSON\.parse|localStorage|sessionStorage'
rg -n 'auth|permission|role|tenant|csrf|token|secret|password|encrypt|decrypt|transaction|rollback|retry|idempot|lock|mutex|queue|worker|webhook'
```

Use the plain `git diff` commands for uncommitted work. Use `<base>...HEAD`
when the request names a base branch, commit, PR, or `--diff`; determine
`<base>` from the user's argument, PR target branch, or remote default branch.
Adapt the commands to the stack. Prefer structured tools and local scripts over
ad hoc grep when the repo provides them.

## Bug Domains

Inspect the domains that match the codebase and request:

- **Trust boundaries:** authn/authz, tenant scoping, CSRF, webhook signatures,
  file upload/download, secrets, environment parsing, and input validation.
- **Persistence:** transactions, migrations, repository boundaries, idempotency,
  lost updates, stale reads, data retention, cascade behavior, and nullability.
- **API contracts:** request/response schemas, route params, status codes,
  pagination, sorting, date/time zones, currency, rounding, and version drift.
- **Async and lifecycle:** queues, workers, retries, cancellation, timers,
  cleanup, singleton state, resource leaks, concurrency, and race conditions.
- **Frontend state:** form submission, optimistic updates, stale cache,
  disabled/loading states, URL state, empty/error states, accessibility-driven
  behavior, and responsive layout that blocks use.
- **Error handling:** swallowed errors, missing context, retry storms, partial
  failure behavior, and inconsistent user or API errors.
- **Tests and CI:** missing regression coverage around risky behavior, flaky
  setup, unsafe shared state, direct unguarded test commands, and fixtures that
  mask bugs.
- **Recent changes:** modified files, recently merged code, new abstractions,
  compatibility shims, generated files, and integration boundaries touched by
  the diff.

## Large-Codebase Subagent Strategy

For large repositories, subagents are useful for coverage, but only when the
user explicitly authorizes subagents, delegation, or parallel agent work in the
current request. If that authorization is absent, do the same shards locally in
priority order or ask one concise question before spawning.

Use the main agent as coordinator:

1. Build the baseline inventory and choose shards from real repo structure.
2. Assign non-overlapping read-only analysis scopes.
3. Keep the immediate blocking work local; use subagents for sidecar inspection.
4. Cap concurrency to 3-6 explorer subagents for large repos.
5. Give each subagent the same finding format and tell it not to edit files.
6. Deduplicate and verify every P0/P1 finding before reporting it.
7. Treat subagent output as leads, not proof.

Recommended shards:

- Entrypoints and trust boundaries.
- Persistence, migrations, transactions, and data integrity.
- Async jobs, workers, retries, webhooks, and lifecycle cleanup.
- Frontend state, forms, navigation, and user-visible failures.
- Tests, fixtures, CI, and isolation risks.
- Diff/recent-change impact and caller contract drift.

Subagent prompt shape:

```text
Read-only bug scrub. Scope: <paths/domains>. Do not edit files.
Return only high-confidence bug findings.
For each finding include severity, file:line, failure path, evidence, false-positive check, and suggested verification.
Do not report style/refactor preferences.
```

## Finding Standard

Use this severity scale:

- **P0:** security break, data loss/corruption, production outage, or impossible
  core workflow.
- **P1:** high-confidence user-visible bug, authorization leak, broken API
  contract, race, persistence error, or failing critical path.
- **P2:** real bug with narrower scope, edge-case correctness issue, missing
  guard that can fail under plausible inputs, or important test isolation bug.
- **P3:** low-blast-radius defect with a concrete trigger and bounded impact.

Accept a finding only when it has:

- a concrete path to failure;
- file and line references;
- expected vs actual behavior;
- why existing tests or guards do not catch it;
- a minimal reproduction, test, or verification command.

Reject or defer findings that are speculative, purely stylistic, impossible to
trigger, already covered by a guard, or require product policy the repo does
not define.

## Synthesis

After local and subagent analysis:

1. Reread the relevant code for every candidate P0/P1 and representative P2s.
2. Check callers, data flow, and tests before trusting a finding.
3. Merge duplicates and keep the strongest evidence.
4. Run focused commands only when they are safe and likely to prove or disprove
   a finding.
5. If a finding depends on runtime state you cannot inspect safely, mark the
   evidence gap instead of overstating certainty.

## Output

For read-only scrubs, do not write files unless the user explicitly requested a
report file. If the user did request a file and the report is longer than
roughly 30 lines, write it to an appropriate location:

- `docs/plans/bug-scrub-report.md` when repo instructions allow bug analysis in
  the app repository;
- the documented private-plans location for private operational details;
- otherwise a temporary report path and a concise final summary.

When no report file was requested, keep the response concise and include only
the highest-signal findings inline.

Report findings first, ordered by severity:

```markdown
## Findings

- P1 - <title>
  Evidence: <file:line> and <failure path>
  Impact: <behavioral consequence>
  Verification: <smallest convincing command/test/repro>
  Fix direction: <bounded remediation>

## No Finding / Deferred

- <candidate> deferred because <missing evidence or policy decision>

## Verification

- <commands run>
- <commands not run and why>
```

If no high-confidence bugs are found, say that clearly and list the strongest
residual risks or uninspected areas.

## Fix Mode

When the user asks to fix bugs:

1. Select the smallest coherent set of related findings.
2. Update or create a short plan when the fix is non-trivial.
3. Add regression tests that fail for the bug when practical.
4. Implement using existing repository patterns and helpers.
5. Run focused verification, then broader checks based on blast radius.
6. Run an adversarial implementation review before `pr-delivery` for any code
   changes that will be delivered.
7. Use `pr-delivery` only when the user explicitly asked for delivery or merge.

Do not hide unrelated cleanup inside a bug fix.
