# release

Repository-native release execution and release-infrastructure remediation. The
skill discovers a repository's actual versioning, changelog, gates, release
candidate flow, stable promotion path, install/upgrade checks, artifact surface,
and publication steps before cutting or repairing a release.

Ships one skill:

- **`$release`** / **`/release:release`** - cut the next patch release end to end, audit release readiness, or build missing release infrastructure

## Codex Use

This plugin includes Codex metadata at `.codex-plugin/plugin.json`. The skill
can also be installed as a local skill by copying or syncing
`skills/release/SKILL.md` to `$CODEX_HOME/skills/release/SKILL.md`.

The current local install path is:

```
~/.codex/skills/release/SKILL.md
```

In any Codex session:

```
$release
$release readiness
$release build missing release infrastructure
```

## Legacy Marketplace Install

```
/plugin marketplace add nekoguntai/skills
/plugin install release@nekoguntai-skills
/reload-plugins
```

Then in any compatible plugin session:

```
/release:release
/release:release readiness
/release:release build missing release infrastructure
```

## What it covers

- Release-surface discovery from local docs, scripts, workflows, and version files
- Blocking, conditional, and advisory gap reporting when release pieces are missing
- Follow-up plans for building missing release infrastructure
- Patch version selection, RC selection, local gate loops, and release prep commits
- Pre-release gates, stable promotion gates, install/upgrade smoke checks, and artifact verification
- Recovery rules for failed candidates and bad stable tags

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
