# grade-loop

End-to-end quality remediation loop for application repositories.

Ships one skill:

- **`/grade-loop:grade-loop`** - grade a repo, review a remediation plan, implement a bounded fix, deliver the PR, verify target-branch post-merge CI, rebuild running app containers, and rerun grade

## Install

```
/plugin marketplace add nekoguntai/skills
/plugin install grade-loop@nekoguntai-skills
/reload-plugins
```

Then in any repo:

```
/grade-loop:grade-loop
```

## What it covers

- Initial codebase quality grading
- Bounded remediation planning and recursive plan review
- Implementation with focused and proportional verification
- PR delivery with merge ancestry and target-branch post-merge CI verification
- Rebuild of already-running localhost app containers
- Post-closeout grade rerun to decide whether another remediation pass is warranted

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
