# pr-delivery

End-to-end pull request delivery workflow for GitHub and Forgejo repositories.
The skill takes local changes through commit, push, PR creation, checks,
reviews, safe merge, optional target-branch post-merge CI verification, and
branch/worktree cleanup.

Ships one skill:

- **`$pr-delivery`** / **`/pr-delivery:pr-delivery`** - deliver a branch through the full pull request lifecycle

## Codex Use

This plugin includes Codex metadata at `.codex-plugin/plugin.json`. The skill
can also be installed as a local skill by copying or syncing
`skills/pr-delivery/SKILL.md` to `$CODEX_HOME/skills/pr-delivery/SKILL.md`.

The current local install path is:

```
~/.codex/skills/pr-delivery/SKILL.md
```

In any Codex session:

```
$pr-delivery
```

## Legacy Marketplace Install

```
/plugin marketplace add nekoguntai/skills
/plugin install pr-delivery@nekoguntai-skills
/reload-plugins
```

Then in any compatible plugin session:

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
- Post-merge ancestry verification, optional target-branch CI verification, and safe cleanup

## License

MIT - see the repo-level [LICENSE](../../LICENSE).
