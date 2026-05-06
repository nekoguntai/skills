# pr-delivery

End-to-end pull request delivery workflow for taking local changes through commit, push, PR creation, checks, reviews, safe merge, verification, and branch/worktree cleanup.

Ships one skill:

- **`/pr-delivery:pr-delivery`** - deliver a branch through the full pull request lifecycle

## Install

```
/plugin marketplace add nekoguntai/skills
/plugin install pr-delivery@nekoguntai-skills
/reload-plugins
```

Then in any repo:

```
/pr-delivery:pr-delivery
```

## What it covers

- Dirty-worktree preflight and unrelated-change handling
- Focused verification before committing
- Clean staging and commit discipline
- Push and PR creation or continuation
- CI, check, and review monitoring
- GitHub merge queue and protected-branch merge handling
- Forgejo scheduled auto-merge handling
- Post-merge verification and safe cleanup

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
