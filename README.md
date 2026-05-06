# nekoguntai / skills

A personal Claude Code plugin marketplace. Each plugin lives in its own subdirectory under `plugins/` and ships one or more skills.

## Quick install

Add the marketplace once, then install any plugin from it:

```
/plugin marketplace add nekoguntai/skills
/plugin install <plugin-name>@nekoguntai-skills
/reload-plugins
```

Where `<plugin-name>` is one of the plugins listed below.

## Plugins

| Plugin | Skills | Description |
|---|---|---|
| [`grade`](plugins/grade) | `/grade:grade`, `/grade:grade-history` | Strict, evidence-driven software quality audit anchored to ISO/IEC 25010. Multi-domain scoring, full + diff modes, trend tracking, multi-language. |
| [`pr-delivery`](plugins/pr-delivery) | `/pr-delivery:pr-delivery` | End-to-end pull request delivery workflow covering commit, push, PR creation, CI/review monitoring, safe merge, verification, and cleanup. |

<!-- Add new plugins here as rows. Each plugin needs:
     1. Its own directory under plugins/
     2. A plugins/<name>/.claude-plugin/plugin.json with the name field
     3. A plugins/<name>/skills/<skill-name>/SKILL.md per skill
     4. A new entry in .claude-plugin/marketplace.json
     5. A row in the table above -->

## Repo layout

```
skills/                           (this repo)
├── .claude-plugin/
│   └── marketplace.json          # marketplace catalog — all plugins listed here
├── plugins/
│   └── <plugin-name>/
│       ├── .claude-plugin/
│       │   └── plugin.json       # plugin manifest
│       ├── skills/
│       │   └── <skill-name>/
│       │       ├── SKILL.md      # skill instructions
│       │       └── ...           # supporting scripts / data
│       └── README.md             # plugin-specific docs
├── README.md                     # this file
└── LICENSE
```

## Adding a new plugin

1. Create `plugins/<new-plugin>/.claude-plugin/plugin.json` with `name`, `description`, `author`, `license`.
2. Create `plugins/<new-plugin>/skills/<skill>/SKILL.md` for each skill the plugin ships. Use `${CLAUDE_SKILL_DIR}` to reference sibling files (scripts, markdown, etc.) — this works for both plugin-installed and standalone skills.
3. Add the plugin to `.claude-plugin/marketplace.json` under `plugins`. Use a relative path like `"source": "<new-plugin>"` (the `metadata.pluginRoot` makes paths relative to `./plugins/`). Set `version` here, not in `plugin.json` — for relative-path plugins, the plugin manifest's version silently wins and can shadow marketplace updates.
4. Add a row to the **Plugins** table in this README.
5. Commit and push. Existing installs pick up new plugins via `/plugin marketplace update nekoguntai-skills`.

## Updating an existing plugin

Bump the `version` field in `.claude-plugin/marketplace.json` for that plugin. Without a version bump, Claude Code's plugin cache won't re-install the updated files. Users pull updates with `/plugin marketplace update nekoguntai-skills` followed by `/reload-plugins`.

## License

MIT — see [LICENSE](LICENSE).
