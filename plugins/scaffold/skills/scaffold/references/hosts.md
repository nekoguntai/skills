# GitHub And Forgejo

Read this when the target repo has a GitHub or Forgejo/Gitea-compatible remote
or workflow directory.

## Host Detection

- GitHub: `github.com` remote or existing `.github/workflows`.
- Forgejo: `.forgejo/workflows`, Codeberg/Forgejo remote, or a repo URL whose
  API exposes `/api/v1/version`.
- If both workflow dirs exist, preserve the repo's active host unless the user
  asks to migrate.

Use Actions-compatible YAML for both hosts, but avoid GitHub-only events and
contexts on Forgejo unless the target instance proves support through existing
workflows or API docs.

## Workflow Location

- GitHub: `.github/workflows/ci.yml`.
- Forgejo: `.forgejo/workflows/ci.yml`.

Small portable workflow skeleton:

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
  schedule:
    - cron: "17 8 * * *"

permissions:
  contents: read

concurrency:
  group: ci-${{ github.event_name }}-${{ github.event.pull_request.head.ref || github.ref_name || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  ci:
    name: ci
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Add host/package-manager setup.
      # Run deterministic install.
      # Run lint/typecheck/coverage/build/audit/security gates.
```

For Forgejo, remove `merge_group`; keep the rest only when the runner supports
the syntax. If an existing Forgejo workflow omits `permissions` or concurrency
expressions because the instance does not support them, follow the local pattern.

## GitHub Protection

Prefer `gh` when authenticated. Discover repo and default branch:

```bash
gh repo view --json nameWithOwner,defaultBranchRef,url
gh api repos/:owner/:repo/branches/main/protection
```

After the CI workflow has produced status contexts, configure branch protection
or a ruleset requiring the actual check names. A branch protection payload should
express:

- `required_status_checks.strict: true`;
- `required_status_checks.contexts` containing all blocking check names;
- `required_pull_request_reviews.required_approving_review_count` at least `1`
  when the project expects review;
- `required_pull_request_reviews.dismiss_stale_reviews: true`;
- `enforce_admins: true` unless the owner intentionally allows admin bypass;
- `restrictions: null` unless the repo uses explicit push allowlists;
- force pushes and deletions disabled;
- conversation resolution and linear history when the repo policy supports them.

If `gh api repos/:owner/:repo/branches/<branch>/protection` is unavailable
because the repo uses rulesets, inspect and update repository rulesets instead:

```bash
gh api repos/:owner/:repo/rulesets
```

Always read protection back after changes and verify the expected required
checks are present.

## Forgejo Protection

Use the instance API under `/api/v1`. First verify the instance exposes branch
protection endpoints and field names:

```bash
FORGEJO_API="${FORGEJO_URL%/}/api/v1"
curl -fsS "$FORGEJO_API/version"
curl -fsS "$FORGEJO_URL/swagger.v1.json" \
  | jq -r '.paths | keys[] | select(test("branch_protection|branch_protections"))'
```

Common Forgejo/Gitea-compatible endpoints are:

- `GET /repos/{owner}/{repo}/branch_protections`
- `POST /repos/{owner}/{repo}/branch_protections`
- `GET/PATCH /repos/{owner}/{repo}/branch_protections/{name}`

Before applying an example payload, confirm field names in `swagger.v1.json` for
the target instance. Configure the equivalent of:

- protected branch name;
- push disabled or push whitelist empty for normal writers;
- status checks enabled with required CI contexts;
- required approvals enabled;
- stale/outdated approvals blocked when supported;
- rejected reviews and unresolved review requests blocking merge when supported;
- force push and deletion disabled when exposed.

Read the protection back through the API after configuration. If the instance
has no API support or the token lacks admin rights, provide the exact UI path and
settings to apply instead of marking enforcement complete.

## Verification

Evidence that enforcement is real:

- host API readback shows the target branch has required PR/status policy;
- required status names match jobs emitted by the workflow;
- default branch is not the current direct-edit branch;
- a PR can be opened from a task branch and cannot merge until checks pass.

Do not use an actual direct push to test blocking unless the user explicitly
approves that destructive probe. `git push --dry-run` is optional evidence only;
host API readback is the primary proof.
