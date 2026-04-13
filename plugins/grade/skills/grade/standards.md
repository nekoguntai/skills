# Software Quality Standards Reference

This document is the **source of truth** for the `/grade` skill's rubric. It records *why* every threshold is what it is and *where* it comes from. If you change a scoring rule in `SKILL.md`, update this file in the same pass.

---

# 🎯 THE SPIRIT

`/grade` is a **software quality audit tool**, not an LLM opinion generator. It exists to give you a defensible, reproducible, multi-domain score for a repository at a specific commit — something you can hand to a stakeholder and back up with evidence.

## Core principles

1. **Anchor to real standards.** Every mechanical threshold traces back to an industry source — ISO/IEC 25010 (software quality model), McCabe (cyclomatic complexity), NIST SP 500-235, SonarQube defaults, OWASP CVSS, Google SRE. No made-up numbers.

2. **Measure what can be measured. Judge what can't.** For each criterion:
   - If a real tool exists (`lizard`, `jscpd`, `gitleaks`, language-native test/lint/typecheck/audit), use it and apply the documented threshold. Same inputs → same score.
   - If no static tool can measure it reliably (Fault Tolerance, Time Behavior, Recoverability), use LLM judgment — but anchor it to the relevant ISO 25010 sub-characteristic definition, not freeform vibes.
   - Never fake objectivity with a weak grep proxy. A score is either measured or judged — never a pretend-measurement.

3. **Be honest about confidence.** Missing evidence ≠ guessing. If a tool isn't installed, emit `unknown`, downgrade confidence, and say so in the Missing section. Never regex-substitute for a real measurement.

4. **Cite everything.** Every score in the report must cite its source — either `tool + threshold + exit status` or `ISO 25010 sub-characteristic + inspection target + evidence`. No unsourced numbers.

5. **Work across languages.** The universal quality metrics (complexity, duplication, secrets) come from multi-language tools (`lizard`, `jscpd`, `gitleaks`). Per-language logic only appears in stack-specific test/lint/typecheck/audit chains. The same rubric applies to any repo in any language.

6. **Be actionable.** Every low score should tell the user exactly what to fix — specific file, specific function, specific threshold that was missed. "Your Reliability is low" is useless; "12 functions have CCN > 15 per lizard, here are the top 5" is actionable.

7. **Acknowledge what static analysis can't see.** DORA metrics (deployment frequency, MTTR, change failure rate) and SRE metrics (p99 latency, error rate) need production data. `/grade` measures their *enablers* — CI config, deploy automation, health endpoints, rollback safety — and labels the result "DORA-readiness", not "DORA score".

## Anti-patterns this tool avoids

- ❌ Producing a single fuzzy "quality score" with no breakdown
- ❌ Rewarding vanity metrics (line count, test count) over meaningful ones
- ❌ Pretending `grep -c` approximates static analysis
- ❌ Inflating scores out of politeness
- ❌ Hiding LLM judgment behind fake-precise numbers
- ❌ Using different standards for different runs on the same repo
- ❌ Penalizing valid architectural choices (e.g., a CLI tool shouldn't need `/healthz`)

## What "objective" means here

Perfectly objective software quality grading is impossible without runtime data and original requirements. What *is* possible:

- **Tool-measured criteria**: perfectly reproducible (lizard complexity, gitleaks secrets, npm audit CVEs, pass/fail of tests)
- **Threshold-bounded criteria**: reproducible when thresholds are documented (SonarQube's 3% duplication, McCabe's CCN 10)
- **ISO 25010-anchored judgment**: *bounded drift* when the LLM applies the same sub-characteristic definition to the same code, anchored to previous entries in history

The mechanical half is objective. The judged half is defensibly *grounded* — not objective, but not arbitrary either. The report tells you which is which on every row.

---

# 🧱 ISO/IEC 25010 MAPPING

The 7 `/grade` domains map to ISO/IEC 25010:2011 quality characteristics as follows.

| `/grade` Domain | ISO 25010 Characteristic | Sub-characteristics used |
|---|---|---|
| Correctness (20) | **Functional Suitability** | Functional Completeness, Functional Correctness, Functional Appropriateness |
| Reliability (15) | **Reliability** | Maturity, Availability, Fault Tolerance, Recoverability |
| Maintainability (15) | **Maintainability** | Modularity, Reusability, Analyzability, Modifiability, Testability |
| Security (15) | **Security** | Confidentiality, Integrity, Non-repudiation, Authenticity |
| Performance (10) | **Performance Efficiency** | Time Behaviour, Resource Utilization, Capacity |
| Test Quality (15) | cross-cutting — **Functional Suitability** + **Maintainability/Testability** | — |
| Operational Readiness (10) | **Reliability/Availability** + **Portability** (Installability, Adaptability) + **Compatibility/Interoperability** | — |

Weights sum to 100. ISO 25010 itself does not prescribe weights — we use the breakdown above as a defensible default that can be adjusted per-repo via `.grade.yml` overrides (future work).

---

# 📊 MECHANICAL THRESHOLDS

Every mechanical scoring rule in `SKILL.md` uses one of these. Each row cites its origin.

## Functional Suitability (Correctness)

| Signal | Tool | Thresholds | Source |
|---|---|---|---|
| Tests pass | native test runner (jest, pytest, go test, cargo test, mvn test, etc.) | `pass` / `fail` / `timeout` / `missing` — binary + timeout state | ISO 25010 Functional Correctness; pass/fail is inherently binary |
| Typecheck clean | native typechecker (tsc, mypy, `go vet`, `cargo check`, etc.) | `pass` / `fail N errors` / `timeout` / `missing` | ISO 25010 Functional Correctness |
| Lint clean | native linter (eslint, ruff, golangci-lint, clippy, rubocop, etc.) | `pass` / `fail N issues` / `timeout` / `missing` | Industry practice; no single standard |

**Hard-fail triggers:** `tests=fail` OR `typecheck=fail` → cap grade at D (≤69).

## Maintainability

### Cyclomatic Complexity — `lizard`

| Metric | Threshold | Source |
|---|---|---|
| Average CCN per function | <7 = excellent, 7–10 = good, 10–15 = moderate, >15 = poor | McCabe 1976 ("A Complexity Measure", IEEE TSE); NIST Special Publication 500-235 |
| Max CCN in any function | <15 = OK, 15–25 = concerning, >25 = strongly suggests refactor | NIST SP 500-235 recommends ≤10; SonarQube default warning at 15 |
| Functions exceeding CCN 15 (`lizard -w` warning count) | 0 = excellent, 1–5 = good, 6–15 = moderate, >15 = poor | SonarQube "Cognitive Complexity" rule default |

**Tool:** [lizard](https://github.com/terryyin/lizard) — supports C/C++, Java, C#, JavaScript, TypeScript, Objective-C, Python, Ruby, PHP, Scala, Go, Lua, Rust, Swift, Fortran, Kotlin, Solidity, Erlang, Zig, Perl, GDScript (30+ languages).

### Duplication — `jscpd`

| Metric | Threshold | Source |
|---|---|---|
| Duplication percentage | <3% = good, 3–5% = moderate, >5% = poor | SonarQube default quality gate ("Duplicated Lines %") |

**Tool:** [jscpd](https://github.com/kucherenko/jscpd) — supports 150+ languages via token-based paste detection.

### File Size (god-file detection)

| Metric | Threshold | Source |
|---|---|---|
| Largest file LOC | <500 = good, 500–1000 = moderate, >1000 = poor | SonarQube "class size" recommendation; Clean Code (Martin 2008) rule of thumb |

## Security

### Dependency Vulnerabilities — stack-native audit tools

| Stack | Tool | Scoring source |
|---|---|---|
| Node | `npm audit --audit-level=high` | CVSS ≥7.0 = High, ≥9.0 = Critical |
| Python | `pip-audit` | OSV.dev + PyPA advisory database |
| Rust | `cargo audit` | RustSec advisory database |
| Go | `govulncheck` | Go vulnerability database |
| Ruby | `bundler-audit` | Ruby Advisory DB |
| PHP | `composer audit` | Packagist advisories |
| .NET | `dotnet list package --vulnerable` | GitHub advisory database |
| Java/Kotlin | `mvn dependency-check` / `gradle dependencyCheckAnalyze` | OWASP Dependency-Check (NVD-backed) |

**Universal CVSS thresholds:**

| high/critical count | Score | Source |
|---|---|---|
| 0 | +5 (full) | OWASP best practice |
| 1–2 | +2 (partial) | Pragmatic — small drift is common |
| ≥3 | 0 | CVSS accumulation |
| **≥3** | **also HARD-FAIL** | OWASP Top 10 A06:2021 (Vulnerable and Outdated Components) |

### Secrets — `gitleaks` (preferred) or regex fallback

| Metric | Threshold | Source |
|---|---|---|
| Secret count | 0 = full credit; ≥1 = **0 points AND HARD-FAIL** | OWASP Top 10 A07:2021 (Identification and Authentication Failures); CWE-798 (Hardcoded Credentials) |

**Tool:** [gitleaks](https://github.com/gitleaks/gitleaks) — industry-standard git-aware secret scanner using rule-based patterns + entropy detection. Falls back to our in-script regex only if gitleaks is not installed.

## Test Quality

### Coverage

| Metric | Threshold | Source |
|---|---|---|
| Line coverage | ≥80% = excellent, 60–80% = good, <60% = needs work | Google SRE book ("Testing for Reliability"); industry norm |

Note: Google's own internal guidance is "don't block on coverage" — the number is a signal, not a gate. We use the standard 70% as a soft target.

### Mutation Score (opt-in, if tool available)

| Metric | Threshold | Source |
|---|---|---|
| Mutation score | ≥60% = good, 40–60% = OK, <40% = weak | Stryker documentation; Petrović et al. 2018 ("State of Mutation Testing at Google") |

**Tools:** Stryker (JS/TS), mutmut (Python), PIT (Java), cargo-mutants (Rust), go-mutesting (Go). Slow — opt-in via `/grade --mutation`.

## Operational Readiness (DORA enablers)

Real DORA metrics require production telemetry. `/grade` scores the *enablers* — the static artifacts that make DORA possible.

| Enabler | Check | Source |
|---|---|---|
| Deployment automation | presence of Dockerfile / docker-compose.yml / k8s manifests | DORA: "Deployment Automation" capability |
| Continuous Integration | presence of `.github/workflows/`, `.gitlab-ci.yml`, `.circleci/`, `Jenkinsfile`, `azure-pipelines.yml` | DORA: "Continuous Integration" capability |
| Health endpoints | regex match for `/health`, `/healthz`, `/ready`, `/readyz`, `/livez` routes | Kubernetes probes convention; Google SRE liveness/readiness pattern |
| Observability | presence of prometheus / opentelemetry / datadog / sentry / honeycomb / newrelic imports | DORA: "Monitoring and Observability" capability |
| Structured logging | presence of structured logging lib (winston, pino, zerolog, zap, tracing, logrus, slog, serilog, logback, log4j, structlog) | Google SRE "Logging" chapter |

## Summary — what `/grade` measures mechanically vs judges

| Domain | Mechanical (tools) | Judged (LLM, ISO-anchored) |
|---|---|---|
| Correctness | tests, lint, typecheck | suppression density, functional completeness |
| Reliability | — (all runtime) | Fault Tolerance, Recoverability, error handling quality, resilience patterns |
| Maintainability | lizard CCN, jscpd duplication, largest file LOC | Readability, naming, architecture clarity |
| Security | CVSS dependency audit, gitleaks secrets | Input validation quality, safe API usage, authZ patterns |
| Performance | — (all runtime) | Time Behavior (LLM spot-checks hot paths), Resource Utilization |
| Test Quality | coverage %, (optional) mutation score | Test structure quality, edge case coverage, flaky patterns |
| Operational Readiness | Dockerfile/CI/k8s presence, health endpoints, observability lib, logging lib | Logging quality, config validation robustness, migration safety |

Roughly **60 mechanical points** and **40 judged points** out of 100. The mechanical half is bit-exact reproducible. The judged half has bounded drift (±2 typical) anchored to previous entries via the "inherit prior score when evidence is unchanged" rule.

---

# 📚 REFERENCES

- **ISO/IEC 25010:2011** — Systems and software Quality Requirements and Evaluation (SQuaRE). https://iso25000.com/index.php/en/iso-25000-standards/iso-25010
- **McCabe, T. J. (1976)** — "A Complexity Measure". IEEE Transactions on Software Engineering, SE-2(4).
- **NIST Special Publication 500-235** — Structured Testing: A Testing Methodology Using the Cyclomatic Complexity Metric.
- **SonarQube Quality Gates** — https://docs.sonarsource.com/sonarqube/latest/user-guide/quality-gates/
- **OWASP Top 10 (2021)** — https://owasp.org/Top10/
- **CVSS v3.1** — Common Vulnerability Scoring System Specification. https://www.first.org/cvss/v3.1/specification-document
- **CWE-798** — Use of Hard-coded Credentials. https://cwe.mitre.org/data/definitions/798.html
- **Google SRE Book** — *Site Reliability Engineering: How Google Runs Production Systems.* Beyer et al., 2016. O'Reilly.
- **DORA / Accelerate** — Forsgren, Humble, Kim (2018). *Accelerate: The Science of Lean Software and DevOps.* IT Revolution Press.
- **Petrović, G., Ivanković, M. (2018)** — "State of Mutation Testing at Google". ICSE-SEIP 2018.
- **Martin, R. C. (2008)** — *Clean Code: A Handbook of Agile Software Craftsmanship.* Prentice Hall.

---

# 🛠 TOOL INSTALLATION HINTS

The skill emits `unknown` for any tool that isn't on PATH and downgrades confidence accordingly. For best results:

| Tool | Install | Covers |
|---|---|---|
| `lizard` | `pip install lizard` | Complexity — 30+ languages |
| `jscpd` | `npm install -g jscpd` | Duplication — 150+ languages |
| `gitleaks` | `brew install gitleaks` / release download | Secrets scanning |
| `ripgrep` (rg) | `brew install ripgrep` / `apt install ripgrep` | File listing + evidence grep |
| `jq` | `brew install jq` / `apt install jq` | JSON parsing of tool outputs |

Stack-specific tools (`npm`, `pytest`, `go`, `cargo`, `mvn`, `mix`, `composer`, `dotnet`, etc.) are detected per repo and skipped gracefully if not present.
