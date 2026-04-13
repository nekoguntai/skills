# grade

Strict, evidence-driven software quality audit for any repository. Produces a defensible multi-domain quality score anchored to **ISO/IEC 25010** — not an LLM opinion.

Ships two skills:

- **`/grade:grade`** — runs the audit and produces the report
- **`/grade:grade-history`** — displays the timeline of past runs for the current repo, without re-auditing

## The spirit

> `/grade` is an **audit tool, not an LLM opinion generator.**

Full philosophy, ISO 25010 mapping, and every threshold's citation (McCabe 1976, NIST SP 500-235, SonarQube defaults, OWASP CVSS, Google SRE) lives in [`skills/grade/standards.md`](skills/grade/standards.md). Read it before your first run.

The core principles:

1. **Anchor to real standards.** Every mechanical threshold traces to a documented industry source. No made-up numbers.
2. **Measure what can be measured. Judge what can't.** Real tools (lizard, jscpd, gitleaks, native test/lint/audit runners) get thresholds. No-tool criteria get LLM judgment anchored to an ISO 25010 sub-characteristic — never freeform vibes.
3. **Never fake objectivity with a weak grep proxy.** Missing tool → `unknown` and lowered confidence, never regex-substitute.
4. **Cite everything.** Every score cites either `tool + threshold + exit status` or `ISO sub-characteristic + inspection target + file path`.
5. **Work across languages** via multi-language tools.
6. **Acknowledge what static analysis can't see.** DORA/SRE metrics need runtime data; this tool scores their *enablers* (CI, Dockerfile, health endpoints) and labels the result "DORA-readiness".

## Scoring breakdown

| Domain | Weight | ISO 25010 Characteristic |
|---|---|---|
| Correctness | 20 | Functional Suitability |
| Reliability | 15 | Reliability (Fault Tolerance, Recoverability) |
| Maintainability | 15 | Maintainability (Modularity, Analyzability, Modifiability) |
| Security | 15 | Security (Confidentiality, Integrity) |
| Performance | 10 | Performance Efficiency |
| Test Quality | 15 | Functional Suitability + Testability |
| Operational Readiness | 10 | Availability + Portability (DORA-readiness) |

Roughly **44 points mechanical** (tool-backed, bit-reproducible) and **56 points judged** (LLM, ISO-anchored, bounded drift via "inherit from prev entry" anchor).

## Install

```
/plugin marketplace add nekoguntai/skills
/plugin install grade@nekoguntai-skills
/reload-plugins
```

Then in any repo:

```
/grade:grade                    # full audit of the current repo at HEAD
/grade:grade --diff             # audit only files changed vs main/master
/grade:grade --diff origin/dev  # audit only files changed vs a specific base ref
/grade:grade-history            # show the trend timeline for this repo (full mode)
/grade:grade-history --diff     # show diff-mode history
/grade:grade-history --all      # show both
```

## Tool dependencies

The skill degrades gracefully when tools are missing — `unknown` signals surface in the report and confidence drops. For best results, install:

| Tool | Purpose | Install |
|---|---|---|
| [`lizard`](https://github.com/terryyin/lizard) | Cyclomatic complexity (McCabe / NIST / SonarQube) — 30+ languages | `pip install lizard` |
| [`jscpd`](https://github.com/kucherenko/jscpd) | Code duplication (SonarQube 3% default) — 150+ languages | `npm install -g jscpd` |
| [`gitleaks`](https://github.com/gitleaks/gitleaks) | Secret scanning (preferred over built-in regex fallback) | `brew install gitleaks` |
| [`ripgrep`](https://github.com/BurntSushi/ripgrep) | File listing + evidence grep | `brew install ripgrep` or `apt install ripgrep` |
| `jq` | Parses JSON output from audit tools | `brew install jq` or `apt install jq` |

Stack-specific tools (`npm`, `pytest`, `go`, `cargo`, `mvn`, `gradle`, `mix`, `composer`, `dotnet`, `rubocop`, etc.) are detected per-repo and skipped gracefully if not present.

## How it works

`/grade:grade` orchestrates four shell helpers:

- **`grade.sh`** — runs project-wide signal collection (native test/lint/typecheck/audit per detected stack, lizard complexity, jscpd duplication, gitleaks secrets, DORA enablers)
- **`diff_scan.sh`** — runs the same suite scoped to files changed against a base ref (for `--diff` mode)
- **`heuristics.sh`** — emits lightweight evidence counts for the LLM's judged criteria (resilience patterns, blocking I/O density, logging calls, etc.) — never used as direct score inputs
- **`trend.sh`** — manages the per-repo history JSONL files so runs can diff against prior entries

All shell scripts reference each other via `${CLAUDE_SKILL_DIR}` so they work whether installed as a plugin or dropped into `~/.claude/skills/` directly.

## History and trend tracking

Each run appends a JSON entry to `~/.claude/grade-history/<repo-slug>.jsonl` (full mode) or `<repo-slug>.diff.jsonl` (diff mode). The next run diffs against that to show:

- Overall score delta
- Grade and confidence transitions
- Per-domain deltas (only if ≥1 point moved)
- Signal-level deltas (what changed mechanically)

`/grade:grade` in full mode also short-circuits if HEAD matches the latest history entry and the working tree is clean — no point re-running the same audit.

History lives outside the plugin install directory so it persists across plugin updates. `/grade:grade-history` is a pure reporter — it reads the JSONL files and renders a timeline without re-auditing.

## License

MIT — see the repo-level [LICENSE](../../LICENSE).
