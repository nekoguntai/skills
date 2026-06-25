---
name: grade
description: Strict, evidence-driven software quality audit of the current repository or a diff, with fresh repo-context checks before scoring and report writes. Produces or updates docs/plans/codebase-health-assessment.md with a scored ISO/IEC 25010-aligned report, mechanical tool-backed signals, hard-fail blockers, trend tracking, and actionable improvements. Use when the user types "$grade" or "/grade", asks to grade/audit/assess codebase health, compare diff quality, or create a codebase quality plan.
---

# Grade

Prefer evidence and repeatable signals over subjective impressions.

Do not stop at a chat-only summary unless the user explicitly says not to write files. In a repository, write or update `docs/plans/codebase-health-assessment.md`. If `docs/plans/` does not exist, create it. Preserve useful prior status notes when updating an existing assessment.

## Bundled Resources

Resolve these paths relative to this `SKILL.md` directory:

- `standards.md`: source of truth for the rubric, standards mapping, and threshold citations. Read it once per session before auditing.
- `grade.sh`: project-wide signal collector for tests, lint, typecheck, coverage, vulnerabilities, secrets, complexity, duplication, file size, operational enablers, and heuristic evidence.
- `diff_scan.sh`: diff-scoped signal collector for changed files.
- `heuristics.sh`: evidence hints for judged criteria; these are not direct mechanical scores.
- `trend.sh`: grade history and quality-delta helper. By default it writes repo-local history under `docs/plans/grade-history/`; `GRADE_HISTORY_DIR` can override this.

Run bundled scripts with `bash <skill-dir>/<script>` if executable bits are unavailable.

## Context Freshness

Before collecting signals, judging evidence, or writing the report, refresh the
repository context:

1. Establish the repo root, current request mode, base ref, branch, HEAD, and
   dirty state from disk. Do not rely on earlier conversation state.
2. Re-read repo instructions, the current report/history entry, relevant plans,
   and `standards.md`. Treat previous scores, old reports, and subagent output
   as leads until confirmed by current artifacts.
3. If HEAD, dirty files, base ref, or diff scope changes after an interruption
   or long-running command, rerun the affected signal collectors and judged
   inspections before scoring.
4. Preserve unrelated dirty work. Full mode includes the current working tree;
   diff mode must record the resolved base and changed-file scope explicitly.
5. Before the final report write, re-check `git status` and HEAD. If provenance
   changed, refresh it or stop and rerun instead of writing a stale assessment.

This is context hygiene, not destructive cleanup: do not reset the worktree,
discard changes, or rewrite report history to hide older runs.

## Loop-Check Invocation

Do not create or remove branches/worktrees for ordinary audits. When a loop
skill runs `grade` from a caller-created loop-check branch or temporary
worktree, write the report and history in the current checkout, record the
current branch/worktree path and generated files in Verification Notes, and
leave cleanup or conversion to the caller. Remove only temporary files that
`grade` itself created, such as diff-scope file lists.

## Spirit

`$grade` is an audit tool, not an opinion generator.

1. Anchor to real standards. Every mechanical threshold must trace back to `standards.md`.
2. Measure what can be measured. Judge what cannot be measured, but anchor each judgment to an ISO/IEC 25010 sub-characteristic and inspected evidence.
3. Never fake objectivity with weak grep proxies. A score is measured, judged, or unknown.
4. Cite every score with either `tool + threshold + exit status` or `ISO sub-characteristic + inspection target + evidence`.
5. Make low scores actionable with specific files, functions, thresholds, or missing artifacts.
6. Work across languages via native project tools and multi-language tools such as `lizard`, `jscpd`, and `gitleaks`.
7. Label runtime-only claims honestly. Static analysis can score DORA/SRE enablers, not live production latency, MTTR, or change-failure rate.
8. Flag divergent implementation paths as audit findings, but do not turn `/grade` into a cleanup plan. Recommend the `rationalize` skill when convergence needs decisions or sequencing.
9. Detect improvements explicitly. Report score movement, threshold crossings, within-bucket signal deltas, newly measured evidence, and lost evidence separately so real cleanup is visible even when the letter grade does not change.

## Arguments

| Invocation | Mode | Scope |
| --- | --- | --- |
| `$grade` or `/grade` | full | Audit the repository at HEAD, including the current working tree. |
| `$grade --diff` or `/grade --diff` | diff | Audit files changed between HEAD and the default base ref. |
| `$grade --diff <ref>` or `/grade --diff <ref>` | diff | Audit files changed against `<ref>`, such as `origin/main` or `HEAD~5`. |

Default base ref resolution for `--diff` with no ref:

1. Try `git rev-parse --verify main`.
2. Else try `git rev-parse --verify master`.
3. Else abort with: `Could not resolve a default base ref. Pass one explicitly.`

Record the resolved base ref in the report.

## Domains

| Domain | Weight | ISO/IEC 25010 alignment |
| --- | ---: | --- |
| Correctness | 20 | Functional Suitability: completeness, correctness, appropriateness |
| Reliability | 15 | Reliability: maturity, availability, fault tolerance, recoverability |
| Maintainability | 15 | Maintainability: modularity, reusability, analyzability, modifiability, testability |
| Security | 15 | Security: confidentiality, integrity, non-repudiation, authenticity |
| Performance | 10 | Performance Efficiency: time behavior, resource utilization, capacity |
| Test Quality | 15 | Functional Suitability plus Maintainability/Testability |
| Operational Readiness | 10 | Reliability/Availability plus Portability and Compatibility enablers |

Total: 100 points.

## Hard-Fail Gates

Cap the overall grade at **D (<=69)** and list blockers first when any concrete gate fires:

| Gate | Trigger | Source |
| --- | --- | --- |
| Tests broken | `tests=fail` | ISO 25010 Functional Correctness |
| Typecheck broken | `typecheck=fail` | ISO 25010 Functional Correctness |
| Hardcoded secrets | `secrets >= 1` | OWASP A07:2021, CWE-798 |
| High/critical vulnerabilities | `security_high >= 3` | OWASP A06:2021, CVSS >=7.0 |

Do not treat `timeout`, `missing`, or aspirational concerns as hard-fail gates. Score or report them as risks with confidence impact.

## Scoring Rules

Rows marked **[M]** are mechanical: apply the threshold directly to parsed signals. Rows marked **[J]** are judged: inspect targeted files and choose Low / Medium / High with a one-sentence ISO-anchored justification.

For judged rows:

- Read the evidence signals first.
- Inspect the file paths indicated by the evidence and by `rg` searches; cite concrete paths.
- Use direct inspection in Codex by default. Use subagents only when the user explicitly requests delegated or parallel analysis.
- If evidence signals are within +/-10% of the previous run and no material code change is detected, inherit the previous judged score unless specific new evidence justifies a change.

### 1. Correctness (20)

| # | Criterion | Kind | Signal / Source | Scoring |
| --- | --- | --- | --- | --- |
| 1.1 | Tests pass | [M] | `tests` from native test runner | `pass` +6; `timeout` +2; `fail` 0; `missing` 0 |
| 1.2 | Typecheck clean | [M] | `typecheck` from native typechecker | `pass` +4; `timeout` +2; `fail` with <=5 evident errors +2; `fail` with >5 errors 0; `missing` +2 |
| 1.3 | Lint clean | [M] | `lint` from native linter | `pass` +3; `timeout` +1; `fail` with <=10 evident issues +1; `fail` with >10 issues 0; `missing` +1 |
| 1.4 | Suppression density | [J] | `suppression_count`; Functional Appropriateness | Low 0 (>30/KLOC or critical-path clusters); Medium +2 (10-30/KLOC, non-critical); High +4 (<10/KLOC and justified) |
| 1.5 | Functional completeness | [J] | README/TODOs and `test_file_count`; Functional Completeness | Low 0 (large unfinished scope); Medium +1 (some gaps); High +3 (feature-complete against stated scope) |

### 2. Reliability (15)

All rows are judged because static tools do not measure runtime reliability.

| # | Criterion | ISO sub-characteristic | Evidence | Scoring |
| --- | --- | --- | --- | --- |
| 2.1 | Error handling quality | Fault Tolerance | `blocking_io_count`, external-call sites | Low 0 (silent/bare failures); Medium +3 (partial handling); High +6 (consistent typed/contextual handling) |
| 2.2 | Timeouts and retries | Availability, Fault Tolerance | `timeout_retry_count`, external-call sites | Low 0 (none where needed); Medium +2 (some coverage); High +4 (consistent on external I/O) |
| 2.3 | Crash-prone paths | Fault Tolerance | production use of panic/unwrap/assert/null-deref patterns | Low 0 (many in prod paths); Medium +2 (few/cold init only); High +5 (none or test/example only) |

### 3. Maintainability (15)

| # | Criterion | Kind | Signal / Source | Scoring |
| --- | --- | --- | --- | --- |
| 3.1 | Cyclomatic complexity | [M] | `lizard_warning_count` for functions with CCN >15 | `0` +5; `1-5` +3; `6-15` +1; `>15` 0; `unknown` +2 |
| 3.2 | Duplication | [M] | `duplication_pct` from `jscpd` | `<3%` +3; `3-5%` +1; `>5%` 0; `unknown` +1 |
| 3.3 | No god files | [M] | `largest_file_lines` | `<500` +2; `500-1000` +1; `>1000` 0; `unknown` +1 |
| 3.4 | Architecture clarity and path convergence | [J] | top-level layout plus divergent-path scan; Modularity/Reusability/Analyzability | Low 0 (flat/tangled or high-risk duplicate active paths); Medium +2 (some structure or known divergences with guardrails); High +3 (clear boundaries, no obvious cycles, no unjustified parallel implementations) |
| 3.5 | Readability/naming | [J] | spot-check 3-5 source files; Analyzability | Low 0 (cryptic/inconsistent); Medium +1 (mixed); High +2 (consistent and self-explanatory) |

### 4. Security (15)

| # | Criterion | Kind | Signal / Source | Scoring |
| --- | --- | --- | --- | --- |
| 4.1 | Dependency vulnerabilities | [M] | `security_high` from native audit tool | `0` +5; `1-2` +2; `>=3` 0 and hard-fail; `unknown` +2 |
| 4.2 | No hardcoded secrets | [M] | `secrets` from `gitleaks` or fallback | `0` +4; `>=1` 0 and hard-fail; `unknown` +2 |
| 4.3 | Input validation quality | [J] | `validation_lib_present`, handlers/entry points; Integrity | Low 0 (raw input reaches logic); Medium +1 (inconsistent validation); High +3 (validation at trust boundaries) |
| 4.4 | Safe system/API usage | [J] | `eval`, `innerHTML`, `shell=True`, `os.system`, string-built SQL; Integrity | Low 0 (dangerous patterns with user input); Medium +1 (minor/non-user-facing risks); High +3 (clean) |

### 5. Performance (10)

All rows are judged because runtime performance cannot be measured reliably from static code alone.

| # | Criterion | ISO sub-characteristic | Evidence | Scoring |
| --- | --- | --- | --- | --- |
| 5.1 | Hot-path efficiency | Time Behaviour | `blocking_io_count`, request handlers/main loops | Low 0 (clear hot-path inefficiency); Medium +2 (minor/cold-path issues); High +5 (clean) |
| 5.2 | Data access patterns | Resource Utilization | DB/API call sites | Low 0 (obvious N+1/full scans); Medium +1 (some concerns); High +3 (batched/index-aware) |
| 5.3 | No blocking in hot paths | Resource Utilization, Capacity | `blocking_io_count` | Low 0 (>5 in request handlers); Medium +1 (some cold init only); High +2 (zero in hot paths) |

### 6. Test Quality (15)

| # | Criterion | Kind | Signal / Source | Scoring |
| --- | --- | --- | --- | --- |
| 6.1 | Coverage | [M] | parse coverage percent from `grade.sh` COVERAGE output | `>=80` +5; `60-80` +3; `40-60` +1; `<40` 0; `unknown` +2 |
| 6.2 | Test structure | [J] | `test_file_count`, 2-3 test files; Testability | Low 0 (brittle/mock-heavy/snapshot-heavy); Medium +2 (mixed); High +4 (clear behavioral tests) |
| 6.3 | Edge cases covered | [J] | tests for null/empty/boundary/error cases; Functional Completeness | Low 0 (happy path only); Medium +1 (some edges); High +3 (explicit boundaries/failures) |
| 6.4 | No flaky patterns | [J] | `test_sleep_count`, time assertions; Testability | Low 0 (many sleeps/time-based assertions); Medium +1 (a few); High +3 (deterministic) |

### 7. Operational Readiness (10)

This domain scores static DORA/SRE enablers, not live production metrics.

| # | Criterion | Kind | Signal / Source | Scoring |
| --- | --- | --- | --- | --- |
| 7.1 | Deployment and CI enablers | [M] | `deploy_artifact_count` | `>=2` +3; `1` +1; `0` 0 |
| 7.2 | Health endpoints | [M] | `health_endpoint_count` | `>=1` +2; `0` 0 |
| 7.3 | Observability library present | [M] | `observability_lib_present` | `1` +2; `0` 0 |
| 7.4 | Logging quality | [J] | `logging_call_count`, 2-3 log sites; Availability support | Low 0 (absent/unstructured); Medium +1 (library present, inconsistent); High +3 (structured and contextual) |

Add domain points, cap each domain at its max, and sum to 0-100. Letter grade: A >=90, B >=80, C >=70, D >=60, F <60. If any hard-fail gate trips, cap the overall at D (<=69).

## Evidence Collection

Tool priority:

1. Native project tools: tests, lint, typecheck, coverage, dependency audit.
2. Multi-language analysis tools: `lizard`, `jscpd`, `gitleaks`.
3. Filesystem presence checks: CI, Docker/deploy artifacts, health endpoints.
4. Direct inspection for judged criteria, constrained to specific files.
5. Heuristic counts from `heuristics.sh` as hints only.

If a signal is `unknown`, use the `unknown` scoring column for mechanical criteria, list it under Missing, and lower confidence. Do not silently substitute weaker evidence for a missing real measurement.

## Divergent Path Lens

During judged maintainability inspection, identify likely divergent paths. This is a detection and risk-reporting pass, not a mandate to merge everything.

Look for:

- duplicate public contracts for the same domain object, endpoint, event, schema, or API response;
- parallel services, hooks, clients, handlers, adapters, or test fixtures with overlapping workflow names;
- legacy/current branches, compatibility shims, feature flags, or old/new naming that lack a retirement note;
- tests that prove similar behavior through separate stacks or helper layers;
- intentionally separate provider, platform, or boundary adapters that need explicit "keep separate" justification.

Classify each concrete candidate as:

- `justified` - separate paths encode different boundaries, providers, permissions, performance needs, or compatibility contracts;
- `watch` - duplication exists but current tests, manifests, or narrow ownership keep the risk contained;
- `rationalize` - active paths can drift, have already drifted, or make future changes likely to land in the wrong place.

For `/grade`, cite only evidence and risk. If the next step requires choosing a canonical path, migration order, delete order, or compatibility policy, recommend the `rationalize` skill instead of embedding a full cleanup plan in the audit.

## Confidence

- High: native tools ran, at least two of `lizard`, `jscpd`, `gitleaks` ran, and coverage is known.
- Medium: most native tools ran but some universal tools or coverage are missing.
- Low: multiple native tools are missing or all three universal tools are missing.

State confidence and name the missing tools/signals.

## Output Format

Write this report to `docs/plans/codebase-health-assessment.md` unless the user specifies a different path.

Begin the file with the Prismatic Thread front matter below so the report is
classified as an audit record (kept out of the review queue) rather than flagged
as untracked work needing review. Fill `summary` with the one-line score line. If
the repository does not use Prismatic Thread the front matter is harmless.

```markdown
---
thread: codebase-health-assessment
threadTitle: Codebase Health Assessment
artifactKey: codebase-health-assessment
type: plan
format: markdown
title: "Software Quality Report"
status: approved
summary: "<grade>/<100>, <A-F>, <commit> — audit record."
tags:
  - grade
  - audit
metadata:
  workStatus: audit
  disposition: audit
---

# Software Quality Report

Date: YYYY-MM-DD
Owner: TBD
Status: Draft

**Overall Score**: <0-100>/100
**Grade**: <A|B|C|D|F>
**Confidence**: <High|Medium|Low>
**Mode**: <full | diff vs <base_ref> (<N> files)>
**Commit**: <short-sha>

---

## Hard-Fail Blockers
<List blockers with exact signal values, or "None".>

---

## Domain Scores

| Domain | Score | Notes |
| --- | ---: | --- |
| Correctness | X/20 | ... |
| Reliability | X/15 | ... |
| Maintainability | X/15 | ... |
| Security | X/15 | ... |
| Performance | X/10 | ... |
| Test Quality | X/15 | ... |
| Operational Readiness | X/10 | ... |
| **TOTAL** | **X/100** | |

---

## Trend
- `No prior runs - baseline established.`
- or `vs <prev date> (<prev commit>): overall <+N|-N|+/-0>, grade <prev> -> <new>, confidence <prev> -> <new>`

## Quality Delta
- `No prior comparable run.`
- or include the useful rows from `bash <skill-dir>/trend.sh compare '<prev_json>' '<current_json>'`, preserving its `threshold crossing`, `within bucket`, `newly measured`, and `lost evidence` labels.
- In diff mode, also call out comparable-file diff-vs-base deltas emitted by `diff_scan.sh`, such as `lizard_warning_delta`, `lizard_max_ccn_delta`, and `largest_file_lines_delta`. Negative deltas for these signals are improvements. If `diff_current_only_file_count` or `diff_base_only_file_count` is nonzero, explicitly state that only `diff_comparable_file_count` files were used for before/after deltas.

---

## Evidence

### Mechanical
| Signal | Value | Tool | Scoring criterion |
| --- | --- | --- | --- |

### Judged Findings
- **[Domain.N] Criterion - <Low/Medium/High -> +N>**: one-sentence justification citing specific paths and the ISO sub-characteristic.

### Missing
- `<signal>` - `<tool>` not installed, blocked, timed out, or not applicable.

---

## Top Risks
1. <risk> - <impact> - <specific path/evidence>

## Divergent Paths
| Candidate | Evidence | Disposition | Risk / Next Step |
| --- | --- | --- | --- |
| <workflow/contract> | <paths> | <justified/watch/rationalize> | <why it matters, or "None found"> |

## Fastest Improvements
1. <action> - <expected point gain> - <effort estimate>

## Roadmap To A Grade
| Phase | Target | Work | Exit Criteria | Expected Score Movement |
| --- | --- | --- | --- | --- |

## Strengths To Preserve
- <architecture/practice worth keeping>

## Work To Defer Or Avoid
- <tempting but low-evidence/churn-heavy change to avoid>

## Verification Notes
- <commands run and outcomes>
```

## Execution Rules

1. Establish the repo root with `git rev-parse --show-toplevel` when possible.
2. Check `git status --short` before editing. Do not revert unrelated user changes.
3. Read `standards.md` once per session.
4. Resolve mode and base ref from the user request.
5. Capture provenance with `git rev-parse --short HEAD` and `bash <skill-dir>/trend.sh slug`.
6. Read the previous entry for this mode with `bash <skill-dir>/trend.sh prev <slug> <mode>`.
7. Run project-wide signals from repo root: `bash <skill-dir>/grade.sh`.
8. In diff mode, create a temporary file with `git diff --name-only <base_ref>...HEAD`, stop if empty, run `bash <skill-dir>/diff_scan.sh <tmp-file> <base_ref>`, then remove the temporary file.
9. Parse all `SIGNAL: key=value` lines. In diff mode, diff-scoped signals override project-wide signals only for diff-scoped criteria.
10. Apply mechanical scoring exactly from the tables.
11. Apply judged scoring with direct file inspection and ISO-anchored justifications.
12. Run the divergent-path lens during Maintainability judgment and include a `Divergent Paths` section, even if it says "None found."
13. Check hard-fail gates and cap the grade if needed.
14. Build the v1 JSON history entry, then compare it with the previous entry using `bash <skill-dir>/trend.sh compare '<prev_json>' '<current_json>'` when `prev_json` exists. Use this output for `Quality Delta`; omit unchanged rows.
15. Append the v1 JSON history entry with `bash <skill-dir>/trend.sh append <slug> '<json>' <mode>`. If append fails, report that in the Trend section.
16. Write or update the report file, preserving useful local history/status notes.
17. If running inside a loop-check branch/worktree, include that branch/path and
    the report/history files changed in Verification Notes so the caller can
    clean up or convert the branch intentionally.

## Diff Mode

Grades only files changed between `HEAD` and the base ref.

| Criterion | Scope |
| --- | --- |
| Tests | project |
| Typecheck | project |
| Lint | diff |
| Coverage | project |
| Dependency vulnerabilities | project |
| Secrets | diff |
| Complexity | diff |
| Duplication | diff |
| Largest file | diff |
| Operational enablers | project |
| Heuristic evidence | diff |

All judged inspection in diff mode must be scoped to the changed files. A reliability issue in an untouched file is not relevant to a diff grade unless it is surfaced by project-wide tests/typecheck.

For divergent-path findings in diff mode, cite unchanged canonical paths only when needed to prove the changed file duplicates or forks them. Score and recommend only against the changed surface.

When a base ref is available, `diff_scan.sh` emits scope counts and comparable-file base/current deltas for changed-file complexity and largest-file size. Use `diff_comparable_file_count`, `diff_current_only_file_count`, and `diff_base_only_file_count` to state how much of the diff had true before/after comparability. Treat negative `lizard_warning_delta`, `lizard_avg_ccn_delta`, `lizard_max_ccn_delta`, and `largest_file_lines_delta` values as direct evidence of improvement only for comparable files, even when the absolute score bucket is unchanged. Treat positive values as regression evidence. If current-only or base-only files are present, report them as scope changes rather than improvement/regression deltas.

## Trend Tracking

Build a single-line v1 JSON entry after scoring:

```json
{"v":1,"date":"YYYY-MM-DD","commit":"<short-sha>","mode":"<full|diff>","base_ref":"<ref or null>","overall":N,"grade":"<A-F>","confidence":"<High|Medium|Low>","domains":{"correctness":N,"reliability":N,"maintainability":N,"security":N,"performance":N,"test_quality":N,"operational_readiness":N},"signals":{"tests":"<pass|fail|timeout|missing>","lint":"<pass|fail|timeout|missing>","typecheck":"<pass|fail|timeout|missing>","coverage":"<N|unknown>","security_high":"<N|unknown>","secrets":"<N|unknown>","secrets_tool":"<gitleaks|rg-fallback|none>","largest_file_lines":"<N|unknown>","lizard_warning_count":"<N|unknown>","lizard_avg_ccn":"<N|unknown>","lizard_max_ccn":"<N|unknown>","duplication_pct":"<N|unknown>","deploy_artifact_count":"<N|unknown>","health_endpoint_count":"<N|unknown>","observability_lib_present":"<0|1|unknown>","validation_lib_present":"<0|1|unknown>","suppression_count":"<N|unknown>","timeout_retry_count":"<N|unknown>","blocking_io_count":"<N|unknown>","logging_call_count":"<N|unknown>","test_file_count":"<N|unknown>","test_sleep_count":"<N|unknown>"}}
```

Append with `bash <skill-dir>/trend.sh append <slug> '<json>' <mode>`. Full-mode and diff-mode histories are separate. Populate the Trend section by diffing prior overall/domain values. Populate `Quality Delta` with `bash <skill-dir>/trend.sh compare '<prev_json>' '<current_json>'` plus diff-vs-base deltas when present.

## Recommendation Rules

Include recommendations only when they:

- fix or prevent a demonstrated defect,
- reduce security or operational risk,
- add a measurable guardrail,
- improve a contract boundary,
- preserve or improve diagnosability,
- or reduce future change cost in code already blocking work.
- converge duplicate active paths when evidence shows drift risk, confusing ownership, or repeated change cost.

Avoid churn-heavy recommendations:

- no framework rewrites by default,
- no service splits unless scale or ownership evidence demands it,
- no broad file-splitting campaigns unless oversized files are actively blocking work,
- no broad convergence campaign without naming the workflow, canonical path, retirement target, and verification gate,
- no "increase coverage" recommendation without naming the specific risk the test should cover.

## Final Response

Keep the final response concise:

- Give the report file path.
- List overall score, grade, confidence, and domain scores.
- Summarize hard-fail blockers and top P0/P1-equivalent improvements.
- List verification commands run.
- Mention anything important that was not run or remained unknown.
