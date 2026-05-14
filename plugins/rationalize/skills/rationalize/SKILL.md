---
name: rationalize
description: Identify divergent implementation paths, choose or recommend canonical paths, and produce a convergence plan for duplicated workflows, contracts, APIs, schemas, services, UI paths, tests, or legacy/current code paths. Use when the user asks to rationalize, converge, consolidate, de-duplicate, retire old paths, compare divergent paths, or turn /grade divergence findings into an actionable cleanup plan.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# Rationalize

Use this skill to turn suspected divergence into decisions and a sequenced plan. The goal is not to eliminate every duplicate. The goal is to identify which paths are intentionally separate, which are safe to watch, and which should converge because they create drift risk or repeated change cost.

Do not stop at a chat-only summary unless the user explicitly says not to write files. In a repository, write or update `docs/plans/rationalization-plan.md`. If `docs/plans/` does not exist, create it. Preserve useful prior decisions and status notes when updating an existing plan.

## Scope

Use this for:

- duplicate public contracts: schemas, OpenAPI entries, shared types, event payloads, API responses;
- parallel workflow implementations: routes, services, hooks, clients, jobs, workers, command handlers;
- old/current naming or compatibility paths that may outlive their purpose;
- feature flags, fallback paths, provider adapters, or platform splits whose ownership is unclear;
- test suites that prove the same behavior through separate helpers or fixtures;
- follow-up planning from `/grade:grade` `Divergent Paths` findings.

Do not use this to replace `/grade:grade`. `/grade:grade` scores risk. `rationalize` decides what should converge and how.

## Output

Write `docs/plans/rationalization-plan.md` with this shape unless the user requests a different artifact:

```markdown
# Rationalization Plan

Date: YYYY-MM-DD
Owner: TBD
Status: Draft
Scope: <repo-wide | subsystem | diff | user-specified scope>

## Executive Summary
- <highest-value convergence decision>

## Divergence Inventory
| Area | Paths | Current Behavior | Evidence | Disposition |
| --- | --- | --- | --- | --- |
| <workflow/contract> | <files> | <same/different/unknown> | <tests, code refs, docs> | <keep separate/watch/converge/remove> |

## Canonical Path Decisions
| Area | Canonical Path | Paths To Retire Or Wrap | Compatibility Policy | Decision Needed |
| --- | --- | --- | --- | --- |

## Convergence Plan
| Phase | Work | Files / Owners | Verification | Exit Criteria |
| --- | --- | --- | --- | --- |

## Edge Cases
- <null/empty/boundary/error/backcompat/race/security cases>

## Deferred Or Rejected
- <why a tempting cleanup is not worth doing now>

## Verification Notes
- <commands run and outcomes>
```

## Workflow

1. Establish the repo root with `git rev-parse --show-toplevel` when possible.
2. Check `git status --short` before editing. Do not revert unrelated user changes.
3. Read relevant project instructions, existing plans, and recent `/grade:grade` reports if present.
4. Define the scope from the user's request. If the request is broad, inventory the top-level domains first and then focus on the highest-risk areas.
5. Search for candidate divergence with `rg` and native project structure. Start from names the user mentioned, then inspect adjacent routes, types, schemas, clients, tests, docs, and feature flags.
6. For each candidate, compare behavior, ownership boundary, callers, tests, compatibility requirements, and failure modes.
7. Classify each candidate:
   - `keep separate`: the split encodes a real boundary such as provider, platform, permission, latency, runtime, or compatibility.
   - `watch`: duplication exists, but tests, manifests, or narrow ownership make drift unlikely enough to defer.
   - `converge`: active paths can drift, have drifted, or make future work likely to land in the wrong place.
   - `remove`: an old path is dead or unsupported and should be deleted after verification.
8. Choose a canonical path only when evidence supports it. If a product or compatibility decision is required, record the decision point instead of guessing.
9. Sequence convergence in small phases. Prefer helpers, shared contracts, adapters, or generated sources only when they remove real drift risk.
10. Specify verification per phase: focused tests, typechecks, lint, contract tests, migration checks, screenshots, logs, or behavior diffs as appropriate.
11. Re-read the plan for unnecessary churn. Remove broad cleanup that lacks evidence.
12. Update the plan file and summarize the highest-priority decisions for the user.

## Search Hints

Prefer targeted searches over generic duplication claims:

- contract drift: `rg "type .*Response|interface .*Response|z\\.object|OpenAPI|schema|payload|event"`;
- route/client splits: `rg "fetch\\(|apiClient|router\\.|app\\.|Controller|handler|endpoint"`;
- compatibility paths: `rg "legacy|deprecated|compat|fallback|old|new|v1|v2|featureFlag|flag"`;
- duplicate domain values: `rg "<domain term>|enum|const .*\\[|as const|Union|Literal"`;
- test divergence: `rg "<workflow name>|describe\\(|it\\(|test\\(" tests src server shared`.

Use language-native structure when available. For TypeScript, compare exported types, schemas, API modules, route handlers, and tests. For Python, compare pydantic models, serializers, routers, services, and tests. For strongly typed backends, compare DTOs, interfaces, validation layers, and generated API specs.

## Decision Criteria

Favor convergence when:

- user-facing behavior or API contracts should be identical;
- one path already omits fields, validation, authorization, logging, retries, or tests present in another;
- engineers must remember to update multiple files for one product change;
- duplicate constants, enums, schemas, or request/response types cross a trust boundary;
- similar names hide materially different semantics.

Favor keeping paths separate when:

- the split protects a security, process, network, provider, or runtime boundary;
- different latency, availability, deployment, or resource constraints justify different implementations;
- compatibility with stored data or external clients requires an adapter;
- merging would create a larger abstraction than the duplication it removes.

## Implementation Mode

Default to analysis and planning. If the user explicitly asks to implement a convergence phase, make the smallest coherent change, update the plan status as work completes, and verify before calling it done.

For implementation:

- preserve public compatibility unless the plan explicitly retires it;
- add or update contract tests before deleting duplicate behavior;
- keep adapters at real system boundaries instead of hiding them behind broad shared helpers;
- remove dead paths only after proving they have no callers or after a migration gate passes;
- run touched-file complexity checks when logic changes are non-trivial.

## Final Response

Keep the final response concise:

- Give the plan file path.
- Summarize the top converge/remove/watch decisions.
- List verification commands run.
- Name any decisions that still need user or product input.
