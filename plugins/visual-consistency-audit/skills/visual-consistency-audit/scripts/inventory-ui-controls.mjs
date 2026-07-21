#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";

const DEFAULT_EXTENSIONS = new Set([
  ".astro", ".cjs", ".css", ".html", ".js", ".jsx", ".less", ".mdx", ".mjs", ".mts",
  ".sass", ".scss", ".svelte", ".ts", ".tsx", ".vue"
]);
const EXCLUDED_DIRECTORIES = new Set([
  ".git", ".next", ".nuxt", ".output", ".svelte-kit", "build", "coverage", "dist",
  "node_modules", "playwright-report", "storybook-static", "test-results"
]);

const NAMED_COLORS = new Set((
  "aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood " +
  "cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray " +
  "darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen " +
  "darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue " +
  "firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew " +
  "hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan " +
  "lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray " +
  "lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid " +
  "mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream " +
  "mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen " +
  "paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown " +
  "royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow " +
  "springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen"
).split(" "));
const HEX_OR_FUNCTION_COLOR = /#[0-9a-f]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^;{}]+\)/gi;
const STYLE_COLOR_PROPERTY = String.raw`(?:accent-color|background(?:-color|-image)?|border(?:-(?:top|right|bottom|left|inline(?:-start|-end)?|block(?:-start|-end)?))?(?:-color|-image)?|box-shadow|caret-color|color|column-rule-color|fill|flood-color|lighting-color|outline(?:-color)?|scrollbar-color|stop-color|stroke|text-decoration-color|text-emphasis-color|text-shadow|accentColor|backgroundColor|backgroundImage|borderColor|borderImage|boxShadow|caretColor|columnRuleColor|outlineColor|scrollbarColor|textDecorationColor|textEmphasisColor|textShadow)`;
const STYLE_COLOR_DECLARATION = new RegExp(String.raw`(?<![-\w$@])(${STYLE_COLOR_PROPERTY})\s*:\s*([^;}]+)`, "gi");
const TOKEN_COLOR_DECLARATION = /(?:--|\$|@)[\w-]+\s*:\s*([^;}]+)/gi;
const DOM_STYLE_ASSIGNMENT = new RegExp(String.raw`\.style\.(${STYLE_COLOR_PROPERTY})\s*=\s*(["'])([^"']*)\2`, "gi");
const SVG_COLOR_ATTRIBUTE = new RegExp(String.raw`\b(?:fill|stroke|stop-color|flood-color|lighting-color)\s*=\s*\{?\s*(["'])([^"']*)\1`, "gi");

const SIGNALS = [
  ["tablist", /role\s*=\s*[{"']*tablist\b/gi],
  ["pressed-choice", /aria-pressed\s*=/gi],
  ["button-element", /<button\b/gi],
  ["button-role", /role\s*=\s*[{"']*button\b/gi],
  ["dialog", /(?:<dialog\b|role\s*=\s*[{"']*(?:dialog|alertdialog)\b)/gi],
  ["navigation", /(?:<nav\b|role\s*=\s*[{"']*navigation\b)/gi],
  ["utility-color-class", /\b(?:bg|text|border|fill|stroke)-(?:white|black|\[[#a-z0-9(),.%/ -]+\])/gi],
  ["ink-background", /background(?:-color)?\s*:\s*["']?var\(\s*--(?:ink|foreground|text)(?:\s*,[^)]*)?\s*\)/gi],
  ["glow-or-shadow", /(?:box-shadow|text-shadow|filter\s*:\s*drop-shadow)\s*:/gi],
  ["state-pseudo-element", /(?:\[[^\]]*(?:active|checked|pressed|selected)[^\]]*\]|\.(?:active|selected|pressed|current)\b)[^{]*::(?:before|after)/gi],
  ["thick-border-declaration", /border-(?:left|right|top|bottom|inline(?:-start|-end)?|block(?:-start|-end)?)\s*:\s*(?:[2-9]|[1-9]\d+)px/gi],
  ["overflow-rule", /overflow-(?:x|y)\s*:/gi]
];

function usage() {
  return [
    "Usage: inventory-ui-controls.mjs [repo-root] [options]",
    "Options:",
    "  --output path          Write JSON to path instead of stdout",
    "  --extensions list      Comma-separated extensions (default: common UI sources)",
    "  --include-tests        Include tests, fixtures, and mocks",
    "  --include-stories      Include Storybook files and configuration",
    "  --include-docs         Include files under docs directories",
    "  --include-generated    Include source files named generated/gen",
    "  --include-tooling      Include scripts, tools, and config sources",
    "  --absolute-root        Persist the absolute repository path in JSON"
  ].join("\n");
}

function normalizedExtensions(value) {
  const extensions = value.split(",").map((item) => item.trim()).filter(Boolean)
    .map((item) => item.startsWith(".") ? item.toLowerCase() : `.${item.toLowerCase()}`);
  if (extensions.length === 0) throw new Error("--extensions requires at least one extension");
  return new Set(extensions);
}

function parseArguments(argv) {
  const options = {
    root: ".", output: undefined, extensions: DEFAULT_EXTENSIONS, absoluteRoot: false,
    includeTests: false, includeStories: false, includeDocs: false, includeGenerated: false,
    includeTooling: false
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--output" || argument === "--extensions") {
      const value = argv[index + 1];
      if (!value || value.startsWith("-")) throw new Error(`${argument} requires a non-option value`);
      if (argument === "--output") options.output = path.resolve(value);
      else options.extensions = normalizedExtensions(value);
      index += 1;
    } else if (argument === "--include-tests") options.includeTests = true;
    else if (argument === "--include-stories") options.includeStories = true;
    else if (argument === "--include-docs") options.includeDocs = true;
    else if (argument === "--include-generated") options.includeGenerated = true;
    else if (argument === "--include-tooling") options.includeTooling = true;
    else if (argument === "--absolute-root") options.absoluteRoot = true;
    else if (argument === "--help" || argument === "-h") {
      process.stdout.write(`${usage()}\n`);
      process.exit(0);
    } else if (argument.startsWith("-")) throw new Error(`Unknown option: ${argument}`);
    else options.root = argument;
  }
  options.root = path.resolve(options.root);
  return options;
}

function classifyFile(relative) {
  const normalized = `/${relative.toLowerCase()}`;
  if (/(?:^|\/)(?:generated|gen)(?:\/|$)|\.(?:generated|gen)\./.test(normalized)) return "generated";
  if (/(?:^|\/)(?:\.storybook|stories|storybook)(?:\/|$)|\.stories\.[^/]+$/.test(normalized)) return "storybook";
  if (/(?:^|\/)(?:__tests__|__fixtures__|__mocks__|test|tests|spec|specs|fixtures|mocks?|e2e|cypress|playwright|browser-tests?|ui-tests?|integration|integration-tests?)(?:\/|$)|\.(?:test|spec|e2e|cy)\.[^/]+$/.test(normalized)) return "test";
  if (/(?:^|\/)docs?(?:\/|$)/.test(normalized)) return "documentation";
  if (/^\/(?:scripts?|tools?)\/|(?:^|\/)[^/]+\.config\.[^/]+$/.test(normalized)) return "tooling";
  return "production";
}

function categoryIncluded(category, options) {
  if (category === "test") return options.includeTests;
  if (category === "storybook") return options.includeStories;
  if (category === "documentation") return options.includeDocs;
  if (category === "generated") return options.includeGenerated;
  if (category === "tooling") return options.includeTooling;
  return true;
}

async function collectFiles(directory, root, extensions, files = []) {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  entries.sort((left, right) => left.name.localeCompare(right.name));
  for (const entry of entries) {
    if (entry.name.startsWith(".") && entry.name !== ".storybook") continue;
    if (EXCLUDED_DIRECTORIES.has(entry.name)) continue;
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) await collectFiles(absolute, root, extensions, files);
    else if (entry.isFile() && extensions.has(path.extname(entry.name).toLowerCase())) {
      const relative = path.relative(root, absolute).split(path.sep).join("/");
      files.push({ absolute, relative, category: classifyFile(relative) });
    }
  }
  return files;
}

function lineNumberAt(source, offset) {
  let line = 1;
  for (let index = 0; index < offset; index += 1) if (source.charCodeAt(index) === 10) line += 1;
  return line;
}

function compactExcerpt(value) {
  return value.replaceAll(/\s+/g, " ").trim().slice(0, 180);
}

function containsColorLiteral(value) {
  const withoutUrls = value.replaceAll(/\burl\([^)]*\)/gi, " ");
  HEX_OR_FUNCTION_COLOR.lastIndex = 0;
  if (HEX_OR_FUNCTION_COLOR.test(withoutUrls)) return true;
  const withoutReferences = withoutUrls
    .replaceAll(/\b(?:var|env)\(\s*[-\w]+\s*(?:,\s*([^)]*))?\)/gi, (_match, fallback) => fallback ?? "");
  for (const match of withoutReferences.matchAll(/[a-z]+/gi)) {
    if (!NAMED_COLORS.has(match[0].toLowerCase())) continue;
    const previous = withoutReferences[match.index - 1] ?? "";
    const next = withoutReferences[match.index + match[0].length] ?? "";
    if (!/[.\w-]/.test(previous) && !/[.\w-]/.test(next)) return true;
  }
  return false;
}

function scanColorDeclarations(source) {
  const matches = [];
  for (const [kind, declarationPattern] of [
    ["hard-coded-style-color", STYLE_COLOR_DECLARATION],
    ["token-color-definition", TOKEN_COLOR_DECLARATION]
  ]) {
    declarationPattern.lastIndex = 0;
    for (const declaration of source.matchAll(declarationPattern)) {
      if (!containsColorLiteral(declaration[0])) continue;
      matches.push({
        kind,
        line: lineNumberAt(source, declaration.index),
        excerpt: compactExcerpt(declaration[0])
      });
    }
  }
  return matches;
}

function scanContextColorLiterals(source) {
  const matches = [];
  for (const [kind, pattern] of [
    ["hard-coded-dom-style-color", DOM_STYLE_ASSIGNMENT],
    ["hard-coded-svg-color", SVG_COLOR_ATTRIBUTE]
  ]) {
    const contextSource = kind === "hard-coded-svg-color"
      ? source.replaceAll(/\burl\([^)]*\)/gi, (url) => url.replaceAll(/[^\n]/g, " "))
      : source;
    pattern.lastIndex = 0;
    for (const match of contextSource.matchAll(pattern)) {
      if (!containsColorLiteral(match[0])) continue;
      matches.push({ kind, line: lineNumberAt(contextSource, match.index), excerpt: compactExcerpt(match[0]) });
    }
  }
  return matches;
}

function scanSource(file, source) {
  const matches = [...scanColorDeclarations(source), ...scanContextColorLiterals(source)];
  for (const [kind, pattern] of SIGNALS) {
    pattern.lastIndex = 0;
    for (const match of source.matchAll(pattern)) {
      matches.push({ kind, line: lineNumberAt(source, match.index), excerpt: compactExcerpt(match[0]) });
    }
  }
  matches.sort((left, right) => left.line - right.line || left.kind.localeCompare(right.kind));
  return matches.length > 0 ? { file: file.relative, category: file.category, matches } : undefined;
}

function countsBy(items, key) {
  const counts = {};
  for (const item of items) counts[item[key]] = (counts[item[key]] ?? 0) + 1;
  return Object.fromEntries(Object.entries(counts).sort(([left], [right]) => left.localeCompare(right)));
}

function summarize(records, candidates, selectedFiles) {
  const matches = records.flatMap((record) => record.matches);
  const excludedFiles = candidates.filter((file) => !selectedFiles.includes(file));
  return {
    candidateFiles: candidates.length,
    candidateFilesByCategory: countsBy(candidates, "category"),
    filesScanned: selectedFiles.length,
    filesExcludedByCategory: candidates.length - selectedFiles.length,
    excludedFilesByCategory: countsBy(excludedFiles, "category"),
    filesWithSignals: records.length,
    scannedFilesByCategory: countsBy(selectedFiles, "category"),
    signals: countsBy(matches, "kind")
  };
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  const stat = await fs.stat(options.root);
  if (!stat.isDirectory()) throw new Error(`Repository root is not a directory: ${options.root}`);
  const candidates = await collectFiles(options.root, options.root, options.extensions);
  const selectedFiles = candidates.filter((file) => categoryIncluded(file.category, options));
  const records = [];
  for (const file of selectedFiles) {
    const record = scanSource(file, await fs.readFile(file.absolute, "utf8"));
    if (record) records.push(record);
  }
  const repository = { label: path.basename(options.root), root: options.absoluteRoot ? options.root : "." };
  const result = {
    schemaVersion: 2,
    repository,
    selection: {
      extensions: [...options.extensions].sort(),
      includeTests: options.includeTests,
      includeStories: options.includeStories,
      includeDocs: options.includeDocs,
      includeGenerated: options.includeGenerated,
      includeTooling: options.includeTooling
    },
    summary: summarize(records, candidates, selectedFiles),
    records
  };
  const json = `${JSON.stringify(result, null, 2)}\n`;
  if (options.output) {
    await fs.mkdir(path.dirname(options.output), { recursive: true });
    await fs.writeFile(options.output, json, "utf8");
  } else process.stdout.write(json);
}

main().catch((error) => {
  process.stderr.write(`UI inventory failed: ${error instanceof Error ? error.message : String(error)}\n${usage()}\n`);
  process.exitCode = 1;
});
