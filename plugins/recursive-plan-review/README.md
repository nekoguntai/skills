# recursive-plan-review

Iterative plan-file critique and refinement. The skill reviews one concrete
plan file, applies evidence-backed improvements, and repeats until no verified
actionable comments remain.

Ships one skill:

- **`$recursive-plan-review`** / **`/recursive-plan-review:recursive-plan-review`** - review and refine a plan file until it has no actionable comments left

## Codex Use

This plugin includes Codex metadata at `.codex-plugin/plugin.json`. The skill
can also be installed as a local skill by copying or syncing
`skills/recursive-plan-review/SKILL.md` to
`$CODEX_HOME/skills/recursive-plan-review/SKILL.md`.

The current local install path is:

```
~/.codex/skills/recursive-plan-review/SKILL.md
```

In any Codex session:

```
$recursive-plan-review <path-to-plan>
```

## Legacy Marketplace Install

```
/plugin marketplace add nekoguntai/skills
/plugin install recursive-plan-review@nekoguntai-skills
/reload-plugins
```

Then in any compatible plugin session:

```
/recursive-plan-review:recursive-plan-review <path-to-plan>
```

## What it covers

- Whole-plan review of goals, assumptions, phases, dependencies, verification, and completion criteria
- Source-backed checks for stale facts, unsafe sequencing, vague acceptance criteria, and hidden migration or rollback needs
- Minimal direct edits to the plan file for accepted comments
- Explicit rejection of speculative, subjective, duplicate, or outside-scope comments
- Repeated passes until the final plan has no verified actionable comments left

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
