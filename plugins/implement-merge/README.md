# implement-merge

Plan-to-merge execution loop for implementation plans. The skill clears stale
context, selects the newest plan, tracks it as an explicit goal, implements the
plan in bounded phases, delivers each phase with `pr-delivery`, and rebuilds
already-running local containers after the full plan has landed.

Ships one skill:

- **`$implement-merge`** / **`/implement-merge:implement-merge`** - implement the newest plan through merged PR phases

## Codex Use

This plugin includes Codex metadata at `.codex-plugin/plugin.json`. The skill
can also be installed as a local skill by copying or syncing
`skills/implement-merge/SKILL.md` to
`$CODEX_HOME/skills/implement-merge/SKILL.md`.

The current local install path is:

```
~/.codex/skills/implement-merge/SKILL.md
```

In any Codex session:

```
$implement-merge
```

## Legacy Marketplace Install

```
/plugin marketplace add nekoguntai/skills
/plugin install implement-merge@nekoguntai-skills
/reload-plugins
```

Then in any compatible plugin session:

```
/implement-merge:implement-merge
```

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
