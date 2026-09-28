# Visual consistency audit rubric

Use this rubric to organize evidence and severity. Score only surfaces actually inspected.

## Evidence standard

| Confidence | Required evidence |
| --- | --- |
| High | Reproducible rendered behavior plus confirmed source cause/owner and verified affected scope, or an executable accessibility failure with a bounded owner |
| Medium | Rendered confirmation exists, but source cause, ownership, or blast radius remains unverified; alternatively, repeated source divergence has only one rendered sample |
| Low | Selector/value difference without rendered context; keep as a lead |

Do not promote low-confidence leads into the prioritized fix list.

## Audit domains

### Semantics and role

- Equivalent roles use equivalent primitives and state vocabulary.
- Navigation (`tablist`/links) is visually distinct from preference choices (`aria-pressed`).
- Buttons and button-like links with the same action role have parity.
- Specialized selectors have a documented semantic reason to differ.

### Navigation continuity and wayfinding

- Child, drill-down, and interrupting workflow pages expose enough in-product context to identify both the current location and its parent or origin.
- Equivalent journeys use consistent breadcrumb, back/return, close/cancel, local-tab, and global-navigation roles; placement and wording reflect semantic differences rather than route-by-route invention.
- A contextual return reaches the promised parent or origin and preserves meaningful record, filter, search, pagination, or workflow state when the product contract requires it.
- Direct links, reloads, new tabs, and external entry have a deterministic embedded fallback; browser history is not the only usable return mechanism for a page that needs one.
- Global navigation to a broad section is not counted as equivalent to returning to an originating record or filtered list unless it restores the same task context.
- Redundant navigation is avoided: do not add a back control when an equally discoverable breadcrumb, parent link, or workflow close/cancel action already provides the same semantics.

### State grammar

- Default, hover, focus, active, selected/pressed, disabled, loading, invalid, and destructive states remain distinguishable.
- Selection does not borrow status/unread motifs.
- Focus is not used as a resting or selected decoration.
- One state does not accumulate fill, gradient, border, dot, rail, shadow, and glow without a documented reason.

### Theme and luminance

- Dark-mode ordinary controls remain subordinate to content and primary actions.
- Semantic roles—not HTML element types—own emphasis.
- Raw white/black literals are ownership and theme-behavior leads, not defects by themselves. Judge their rendered hierarchy, contrast, role, and intentional use; coherent high-contrast systems may use pure white or black broadly.
- Disabled treatments remain recognizable and readable in both themes.

### Geometry and typography

- Equivalent control families converge on height, radius, padding, border, elevation, icon size, and label rhythm.
- Density differences map to explicit compact/default/spacious variants.
- Long labels, descriptions, counters, and translations do not break hierarchy.
- Repeated literals are evidence for shared ownership, not an automatic tokenization mandate.

### Responsive behavior

- Navigation preserves reading order and selected-panel association.
- Horizontal overflow has an affordance and scrolls the selected item into view.
- Wrapping is reserved for independent choices when appropriate.
- Hit targets, clipping, fixed positioning, drawers, and modals work at narrow widths and zoom.
- Location and return cues remain visible, correctly ordered, and usable when global navigation collapses into a drawer or menu.

### Surface hierarchy

- Routine panels use restrained surface, boundary, and elevation.
- Nested cards are not added merely to compensate for weak spacing or rules.
- Dialogs/drawers communicate layering without overpowering their content.
- Analytical or expressive surfaces are not used as the baseline for operational UI.

### Accessibility

- Normal text contrast is at least 4.5:1 unless an applicable standard permits otherwise.
- Large text and essential non-text boundaries are at least 3:1.
- Focus indicators reach at least 3:1 against adjacent colors and remain visible.
- Semantics, keyboard order, URL state, disabled behavior, and reflow survive visual convergence.

## Severity

- **P0:** Blocks a critical workflow or makes state/action meaning dangerously ambiguous.
- **P1:** Widespread role/state inconsistency, broken navigation continuity across a frequent workflow family, dark-theme failure, or accessibility defect in a shared primitive.
- **P2:** Repeated divergence with material scanability, responsive, or maintenance cost.
- **P3:** Local polish issue with limited user or system impact.

Raise severity for shared primitives, frequent workflows, accessibility failures, and defects present in both component fixtures and product routes. Lower severity for isolated, deliberate metaphors and unproven source-only differences.

## Motif classification

Use a product-specific mapping, but begin with these hypotheses:

- rail: vertical location or row severity;
- dot: status, unread state, category, or plotted point;
- filled/tinted surface: selection or pressed choice;
- outline/ring: keyboard focus or validation focus;
- glow: analytical emphasis or rare attention moment.

Document exceptions. Do not force this mapping when the product already has a coherent alternative vocabulary.
