# Prismatic Thread Integration

Use this reference when the target repository contains `.prismatic-thread.yaml`
or when the user asks to publish validation progress to Prismatic Thread.

## Artifact Strategy

Keep the CSV canonical and generate stable artifacts:

- `docs/artifacts/feature-validation-loop.md`
- `docs/artifacts/feature-validation-ledger.html` when `--write-html` is used
- `docs/feature-validation/prismatic-thread-contribution.json` when
  `--write-contribution` is used

Use stable front matter:

```yaml
thread: feature-validation-loop
threadTitle: Feature Validation Loop
artifactKey: feature-validation-ledger
type: progress
format: markdown
status: needs_review
metadata:
  workStatus: in_progress
  disposition: committed
  sourcePath: docs/feature-validation/feature-validation-ledger.csv
  featureValidation:
    schemaVersion: 1
```

The HTML artifact uses:

```yaml
artifactKey: feature-validation-ledger-html
format: html
metadata:
  featureValidation:
    view: html
```

## Metadata Contract

Populate `metadata.featureValidation` with normalized numbers:

- `schemaVersion`
- `ledgerPath`
- `totalFeatures`
- `discoveredFeatures`
- `testDesignedFeatures`
- `testedFeatures`
- `passedFeatures`
- `failedFeatures`
- `openDefects`
- `criticalDefects`
- `highDefects`
- `uxDefects`
- `waivedDefects`
- `confidenceScore`
- `maxSeverity`
- `lastTestedAt`

Missing numbers should be treated as zero by consuming apps. Clamp
`confidenceScore` to `0-100`.

## Submission Order

1. Write collector-recognized files under the configured artifacts path and let
   the local collector submit them.
2. If immediate manual submission is needed, use:

```bash
pt-collector submit-file docs/artifacts/feature-validation-loop.md \
  --url "$PRISMATIC_THREAD_URL" \
  --api-key "$PRISMATIC_THREAD_API_KEY"
```

3. If a contribution envelope is needed, generate it with
   `prismatic_artifact.py --write-contribution` and validate or submit it with
   `prismatic-thread-agent`.

## HTML Safety

- Standalone HTML under `docs/feature-validation/` may include small inline
  JavaScript for filtering.
- Prismatic Thread HTML under `docs/artifacts/` must remain useful after
  sanitizer processing.
- Do not rely on scripts, inline event handlers, forms, external fonts, CDNs,
  or remote assets in the Prismatic Thread HTML artifact.
- Escape every CSV-derived value before writing HTML.
