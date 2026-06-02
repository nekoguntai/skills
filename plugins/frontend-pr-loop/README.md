# frontend-pr-loop

Autonomous frontend/UI improvement loop for application repositories.

Ships one skill:

- **`/frontend-pr-loop:frontend-pr-loop`** - inspect the frontend, choose a bounded improvement, implement it, verify it, and deliver it through a merged PR

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
- Read-only recommendation mode when explicitly requested
- Implementation with focused verification
- PR creation, CI/review monitoring, safe merge, and ancestry verification through `/pr-delivery:pr-delivery`
- Optional post-merge container rebuild only when requested

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
