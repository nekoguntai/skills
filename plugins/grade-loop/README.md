# grade-loop

End-to-end quality remediation loop for application repositories, with durable
iteration state, archived grade evidence, and strict cleanup to a verified
repository inventory baseline after every pass and terminal exit.

Ships one skill:

- **`/grade-loop:grade-loop`** - grade a repo, review a remediation plan, implement a bounded fix, deliver the PR, verify target-branch post-merge CI, rebuild running app containers, and rerun grade from refreshed target-branch state

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
- Stale-context reset at startup and between remediation passes
- Bounded remediation planning and recursive plan review
- Implementation with focused and proportional verification
- PR delivery with merge ancestry and target-branch post-merge CI verification
- Rebuild of already-running localhost app containers
- Initial and post-closeout audits on owned branches or worktrees
- External durable run state and report/history/plan/evidence archives
- Two delivery passes by default, with review and delivery gates retained
- Full inventory restoration after each iteration and every terminal exit

The loop requires the API 1 cleanup inventory provider shipped by
`pr-delivery`. It stops before repository mutation if that provider is
unavailable. Run state and archived evidence are stored outside repository
checkouts and worktrees.

## Validation

```bash
python3 -m unittest discover -s plugins/grade-loop/skills/grade-loop/scripts -p 'test_*.py' -v
python3 -m unittest discover -s plugins/bug-scrub-loop/skills/bug-scrub-loop/scripts -p 'test_*.py' -v
python3 -m unittest discover -s plugins/pr-delivery/skills/pr-delivery/scripts -p 'test_*.py' -v
```

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
