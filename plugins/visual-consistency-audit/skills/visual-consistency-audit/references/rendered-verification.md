# Rendered verification

## Establish authority

Before capture, record repository HEAD, runtime build identity, theme, viewport, seed/account state, browser, and route. Rebuild or use an isolated test server when runtime identity does not match HEAD. Never present stale screenshots as current evidence.

## Select the matrix

Cover the smallest route and journey set that exercises every shared owner and meaningful exception. Include at least one dense operational page, one nested navigation surface, one parent-to-child or drill-down transition, one direct entry to that destination, one form/action cluster, and one layered surface when those exist.

Recommended viewports:

- desktop: the product's common working width, often 1280px or 1440px;
- mobile: a narrow width around 390px;
- add an intermediate width only when wrapping or layout mode changes there.

## Capture state

Prefer deterministic data and disable animation only through the repository's accepted visual-test setup. Capture resting, hover, focus-visible, active, selected/pressed, disabled, and any reported failure state. Add long labels, counters, empty/error/loading states, and overflow boundaries when relevant.

Use screenshots for comparison and computed styles for claims. Screenshots alone cannot prove contrast or exact luminance.

For each audited journey, exercise the navigation rather than only loading both URLs. Record the origin URL and visible state, trigger, destination URL, location cues, all embedded return/escape controls, the result of the intended return action, and retained or lost context. Repeat the destination as a direct load or new-tab entry to distinguish a durable parent path from a history-only back action. At narrow widths, verify that collapsed global navigation does not hide the only embedded location or return cue.

## Compute color evidence

Convert sRGB channels to linear values:

```text
c = channel / 255
linear = c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ^ 2.4
L = 0.2126R + 0.7152G + 0.0722B
contrast = (lighter L + 0.05) / (darker L + 0.05)
```

Resolve alpha compositing and inherited backgrounds before measuring. Compare focus indicators with both adjacent colors when they straddle a control and page surface.

Treat a dark-surface luminance delta as a product guardrail, not a WCAG rule. Derive and document any threshold from approved examples, then change documentation and tests together.

## Record geometry

Record bounding box, padding, border width, radius, font metrics, box shadow, overflow mode, scroll position, wrapping, and clipped content where material. Compare roles at the same density level.

## Avoid false evidence

- Do not compare screenshots from different data states.
- Do not infer hover/focus from class names.
- Do not treat antialiased screenshot pixels as computed colors.
- Do not declare consistency from a component fixture alone; verify representative routes.
- Do not declare a product-wide defect from one route without confirming shared ownership.
- Do not approve a source migration without checking semantics and keyboard behavior.
- Do not infer a usable return path merely because a sidebar contains the parent section or the browser has a Back button.
- Do not flag every child page without a back button; first test breadcrumbs, parent links, close/cancel actions, direct-entry behavior, and the task's expected return semantics.

## Suggested automation gates

- component tests for variant ownership, semantics, keyboard behavior, and disabled state;
- browser assertions for computed contrast, luminance, focus, overflow, and button/link parity;
- browser journey assertions for destination correctness, visible location context, contextual return behavior, direct-entry fallback, and preservation of relevant origin state;
- light/dark desktop/mobile screenshots for shared variants and deliberate exceptions;
- static gates for raw duplicate primitives or forbidden token coupling, with negative tests;
- representative route captures to detect cascade and layout interactions absent from fixtures.
