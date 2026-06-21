# feature-validation-loop

End-to-end product behavior validation loop for application repositories. The
skill discovers code-derived user-facing features, maintains one canonical CSV
ledger, generates test scenarios, records defects, fixes verified functional or
UX issues, retests, and publishes Prismatic Thread summaries when configured.

Ships one skill:

- **`$feature-validation-loop`** / **`/feature-validation-loop:feature-validation-loop`** - run a bounded feature validation pass with ledger and artifact generation

## Codex Use

This plugin includes Codex metadata at `.codex-plugin/plugin.json`. The skill
can also be installed as a local skill by copying or syncing the full
`skills/feature-validation-loop/` directory to
`$CODEX_HOME/skills/feature-validation-loop/`, including bundled scripts and
references.

The current local install path is:

```text
~/.codex/skills/feature-validation-loop/SKILL.md
```

In any Codex session:

```text
$feature-validation-loop
```

## Legacy Marketplace Install

```text
/plugin marketplace add nekoguntai/skills
/plugin install feature-validation-loop@nekoguntai-skills
/reload-plugins
```

Then in any compatible plugin session:

```text
/feature-validation-loop:feature-validation-loop
```

## What it covers

- Code-derived feature discovery across UI, API, CLI, config, jobs, and workflows
- One canonical CSV ledger under `docs/feature-validation/`
- Deterministic standalone HTML report generation
- Prismatic Thread Markdown and optional sanitized HTML artifacts
- Bounded execution, remediation, and regression loop with confidence/blind-spot reporting

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
