# scaffold

Portable repository scaffolding for new and existing projects. The skill builds
or repairs CI around a local 100% coverage gate, then enforces PR-only protected
branch merges for GitHub or Forgejo.

Ships one skill:

- **`$scaffold` / `/scaffold:scaffold`** - inspect a repository, add or repair
  coverage, CI, quality/security gates, and branch protection until the pipeline
  is green and merge-blocking

## Codex Use

This plugin includes Codex metadata at `.codex-plugin/plugin.json`. The skill
can also be installed as a local skill by copying or syncing
`skills/scaffold/SKILL.md` and its bundled `scripts/` and `references/` folders
to `$CODEX_HOME/skills/scaffold/`.

The current local install path is:

```
~/.codex/skills/scaffold/SKILL.md
```

In any Codex session:

```
$scaffold
$scaffold standardize this repo's CI
$scaffold add 100% coverage and protected PR-only merges
```

## Legacy Marketplace Use

After installing this plugin from its configured marketplace, use:

```
/scaffold:scaffold
/scaffold:scaffold standardize this repo's CI
/scaffold:scaffold add 100% coverage and protected PR-only merges
```

## What it covers

- GitHub and Forgejo workflow scaffolding
- 100% line, branch, function, and statement coverage gates
- CI convergence loops that keep fixing tests and config until green
- Lint, typecheck, build, dependency audit, secret scan, and relevant smoke gates
- Branch protection/rulesets that block direct pushes and require PR checks
- Context-window discipline through a small inspector and focused references

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
