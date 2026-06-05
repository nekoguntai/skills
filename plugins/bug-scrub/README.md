# bug-scrub

Evidence-driven bug scrub for repositories and diffs. The skill focuses on
high-confidence correctness defects, not style issues or broad refactors.

Ships one skill:

- **`/bug-scrub:bug-scrub`** - inspect a repo or diff for likely real bugs,
  synthesize evidence, and produce a prioritized triage report

## Codex Use

This plugin includes Codex metadata at `.codex-plugin/plugin.json`. The skill
can also be installed as a local skill by copying or syncing
`skills/bug-scrub/SKILL.md` to `$CODEX_HOME/skills/bug-scrub/SKILL.md`.

The current local install path is:

```
~/.codex/skills/bug-scrub/SKILL.md
```

In any Codex session:

```
$bug-scrub
$bug-scrub --diff origin/main
$bug-scrub use subagents to bug scrub this large repo
```

## Legacy Marketplace Install

```
/plugin marketplace add nekoguntai/skills
/plugin install bug-scrub@nekoguntai-skills
/reload-plugins
```

Then in any compatible plugin session:

```
/bug-scrub:bug-scrub
/bug-scrub:bug-scrub --diff origin/main
/bug-scrub:bug-scrub large codebase, use subagents for analysis
```

## What it covers

- Trust boundaries, auth, tenant scope, and validation bugs
- Persistence, transactions, migrations, and data integrity bugs
- API contract, date/time, money, pagination, and schema drift bugs
- Async jobs, retries, workers, webhooks, and lifecycle races
- Frontend state, forms, navigation, and user-visible failure modes
- Test, fixture, CI, and isolation risks that can mask real defects

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
