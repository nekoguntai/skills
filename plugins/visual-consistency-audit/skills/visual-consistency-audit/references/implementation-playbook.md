# Implementation playbook

## Universal bookends

Begin every remediation with contract characterization and finish with cleanup plus full verification. Derive the middle phases from accepted findings; do not impose a tab/button/motif sequence on products whose drift lies in typography, forms, tables, layout, or another family.

### Characterize and lock the contract

Create or identify a representative fixture. Capture current behavior and add tests for approved contrast, luminance, focus, selection grammar, responsive behavior, and deliberate exceptions. Expected failures may characterize known defects temporarily, but each must name the remediation phase that removes it.

### Clean up and enforce

After migrations, remove superseded selectors, aliases, local workarounds, and caller-owned state recipes. Add precise static gates only for repeated, high-confidence drift patterns. Keep an explicit, narrow exception allowlist. Rerun the complete rendered matrix.

## Derive finding-family phases

Create one or more middle phases from the accepted report findings. Common families include:

- action hierarchy and button/link parity;
- navigation, pressed choices, and selection grammar;
- navigation continuity, breadcrumbs, contextual return paths, and cross-page wayfinding;
- fields, validation, and form density;
- tables, lists, empty/loading/error states, and row interaction;
- typography, spacing, iconography, geometry, or elevation;
- theme tokens, contrast, and luminance hierarchy;
- responsive layout, wrapping, overflow, and layered surfaces;
- status, location, severity, focus, and analytical motifs.

For each chosen family:

1. Name the accepted findings and affected shared owners.
2. Define semantic roles and theme/responsive behavior.
3. Change the shared owner before feature-local callers.
4. Preserve semantics, keyboard behavior, URL state, focus, workflow behavior, destination correctness, and meaningful origin context.
5. Retain specialized variants only when their distinction communicates meaning.
6. Add focused component and rendered verification.
7. State dependencies, non-goals, acceptance, and backout boundaries.

Do not create phases for finding families absent from the evidence.

## Slice design

Prefer one coherent family per reviewable change. Keep visual correction separate from broad architecture work. Every slice should contain:

- baseline and after evidence in both themes and relevant viewports;
- shared-owner changes before caller migrations;
- behavioral and accessibility non-regression tests;
- focused verification followed by blast-radius checks;
- acceptance criteria and a safe backout boundary;
- an adversarial review before delivery.

## Static gate design

A useful static gate:

- matches a narrow semantic anti-pattern, not a vague class substring;
- scans production code while classifying or deliberately excluding tests, generated sources, stories, and docs;
- identifies file, line, syntax category, and reason;
- has an exact allowlist for justified owners/exceptions;
- rejects additional violations inside an allowlisted file;
- recognizes common syntax variants;
- has positive tests for accepted owners and negative tests for every failure class;
- runs in an existing static CI command.

Do not replace rendered verification with a static gate.

## Verification ladder

Use repository commands, guarded test entry points, and the smallest convincing sequence:

1. focused component/static tests;
2. token/style checks;
3. lint and typecheck;
4. unit coverage when required;
5. production build;
6. focused visual contract suite;
7. broader browser/route matrix;
8. diff checks and adversarial review;
9. exact PR and target-branch CI when delivery is authorized;
10. runtime commit, health, and readiness verification when redeploy is authorized.

Diagnose CI failures before retriggering. A newly published dependency advisory, coverage regression, type error, browser failure, and runner outage require different responses.
