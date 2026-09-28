# bug-scrub-loop

Autonomous, resumable bug remediation loop. It runs a measured bug scrub,
creates and recursively reviews an executable plan for confirmed P0-P2
findings, implements and merges that plan through `implement-merge`, and
rescrubs the original scope until a fresh complete pass is clean.

Ships one skill:

- **`$bug-scrub-loop`** / **`/bug-scrub-loop:bug-scrub-loop`** — scrub, plan,
  merge fixes, and repeat until no confirmed P0-P2 bugs remain

## Codex Use

This plugin includes Codex metadata at `.codex-plugin/plugin.json`. The skill
can also be installed as a local skill by copying or syncing
`skills/bug-scrub-loop/` to `$CODEX_HOME/skills/bug-scrub-loop/`.

```text
$bug-scrub-loop
$bug-scrub-loop --dry-run
$bug-scrub-loop --resume <run-id>
```

## Legacy Marketplace Install

```text
/plugin marketplace add nekoguntai/skills
/plugin install bug-scrub-loop@nekoguntai-skills
/reload-plugins
```

## Cleanup and validation

Every new run captures branch/worktree baselines and blocks the next iteration
or completion until live local and remote inventories match. Schema 1 records
remain readable; missing historical baselines are never fabricated on resume.
See the skill's [cleanup contract](skills/bug-scrub-loop/references/cleanup-contract.md).

Run the temporary-repository regression suite with:

```bash
python3 -m unittest discover -s plugins/bug-scrub-loop/skills/bug-scrub-loop/scripts -p 'test_*.py' -v
```

## License

MIT — see the repo-level [LICENSE](../../LICENSE).
