import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import test from "node:test";

const execFileAsync = promisify(execFile);
const scriptPath = fileURLToPath(new URL("./inventory-ui-controls.mjs", import.meta.url));

async function write(root, relative, source) {
  const target = path.join(root, relative);
  await fs.mkdir(path.dirname(target), { recursive: true });
  await fs.writeFile(target, source, "utf8");
}

async function run(root, ...args) {
  const { stdout } = await execFileAsync(process.execPath, [scriptPath, root, ...args]);
  return JSON.parse(stdout);
}

async function fixture() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "visual-inventory-test-"));
  await write(root, "styles.scss", `$brand: oklch(60% 0.2 30);
@accent: color(srgb 1 0 0);
:root { --surface: lab(40% 10 20); }
.card {
  border:
    1px solid hwb(120 10% 20%);
  background-image: linear-gradient(
    oklab(50% 0.1 0.1),
    lch(60% 30 20)
  );
  box-shadow: 0 0 4px var(--rule, #ccc);
}
.badge {
  accent-color: rebeccapurple;
  text-decoration-color: blue;
}
.token-owned { color: var(--red); }
.external-icon { background-image: url("icon.svg#fff"); }
.data-icon { background-image: url("data:image/svg+xml,<svg fill='#fff'></svg>"); }
`);
  await write(root, "component.tsx", `const prose = "white black red blue";
const tokenOwned = { color: theme.red };
node.style.color = "#fff";
node.style.border = "1px solid red";
node.style.background = "linear-gradient(#fff, #000)";
export const Icon = () => <svg fill="#000"><path stroke={"color(srgb 1 0 0)"} /></svg>;
`);
  await write(root, "e2e/flow.e2e.tsx", `export const testTabs = <div role="tablist" />;\n`);
  await write(root, "tests/unit.test.tsx", `export const testTabs = <div role="tablist" />;\n`);
  await write(root, "integration/flow.tsx", `export const testTabs = <div role="tablist" />;\n`);
  await write(root, "__mocks__/component.tsx", `export const testTabs = <div role="tablist" />;\n`);
  await write(root, "__fixtures__/component.tsx", `export const testTabs = <div role="tablist" />;\n`);
  await write(root, "spec/component.tsx", `export const testTabs = <div role="tablist" />;\n`);
  await write(root, "docs/example.mdx", `<div role="tablist" />\n`);
  await write(root, ".storybook/example.stories.tsx", `export const story = <div role="tablist" />;\n`);
  await write(root, "stories/example.tsx", `export const story = <div role="tablist" />;\n`);
  await write(root, "generated/types.ts", `export const generated = 'role="tablist"';\n`);
  await write(root, "scripts/build.ts", `export const tooling = 'role="tablist"';\n`);
  return root;
}

function signalCount(result, kind) {
  return result.summary.signals[kind] ?? 0;
}

test("finds modern, multiline, SVG, DOM, and fallback colors without token duplication", async (context) => {
  const root = await fixture();
  context.after(() => fs.rm(root, { recursive: true, force: true }));
  const result = await run(root);

  assert.equal(signalCount(result, "token-color-definition"), 3);
  assert.equal(signalCount(result, "hard-coded-style-color"), 5);
  assert.equal(signalCount(result, "hard-coded-dom-style-color"), 3);
  assert.equal(signalCount(result, "hard-coded-svg-color"), 2);
  assert.equal(signalCount(result, "tablist"), 0);
  const styleExcerpts = result.records.flatMap((record) => record.matches)
    .filter((match) => match.kind === "hard-coded-style-color")
    .map((match) => match.excerpt);
  assert.ok(styleExcerpts.every((excerpt) => !excerpt.startsWith("--")));
  assert.ok(styleExcerpts.some((excerpt) => excerpt.includes("linear-gradient")));
  assert.equal(result.repository.root, ".");
});

test("classifies excluded scopes and includes them only through explicit flags", async (context) => {
  const root = await fixture();
  context.after(() => fs.rm(root, { recursive: true, force: true }));
  const production = await run(root);

  assert.deepEqual(production.summary.scannedFilesByCategory, { production: 2 });
  assert.deepEqual(production.summary.excludedFilesByCategory, {
    documentation: 1,
    generated: 1,
    storybook: 2,
    test: 6,
    tooling: 1
  });

  const all = await run(
    root,
    "--include-tests", "--include-stories", "--include-docs", "--include-generated", "--include-tooling"
  );
  assert.equal(all.summary.filesExcludedByCategory, 0);
  assert.equal(signalCount(all, "tablist"), 11);
});

test("rejects missing and option-looking values", async () => {
  await assert.rejects(execFileAsync(process.execPath, [scriptPath, "--extensions", "--include-tests"]));
  await assert.rejects(execFileAsync(process.execPath, [scriptPath, "--output", "--include-tests"]));
});

test("supports custom extensions and opt-in absolute roots", async (context) => {
  const root = await fixture();
  context.after(() => fs.rm(root, { recursive: true, force: true }));
  const result = await run(root, "--extensions", "tsx", "--include-tests", "--absolute-root");

  assert.deepEqual(result.selection.extensions, [".tsx"]);
  assert.equal(result.repository.root, root);
  assert.equal(signalCount(result, "tablist"), 6);
});
