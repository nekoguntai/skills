# Visual Consistency Loop

Audits application UIs for visual drift, accessibility defects, responsive inconsistencies, and broken navigation continuity, then fixes and delivers major findings and repeats until a fresh scoped audit finds no P0–P2 issues.

## Skill

- `$visual-consistency-loop` — run the complete audit, reviewed plan, implementation, PR/merge, CI, runtime verification, cleanup, and re-audit cycle without a default pass cap.
- Explicit audit-only, plan-only, and local implementation requests retain their narrower scope.

Renamed from `visual-consistency-audit`; use `visual-consistency-loop` for new invocations and plugin installs. Requires the shared loop helper from `pr-delivery` 1.3.1 or newer.
