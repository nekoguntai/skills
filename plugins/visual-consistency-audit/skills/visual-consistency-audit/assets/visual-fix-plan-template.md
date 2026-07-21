# Visual Consistency Remediation Plan

Status: Proposed

## Goal

## Accepted findings

Link each included finding to its rendered/source evidence and classification.

## Non-goals

## Assumptions and dependencies

## Phase 1 — Lock the contract

- [ ] Create or identify the representative fixture and routes.
- [ ] Capture baseline themes, viewports, roles, and states.
- [ ] Add characterization and accessibility assertions.

Acceptance:

Verification:

Backout boundary:

## Phase 2 — [Accepted finding family]

Include this phase only for a family supported by accepted findings, such as actions, navigation continuity, navigation styling, forms, tables, typography, surfaces, theme behavior, responsive layout, or semantic motifs.

- [ ] Define the semantic roles and affected shared owners.
- [ ] Correct the shared owner before feature-local callers.
- [ ] Migrate ordinary callers while preserving behavior and accessibility.
- [ ] Verify deliberate specialized exceptions.
- [ ] For navigation work, verify origin-to-destination behavior, direct entry, embedded return/escape paths, responsive placement, and required context preservation.

Acceptance:

Verification:

Backout boundary:

## Phase 3 — [Next accepted finding family, if needed]

Duplicate the finding-family phase only when evidence supports another independently reviewable family. Record dependencies on earlier phases.

Acceptance:

Verification:

Backout boundary:

## Final phase — Cleanup and enforcement

- [ ] Remove superseded aliases and local state recipes.
- [ ] Add precise drift gates with negative tests and narrow allowlists where justified.
- [ ] Re-run the full rendered matrix and update deliberate exceptions.

Acceptance:

Verification:

Backout boundary:

## Delivery slices

List reviewable changes, dependencies, and whether implementation/delivery/merge is authorized.

## Final verification gates

- [ ] Focused component tests
- [ ] Style/token checks
- [ ] Lint and typecheck
- [ ] Required coverage/build checks
- [ ] Light/dark desktop/mobile visual contract
- [ ] Representative route matrix
- [ ] Adversarial review
- [ ] Exact PR and target-branch CI when applicable
- [ ] Runtime commit, health, and readiness when applicable
