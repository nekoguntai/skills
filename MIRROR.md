# Mirror layout

This repository is hosted on **Forgejo** (source of truth) and
auto-mirrored to **GitHub** (downstream, read-only):

- **Source:** http://10.14.23.20:3000/nekoguntai/skills
- **Mirror:** https://github.com/nekoguntai/skills

The mirror is configured in Forgejo with `sync_on_commit: true`, so any
push to Forgejo propagates to GitHub within seconds. There is also an
8 hour periodic sync as a backstop.

## Development workflow

```
edit files
git commit
git push origin main      # → Forgejo, then mirrored to GitHub
```

Local clone remotes:

```
origin  http://10.14.23.20:3000/nekoguntai/skills.git  (push target)
github  git@github.com:nekoguntai/skills.git           (preserved as fallback only)
```
