# rationalize

Divergent-path analysis and convergence planning with fresh repo-context checks for repositories with duplicated workflows, contracts, APIs, schemas, services, UI paths, tests, or legacy/current code paths.

Ships one skill:

- **`/rationalize:rationalize`** - identify divergent paths, classify what should stay separate, and produce a sequenced convergence plan

## Install

```
/plugin marketplace add nekoguntai/skills
/plugin install rationalize@nekoguntai-skills
/reload-plugins
```

Then in any repo:

```
/rationalize:rationalize
```

## What it covers

- Duplicate contract and schema inventory
- Fresh repo-context checks before decisions and plan writes
- Parallel route, service, hook, client, worker, or command-handler comparison
- Legacy/current path and compatibility-shim review
- Canonical path decisions with compatibility notes
- Phased convergence, removal, or watch plans with verification gates
- Follow-up planning from `/grade:grade` divergent-path findings

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
