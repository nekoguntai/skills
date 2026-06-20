# frontend-pr-loop

Autonomous frontend/UI improvement loop for application repositories, with
stale-context resets at startup and between PR passes.

Ships one skill:

- **`/frontend-pr-loop:frontend-pr-loop`** - inspect the frontend, choose a bounded improvement, implement it, verify it, deliver it through a merged PR, verify target-branch post-merge CI, rebuild running app containers, and recheck from refreshed target-branch state

## Install

```
/plugin marketplace add nekoguntai/skills
/plugin install frontend-pr-loop@nekoguntai-skills
/reload-plugins
```

Then in any repo:

```
/frontend-pr-loop:frontend-pr-loop
```

## What it covers

- Frontend surface inspection and bounded improvement selection
- Stale-context reset at startup and between PR passes
- Read-only recommendation mode when explicitly requested
- Implementation with focused verification
- PR creation, CI/review monitoring, safe merge, ancestry verification, and target-branch post-merge CI verification through `/pr-delivery:pr-delivery`
- Post-merge container rebuild for already-running app services in autonomous loop mode

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
