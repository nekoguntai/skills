# Node Projects

Read this when `package.json` or a JavaScript/TypeScript lockfile is present.

## Package Manager

Use the lockfile to choose install commands:

- `package-lock.json`: `npm ci`
- `pnpm-lock.yaml`: `pnpm install --frozen-lockfile`
- `yarn.lock`: `yarn install --immutable` for modern Yarn, otherwise follow the
  repo's existing workflow
- `bun.lock` or `bun.lockb`: `bun install --frozen-lockfile`

Use the repo's `engines.node`, `.nvmrc`, or `.node-version`. If none exists,
prefer Node 24 for new scaffolds unless dependencies require a lower supported
version.

## Scripts

Create or normalize these scripts when compatible with the repo:

- `lint`: static lint checks;
- `typecheck`: TypeScript compile check without emit;
- `test:run`: non-watch unit test run;
- `coverage`: unit tests with 100% coverage gate;
- `build`: production build;
- `audit`: dependency audit;
- `ci`: deterministic full gate in the same order CI runs.

For npm, `ci` often becomes:

```json
"ci": "npm run lint && npm run typecheck && npm run coverage && npm run build && npm audit --audit-level=high"
```

Adapt for packages without TypeScript/builds. In workspaces, either use a root
aggregator or workspace-aware commands; do not leave child packages outside the
coverage gate.

## Vitest Coverage

Use V8 coverage unless the repo already uses another provider. Ensure
`@vitest/coverage-v8` is installed for matching Vitest versions.

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "json-summary"],
      thresholds: {
        statements: 100,
        branches: 100,
        functions: 100,
        lines: 100,
      },
      include: ["src/**/*.{ts,tsx,js,jsx}"],
      exclude: [
        "**/*.d.ts",
        "**/generated/**",
        "**/dist/**",
        "**/build/**",
      ],
    },
  },
});
```

For frontend React projects, add Testing Library tests for behavior, state,
forms, routing, and error/empty states. For services, cover validation,
serialization, error paths, async failure, and boundary cases.

## Jest Coverage

Use all four thresholds:

```js
module.exports = {
  collectCoverage: true,
  coverageReporters: ["text", "lcov", "json-summary"],
  coverageThreshold: {
    global: {
      branches: 100,
      functions: 100,
      lines: 100,
      statements: 100,
    },
  },
};
```

## CI Job Notes

Cache package-manager downloads, not `node_modules`. Keep install and gate
commands explicit. Include `npm audit`, `pnpm audit`, or the established scanner
as a blocking job unless the repo intentionally uses a different vulnerability
management gate.
