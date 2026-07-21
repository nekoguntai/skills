---
name: visual-consistency-audit
description: Evidence-driven visual and navigational consistency auditing and remediation planning for application UIs. Use when Codex is asked to inspect visual drift; compare inconsistent tabs, buttons, forms, or surfaces; audit embedded navigation, breadcrumbs, back/return paths, or cross-page workflow continuity; investigate dark-mode or responsive inconsistencies; rationalize selection and status motifs; assess design-system adherence; create a visual inventory or fix list; define a semantic visual contract; add visual regression gates; or implement and verify a visual-consistency plan. Supports analysis-only reports, checkable plans, and explicitly authorized implementation; it does not treat every visual or navigational difference as a defect.
---

# Visual Consistency Audit

Build a rendered, source-backed account of visual and navigational drift, decide which differences communicate real meaning, and turn verified findings into a semantic contract and executable fix plan.

## Choose the operating mode

- **Audit/report:** Inspect and write findings. Do not modify product code.
- **Plan:** Produce or update a checkable remediation plan. Do not implement it.
- **Implement:** Change code only when the user explicitly asks for changes.
- **Deliver:** Commit, open, or merge a PR only when separately authorized. Use an available frontend or PR-delivery skill instead of duplicating its forge workflow.

If the request is ambiguous, default to audit/report. Preserve unrelated dirty work in every mode.

## Load repository context

1. Read repository instructions and applicable design guidance completely.
2. Inspect active UI plans, theme tokens, global styles, shared primitives, route structure, navigation shells, contextual navigation owners, and test-isolation rules.
3. Identify the framework and existing guarded commands before running the app or browser tests.
4. Record repository HEAD and dirty state.
5. If using a running app, compare its build identity with repository HEAD. Treat screenshots from a stale or unknown build as non-authoritative.

Read [references/audit-rubric.md](references/audit-rubric.md) before scoring or classifying findings. Read [references/rendered-verification.md](references/rendered-verification.md) before browser capture or computed-style measurement. Read [references/implementation-playbook.md](references/implementation-playbook.md) only for planning or implementation.

## Establish scope and evidence

State the audited scope and explicit blind spots. Distinguish visual-control consistency from navigation-continuity coverage. Neither one is automatically an app-wide typography, form, table, modal, or empty-state audit.

Gather two independent evidence layers:

1. **Source inventory:** semantics, variants, selector ownership, tokens, local overrides, hard-coded colors, responsive rules, route relationships, navigation ownership, destination construction, state/return parameters, and existing tests.
2. **Rendered inventory:** representative routes and route transitions, themes, viewports, states, computed styles, geometry, overflow, screenshots, and the navigation available after each transition.

Run the bundled source helper when the repository uses text-based frontend code:

```bash
skill_dir=/path/to/visual-consistency-audit
repo_root=$(pwd)
inventory_output=$(mktemp)
node "$skill_dir/scripts/inventory-ui-controls.mjs" "$repo_root" --output "$inventory_output"
jq -e . "$inventory_output" >/dev/null
jq '{repository, selection, summary}' "$inventory_output"
```

Keep the inventory file through source inspection. Copy it to a repository-approved artifact location when it is a deliverable; otherwise remove the temporary file only after the analysis is complete.

Treat helper results as leads, not defects. Inspect every accepted finding in its owner code and rendered context.

## Build the rendered matrix

Choose a compact matrix that crosses:

- light and dark themes;
- desktop and narrow mobile widths;
- global, page-level, nested, and contextual navigation;
- representative parent-to-child and sibling workflow transitions, including direct entry at the destination;
- ordinary and specialized selectors;
- buttons and button-like links;
- panels, dialogs, drawers, tables, forms, and analytical surfaces where relevant;
- resting, hover, focus-visible, active, selected/pressed, disabled, loading, empty, validation, and error states as applicable;
- one item, many items, long labels, counters, disabled items, and overflow boundaries.

Use an existing component gallery, Storybook, or test route when available. Otherwise prefer representative product routes over creating product code during an audit-only run.

For each representative transition, record the origin, triggering control, destination, user-visible location context, embedded return/escape options, browser-history dependency, state preservation, direct-entry behavior, and whether sibling destinations follow the same pattern. A sidebar link to a broad section is not automatically equivalent to a contextual return to the originating record or filtered list.

Capture exact route, transition, theme, viewport, state, commit, selector owner, computed values, and screenshot path in the inventory. Do not infer rendered consistency or navigation continuity from selectors or route structure alone.

## Measure before judging

Measure the properties that matter to the reported problem:

- foreground/background contrast and adjacent-color focus contrast;
- relative luminance and dark-surface luminance delta;
- control height, padding, radius, border, and elevation;
- typography, icon size, and label wrapping;
- selected, focus, status, location, severity, and analytical motifs;
- scroll, wrap, clipping, hit target, and responsive layout behavior;
- orientation and wayfinding cues such as page title, parent/entity label, breadcrumb, selected global location, and step or tab context;
- return-path discoverability, label and icon consistency, destination correctness, keyboard/focus behavior, history independence, and preservation of relevant query/filter/record context.

Use the product's documented thresholds. If none exist, present WCAG contrast requirements as accessibility requirements and any luminance/geometry bounds as proposed guardrails that require product validation.

## Classify each difference

Assign exactly one primary classification:

- **Intentional hierarchy:** the difference communicates emphasis or nesting.
- **Specialized metaphor:** distinct geometry communicates a real domain interaction.
- **Accidental divergence:** equivalent roles have unrelated visual recipes.
- **Navigation continuity defect:** a journey lacks adequate in-product orientation, escape, or return semantics, or equivalent journeys behave inconsistently.
- **Accessibility defect:** contrast, focus, semantics, target size, or reflow fails.
- **Unproven:** evidence is insufficient; list the missing observation.

Do not label a difference inconsistent merely because values differ. Ask whether it communicates a difference in role, hierarchy, state, or context. Prefer convergence only when it does not.

Do not require a back button on every destination. Judge whether the page is a true child, drill-down, or interrupting workflow; whether users need to resume an origin-specific context; whether a stable parent destination exists; and whether another visible, consistent in-product mechanism already provides the same orientation and return semantics. Treat browser history as a convenience, not the sole evidence of an embedded return path, because direct links, reloads, new tabs, and external entry may have no usable prior page.

## Define the semantic visual contract

Before proposing selector edits, map each role to its visual grammar:

- default, hover, focus, active, selected/pressed, disabled, and destructive states;
- theme behavior and allowed luminance hierarchy;
- responsive overflow/wrapping behavior;
- motif ownership for surface, border, rail, dot, ring, and glow;
- ordinary shared variants and named specialized exceptions;
- component ownership and any narrowly documented escape hatch;
- navigation roles for global location, local section, parent context, breadcrumb, back/return, close/cancel, previous/next, and cross-entity links;
- destination and state-preservation rules for contextual return controls, including direct-entry fallback behavior.

Use one dominant cue per state. Coordinated surface, border, and text changes may form one cue; do not stack unrelated selection, status, location, and focus motifs.

## Produce the audit artifacts

Honor repository output-location rules. For long deliverables, copy and fill:

- [assets/visual-consistency-report-template.md](assets/visual-consistency-report-template.md)
- [assets/visual-fix-plan-template.md](assets/visual-fix-plan-template.md)

Produce `visual-inventory.json` when rendered measurements are available. Use stable identifiers and this minimum record shape:

```json
{
  "component": "shared-tabs",
  "role": "page-tab",
  "route": "/settings",
  "journey": { "origin": "/clients", "trigger": "Open client", "returnOptions": ["breadcrumb"] },
  "theme": "dark",
  "viewport": { "width": 390, "height": 844 },
  "state": "selected",
  "computed": { "color": "...", "background": "...", "contrast": 0, "luminance": 0 },
  "geometry": { "width": 0, "height": 0, "radius": "...", "overflow": "..." },
  "owner": "path/to/component",
  "screenshot": "path/to/image"
}
```

Every report finding must include severity, affected roles/routes or journeys, source owner, rendered evidence, why the difference is accidental or harmful, recommendation, confidence, and verification target. For navigation findings, include the origin/destination pair, visible location cues, available return paths, direct-entry behavior, and context-preservation result. Separate observed facts from proposed rules.

## Design the remediation plan

Order work by dependency and reviewability:

1. Lock the approved contract with a fixture and characterization checks.
2. Group accepted findings into product-specific families such as actions, navigation continuity, navigation styling, choices, forms, tables, typography, surfaces, responsive layout, or semantic motifs.
3. For each accepted family, correct the shared owner before migrating ordinary callers while preserving behavior and accessibility.
4. Review interactions between the migrated families, responsive behavior, and specialized exceptions.
5. Remove superseded aliases and add narrowly scoped static drift gates where evidence supports them.

Keep behavior-preserving migrations separate from broad redesigns. Each phase must list concrete files or owners, acceptance criteria, focused and broad verification, non-goals, backout boundaries, and before/after evidence.

## Implement safely

When implementation is authorized:

1. Establish a baseline from the approved fixture and representative routes.
2. Change the shared owner before migrating feature-local aliases.
3. Preserve semantics, keyboard behavior, URL state, focus, panel relationships, destination correctness, and meaningful origin context.
4. Keep specialized variants only when their distinction communicates meaning.
5. Add meaningful component and browser tests for the states changed.
6. Add static gates only for precise, high-confidence anti-patterns with positive and negative tests plus a narrow exception allowlist.
7. Compare the final matrix with baseline evidence and update deliberate exceptions.
8. Follow repository verification and delivery instructions; never weaken required checks.

## Run the adversarial gate

Before finalizing an audit, plan, or implementation, ask a fresh reviewer to challenge:

- findings based only on source code;
- intentional differences misclassified as drift;
- missed dark, mobile, focus, disabled, empty, error, or overflow states;
- missed parent/child journeys, direct destination entry, dead ends, inconsistent back/breadcrumb placement, or return controls that lose record/filter context;
- recommendations that add redundant back controls where an equivalent embedded navigation path already exists;
- recommendations that erase useful hierarchy or metaphor;
- thresholds presented as standards without product approval;
- incomplete exception allowlists or static-check false negatives;
- plan phases lacking acceptance or backout criteria.

Resolve verified findings and rerun affected checks. If no independent reviewer is available, perform the same checklist explicitly and disclose that limitation.

## Close out

Report the audited scope, highest-priority inconsistencies, artifact paths, rendered/automated verification, deliberate exceptions, unverified areas, and—only if delivery was authorized—PR and runtime results. Never claim an app-wide audit when the captured matrix covered only a subsystem.
