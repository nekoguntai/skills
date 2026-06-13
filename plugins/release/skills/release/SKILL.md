---
name: release
description: >-
  Use when the user invokes $release or asks for release execution, release
  readiness, release candidates, pre-release gates, official release gates,
  stable tags, install/upgrade release readiness, artifact verification,
  package publishing, image publishing, downstream notifications, release
  objects, or building missing release infrastructure. A bare $release means cut
  the next patch release end to end for the current repository.
---

# Release

Run a repository-native release. Discover the repo's release surface first; do not invent a parallel release process.

## Guardrails

- Use the current repository as source of truth.
- Preserve unrelated dirty work; stage and commit only release files and release fixes.
- Never weaken branch protection, bypass required checks, merge through red checks, delete remote tags, or rewrite remote tags unless the user explicitly asks.
- Do not publish a stable tag while required release evidence is failing, running, skipped unexpectedly, or unknown.
- If a pushed RC is bad, prefer a new RC. If a pushed stable tag is bad, prefer a new patch release.

## Classify The Request

- **Bare `$release`**: cut the next patch release end to end.
- **Specific version**: release the requested `X.Y.Z` or `vX.Y.Z`.
- **Readiness/audit/status/plan**: inspect and report; do not tag or publish.
- **RC only**: cut and validate a release candidate; stop before stable promotion.
- **Stable only**: promote a validated candidate or equivalent evidence to stable.
- **Release infrastructure**: build missing versioning, gate, candidate, promotion, artifact, or install/upgrade components needed for safe releases.
- **Troubleshooting**: inspect failing release gates, fix root cause, and resume the appropriate release phase.

## Discover The Release Surface

Run or inspect:

```bash
git status --short --branch
git remote -v
git fetch --tags --prune
git tag --list 'v*' --sort=-version:refname | head -30
find . -maxdepth 3 -type f \( -name 'package.json' -o -name 'pyproject.toml' -o -name 'Cargo.toml' -o -name 'go.mod' -o -name 'CHANGELOG*' -o -name 'README*' \) -print
find . -maxdepth 4 -type f \( -path './.github/workflows/*' -o -path './.forgejo/workflows/*' -o -path './.gitea/workflows/*' \) -print
rg -n "release|pre-release|prerelease|candidate|rc|tag|version|changelog|install|upgrade|artifact|publish|registry|image|gate|ci:full|test:e2e|audit" README* CHANGELOG* docs .github .forgejo .gitea package.json pyproject.toml Cargo.toml go.mod 2>/dev/null
```

Identify:

- version files and lockfiles;
- release docs/runbooks;
- changelog convention;
- release workflow dispatch inputs and tag triggers;
- local full gate command;
- official pre-release and stable release gates;
- artifact, package, image, install, upgrade, or downstream publication checks;
- APIs/CLIs used to dispatch and monitor CI.

Prefer existing repo scripts, workflows, and docs over generic commands.

## Release Surface Gap Check

Before executing a release, confirm the repository has a coherent release contract:

- a stable version source and a way to update it;
- a tag naming convention for stable and pre-release builds;
- release notes or changelog location, or an explicit reason none is used;
- local gates that can prove the versioned tree;
- an official pre-release or candidate validation path;
- an official stable promotion path;
- a way to inspect required CI/check status;
- install/upgrade validation when the project is installable;
- artifact/package/image verification when the project publishes artifacts;
- documented rollback or recovery expectations for bad candidates or stable releases.

If any component is missing, point it out clearly before proceeding. Classify gaps as:

- **Blocking**: no safe release should be tagged until this exists, such as no version source, no release gate, no CI status visibility, or no stable promotion path.
- **Conditional**: required only if the project claims the related surface, such as image verification for image-publishing projects.
- **Advisory**: useful but not necessarily release-blocking, such as a more detailed changelog format.

For bare `$release`, stop before tagging when a blocking component is missing. Either add the missing component as release-prep work if the user's request reasonably includes building release infrastructure, or report the gap and ask for direction when the missing piece changes release policy.

## Gap Follow-Up Method

When release components are missing, present a follow-up build path before ending the turn. Keep it concrete enough that the user can approve or the agent can continue when the request already authorizes release-infrastructure work.

Use this structure:

1. **Gap report**: list missing components as Blocking, Conditional, or Advisory.
2. **Minimum viable release contract**: define the smallest safe release path for this repo, including version source, changelog/release notes, local full gate, pre-release gate, stable gate, tag convention, and install/upgrade/artifact checks when applicable.
3. **Implementation plan**: list exact files/scripts/workflows/docs/tests to add or update.
4. **Verification plan**: name the local tests and dry-run workflow validations that prove the release infrastructure before any real tag is pushed.
5. **Resume point**: state the next release action after the infrastructure passes, such as "rerun `$release` to cut `vX.Y.Z-rc.1`."

If the user asks to build the missing release path, implement it in the current repo using the repo's existing CI, scripting, and documentation style. Add tests for release planners/scripts, include dry-run or no-publish validation where practical, and do not push real tags until the new release infrastructure passes its own verification.

## Version Selection

Normalize versions as stable tags `vX.Y.Z` and RC tags using the repo's existing convention. Common forms are `vX.Y.Z-rc.N` or `vX.Y.Z-rcN`; use the convention already present in docs, scripts, tests, or workflows.

For bare `$release`:

1. Find the highest stable `vX.Y.Z` tag, ignoring prerelease and marker tags.
2. If a stable tag exists, increment the patch version.
3. If no stable tag exists, use the current version file as the first stable target when it is already a valid semver below `1.0.0`; otherwise choose the smallest sensible first release and explain the assumption.
4. Use the first unused RC for that stable version.

If the user supplies a version, use it when it matches the requested release type and no newer user instruction conflicts.

Before testing, update the repo's version files and lockfiles with the established command when available, for example `npm version --no-git-tag-version X.Y.Z`; otherwise edit the known version fields directly and keep lockfiles consistent.

## Local Gate Loop

Run focused checks first, then the repo's full release gate.

Common discovery order:

```bash
npm run ci:full
npm run test
npm run coverage
npm run lint
npm run typecheck
npm run build
npm audit --audit-level=high
```

Do not run unsafe direct database/browser/lifecycle commands when the repo documents guarded wrappers. Read test-runtime or release-gate docs before DB-backed, browser, migration, install, or upgrade tests.

When a gate fails:

1. Inspect logs and identify the root cause.
2. Reproduce with the smallest documented guarded command.
3. Fix the cause without weakening release gates.
4. Search related tests/workflows for the same pattern before rerunning.
5. Rerun the focused command, then rerun the broader release gate.
6. Continue until the release gate passes or a genuine external blocker has repeated enough to report as blocked.

## Commit And Push Prep

Before dispatching remote release gates:

```bash
git diff --check
git status --short
git add <release-version-files> <changelog/runbook-files> <release-fix-files>
git commit -m "Prepare vX.Y.Z release"
git push origin HEAD:<release-branch>
```

Use the repo's primary release branch unless release docs say otherwise. Do not include unrelated dirty files, generated reports, local artifacts, secrets, backups, or task notes unless the repo explicitly treats them as release artifacts.

## Pre-Release Gate

Use the repository's official release-candidate path. That may be:

- workflow dispatch with release stage/version inputs;
- tag push of an RC tag;
- a release script that creates and verifies candidate artifacts.

Requirements:

- The RC is built from the versioned release commit.
- The official pre-release gate passes.
- The RC tag/artifact is immutable enough for the repo's convention.
- If the gate fails after an RC tag is pushed, fix on the release branch and cut the next unused RC instead of retagging.

Verify the RC target:

```bash
git fetch --tags --force
git rev-parse "vX.Y.Z-rc.N^{}"
git merge-base --is-ancestor "vX.Y.Z-rc.N^{}" <release-branch-or-remote>
```

Adapt tag syntax to the repo's RC convention.

## Candidate Install/Upgrade Smoke

If the repo ships an installable service or package, validate the RC through the documented install/upgrade path before stable promotion.

Common checks:

- fresh install against an empty target;
- upgrade from an existing supported version;
- health/readiness endpoint or equivalent smoke;
- backup/restore or artifact verification when release docs require it;
- package/image inspection when publishing artifacts.

Use only documented production confirmations and guarded test/deploy entry points. Do not casually stop existing long-running services unless the release workflow requires it.

## Official Release Gates

After the RC passes, run the repo's official release-testing or stable-promotion gate. Common patterns:

- retest the RC tag and create a release-tested marker;
- run a stable release workflow against the RC;
- promote the exact RC commit to `vX.Y.Z`;
- publish packages/images/artifacts;
- create release objects;
- notify downstream repositories or installers.

Verify stable promotion points to the same commit as the accepted RC unless the repo documents a different signed-artifact process:

```bash
git fetch --tags --force
test "$(git rev-parse "vX.Y.Z^{}")" = "$(git rev-parse "vX.Y.Z-rc.N^{}")"
```

The stable tag is ready to install or upgrade to only after official release gates and required publication/install/upgrade checks pass.

## Recovery

- Before pushing a bad local tag: `git tag -d <tag>`.
- After pushing a bad RC tag: create the next RC.
- After pushing a bad stable tag: prefer a new patch release.
- Remote tag deletion, release-object deletion, package/image deletion, and downstream rollback require explicit user instruction.

## Final Report

Report:

- stable version/tag, RC tag, and commit SHA;
- version/changelog files changed;
- local gates run and results;
- remote release/pre-release/stable gates and results;
- install/upgrade smoke or artifact verification result;
- publication/downstream result, if any;
- skipped checks with reasons;
- dirty files intentionally left untouched;
- recovery path for any accepted risk.
