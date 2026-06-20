# rationalize-loop

End-to-end convergence remediation loop for application repositories, with
stale-context resets at startup and between convergence passes.

Ships one skill:

- **`/rationalize-loop:rationalize-loop`** - rationalize divergent paths, review a convergence plan, implement a bounded phase, deliver the PR, verify target-branch post-merge CI, rebuild running app containers, and rerun rationalize from refreshed target-branch state

## Install

```
/plugin marketplace add nekoguntai/skills
/plugin install rationalize-loop@nekoguntai-skills
/reload-plugins
```

Then in any repo:

```
/rationalize-loop:rationalize-loop
```

## What it covers

- Divergence inventory and canonical path decisions
- Stale-context reset at startup and between convergence passes
- Bounded convergence planning and recursive plan review
- Implementation with compatibility and drift-test discipline
- PR delivery with merge ancestry and target-branch post-merge CI verification
- Rebuild of already-running localhost app containers
- Post-closeout rationalize rerun to decide whether another convergence pass is warranted

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
