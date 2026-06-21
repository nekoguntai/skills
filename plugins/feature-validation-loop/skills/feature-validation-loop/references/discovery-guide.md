# Feature Discovery Guide

Use this guide before creating or updating ledger rows.

## Scope

Discover implemented, user-facing behavior from current repository evidence:

- web routes, screens, layouts, modals, panels, and navigation;
- forms, validation, loading, empty, success, and error states;
- API endpoints, handlers, schemas, client calls, and auth checks;
- CLI commands, flags, config files, environment-driven behavior, and scripts;
- jobs, queues, scheduled work, import/export, webhooks, and integrations;
- permission, role, ownership, tenancy, and visibility boundaries;
- persistence behavior, generated artifacts, file uploads, and data flows.

Do not invent product intent. Expected behavior must come from code, tests,
repo docs, or observed runtime behavior.

## Discovery Order

1. Read repo instructions and project plans.
2. Inspect package/workspace files to identify apps and entry points.
3. Map routes, API handlers, CLI binaries, background workers, and config
   surfaces.
4. Search tests for behavior names and expected outcomes.
5. Inspect runtime UI only when it materially clarifies behavior.
6. Create or update ledger rows with source paths for every discovered surface.

## Feature Boundary Heuristics

Create one feature row when a user can describe a distinct outcome:

- "View project validation status"
- "Submit an artifact file"
- "Import a repository"
- "Run a CLI collector scan"

Split rows when behavior has different permissions, data lifecycles, or failure
modes. Combine rows when a surface only has minor display variants.

## Evidence Requirements

Every row should include:

- at least one source path;
- a user story derived from implemented behavior;
- expected behavior with concrete system responses;
- edge cases and validation rules when visible in code;
- dependencies such as stores, APIs, env vars, jobs, or external services;
- assumptions for uncertainty.

Use `Confidence: low` for inferred or partially inspected behavior. Use
`blocked` status when credentials, services, test data, or runtime setup prevent
execution.

## Test Scenario Coverage

For each feature, capture compact scenarios covering the applicable cases:

- happy path;
- error path;
- boundary and invalid input;
- permission/security;
- persistence/data integrity;
- accessibility and keyboard behavior for UI;
- mobile/responsive behavior for UI;
- performance or large-data considerations.

Prefer executable checks when the repo already has a test harness. Manual
verification is acceptable when clearly recorded.
