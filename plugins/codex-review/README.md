# codex-review

Codex code review closeout helper for local patches, PR branches, and parallel verification.

Ships one skill:

- **`/codex-review:codex-review`** - run Codex review as an advisory closeout check and verify the result before acting on findings

## Install

```
/plugin marketplace add nekoguntai/skills
/plugin install codex-review@nekoguntai-skills
/reload-plugins
```

Then in any repo:

```
/codex-review:codex-review
```

## What it covers

- Choosing the right review target for local patches versus branch/PR work
- Guardrails for treating `codex review` output as advisory
- Branch review by default on non-main branches, even with dirty local task notes
- Optional parallel focused tests during review
- A bundled `scripts/codex-review` helper for repeatable closeout checks

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
