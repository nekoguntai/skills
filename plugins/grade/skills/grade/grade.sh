#!/usr/bin/env bash
# grade.sh — collect project-wide quality signals for the /grade skill.
#
# Emits raw human-readable output plus `SIGNAL: key=value` lines for the skill
# to parse deterministically. Every mechanical signal traces back to a specific
# tool + documented threshold (see standards.md).
#
# Design principles (see standards.md "Spirit"):
#  - Real tools before regex. Prefer lizard/jscpd/gitleaks over homebrewed patterns.
#  - No `||` fallback chains between tools — stack is detected up front, then the
#    correct tool is invoked. A failing `npm test` does NOT fall through to pytest.
#  - Every long-running tool is wrapped in `timeout` so a hung suite can't block
#    the whole audit. Exit 124 surfaces as `*_result=timeout`.
#  - Missing tool → emit `unknown` and let the skill lower confidence. Never
#    substitute a weaker signal silently.

set -u

# ==============================================================================
# Helpers
# ==============================================================================

section() { printf '\n=== %s ===\n' "$1"; }
signal()  { printf 'SIGNAL: %s=%s\n' "$1" "$2"; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }

GRADE_TIMEOUT="${GRADE_TIMEOUT:-120}"
timeout_wrap() {
  if has_cmd timeout; then
    timeout "$GRADE_TIMEOUT" "$@"
  else
    "$@"
  fi
}
classify_rc() {
  case "$1" in
    0)   echo pass ;;
    124) echo timeout ;;
    *)   echo fail ;;
  esac
}
# Returns 0 if any file in the repo matches the glob (for stack detection).
files_exist() {
  if has_cmd rg; then
    rg --files -g "$1" 2>/dev/null | head -1 | grep -q .
  else
    find . -type f -name "${1#*/}" 2>/dev/null | head -1 | grep -q .
  fi
}

# ==============================================================================
# Stack detection
# ==============================================================================

section "STACK"
has_node=false; has_python=false; has_go=false; has_rust=false
has_java=false; has_kotlin=false; has_ruby=false; has_php=false
has_elixir=false; has_swift=false; has_dotnet=false; has_scala=false

[ -f package.json ]    && has_node=true
{ [ -f pyproject.toml ] || [ -f setup.py ] || [ -f requirements.txt ]; } && has_python=true
[ -f go.mod ]          && has_go=true
[ -f Cargo.toml ]      && has_rust=true
{ [ -f pom.xml ] || [ -f build.gradle ] || [ -f build.gradle.kts ]; } && has_java=true
files_exist '*.kt'     && has_kotlin=true
[ -f Gemfile ]         && has_ruby=true
[ -f composer.json ]   && has_php=true
[ -f mix.exs ]         && has_elixir=true
[ -f Package.swift ]   && has_swift=true
{ files_exist '*.csproj' || files_exist '*.fsproj' || [ -f global.json ]; } && has_dotnet=true
[ -f build.sbt ]       && has_scala=true

echo "node=$has_node python=$has_python go=$has_go rust=$has_rust"
echo "java=$has_java kotlin=$has_kotlin ruby=$has_ruby php=$has_php"
echo "elixir=$has_elixir swift=$has_swift dotnet=$has_dotnet scala=$has_scala"

signal stack_node    "$has_node"
signal stack_python  "$has_python"
signal stack_go      "$has_go"
signal stack_rust    "$has_rust"
signal stack_java    "$has_java"
signal stack_kotlin  "$has_kotlin"
signal stack_ruby    "$has_ruby"
signal stack_php     "$has_php"
signal stack_elixir  "$has_elixir"
signal stack_swift   "$has_swift"
signal stack_dotnet  "$has_dotnet"
signal stack_scala   "$has_scala"

# ==============================================================================
# Tests (ISO 25010: Functional Correctness)
# ==============================================================================

section "TESTS"
tests_result=missing
if $has_node && has_cmd jq && jq -e '.scripts.test' package.json >/dev/null 2>&1; then
  timeout_wrap npm test 2>&1; tests_result=$(classify_rc $?)
elif $has_python && has_cmd pytest; then
  timeout_wrap pytest 2>&1; tests_result=$(classify_rc $?)
elif $has_go; then
  timeout_wrap go test ./... 2>&1; tests_result=$(classify_rc $?)
elif $has_rust; then
  timeout_wrap cargo test 2>&1; tests_result=$(classify_rc $?)
elif $has_java && has_cmd mvn && [ -f pom.xml ]; then
  timeout_wrap mvn -q test 2>&1; tests_result=$(classify_rc $?)
elif $has_java && has_cmd gradle; then
  timeout_wrap gradle -q test 2>&1; tests_result=$(classify_rc $?)
elif $has_ruby && has_cmd bundle; then
  timeout_wrap bundle exec rspec 2>&1; tests_result=$(classify_rc $?)
elif $has_php && has_cmd composer && [ -f vendor/bin/phpunit ]; then
  timeout_wrap vendor/bin/phpunit 2>&1; tests_result=$(classify_rc $?)
elif $has_elixir && has_cmd mix; then
  timeout_wrap mix test 2>&1; tests_result=$(classify_rc $?)
elif $has_dotnet && has_cmd dotnet; then
  timeout_wrap dotnet test --nologo 2>&1; tests_result=$(classify_rc $?)
elif $has_swift && has_cmd swift; then
  timeout_wrap swift test 2>&1; tests_result=$(classify_rc $?)
elif $has_scala && has_cmd sbt; then
  timeout_wrap sbt test 2>&1; tests_result=$(classify_rc $?)
else
  echo "(no recognized test runner for detected stack)"
fi
signal tests "$tests_result"
signal tests_scope project

# ==============================================================================
# Lint (ISO 25010: Functional Correctness / fit for purpose)
# ==============================================================================

section "LINT"
lint_result=missing
if $has_node && has_cmd jq && jq -e '.scripts.lint' package.json >/dev/null 2>&1; then
  timeout_wrap npm run lint 2>&1; lint_result=$(classify_rc $?)
elif $has_python && has_cmd ruff; then
  timeout_wrap ruff check . 2>&1; lint_result=$(classify_rc $?)
elif $has_python && has_cmd flake8; then
  timeout_wrap flake8 2>&1; lint_result=$(classify_rc $?)
elif $has_go && has_cmd golangci-lint; then
  timeout_wrap golangci-lint run 2>&1; lint_result=$(classify_rc $?)
elif $has_rust; then
  timeout_wrap cargo clippy -- -D warnings 2>&1; lint_result=$(classify_rc $?)
elif $has_java && has_cmd mvn; then
  timeout_wrap mvn -q checkstyle:check 2>&1; lint_result=$(classify_rc $?)
elif $has_kotlin && has_cmd ktlint; then
  timeout_wrap ktlint 2>&1; lint_result=$(classify_rc $?)
elif $has_ruby && has_cmd rubocop; then
  timeout_wrap rubocop 2>&1; lint_result=$(classify_rc $?)
elif $has_php && has_cmd phpstan; then
  timeout_wrap phpstan analyse 2>&1; lint_result=$(classify_rc $?)
elif $has_elixir && has_cmd mix; then
  timeout_wrap mix credo 2>&1; lint_result=$(classify_rc $?)
elif $has_dotnet && has_cmd dotnet; then
  timeout_wrap dotnet format --verify-no-changes 2>&1; lint_result=$(classify_rc $?)
elif $has_swift && has_cmd swiftlint; then
  timeout_wrap swiftlint 2>&1; lint_result=$(classify_rc $?)
else
  echo "(no recognized linter for detected stack)"
fi
signal lint "$lint_result"
signal lint_scope project

# ==============================================================================
# Typecheck (ISO 25010: Functional Correctness)
# ==============================================================================

section "TYPECHECK"
typecheck_result=missing
if $has_node && [ -f tsconfig.json ]; then
  timeout_wrap npx --no-install tsc --noEmit 2>&1; typecheck_result=$(classify_rc $?)
elif $has_python && has_cmd mypy; then
  timeout_wrap mypy . 2>&1; typecheck_result=$(classify_rc $?)
elif $has_go; then
  timeout_wrap go vet ./... 2>&1; typecheck_result=$(classify_rc $?)
elif $has_rust; then
  timeout_wrap cargo check 2>&1; typecheck_result=$(classify_rc $?)
elif $has_java && has_cmd mvn; then
  timeout_wrap mvn -q compile 2>&1; typecheck_result=$(classify_rc $?)
elif $has_dotnet && has_cmd dotnet; then
  timeout_wrap dotnet build --nologo 2>&1; typecheck_result=$(classify_rc $?)
elif $has_elixir && has_cmd mix; then
  timeout_wrap mix compile --warnings-as-errors 2>&1; typecheck_result=$(classify_rc $?)
else
  echo "(no typecheck available for detected stack)"
fi
signal typecheck "$typecheck_result"
signal typecheck_scope project

# ==============================================================================
# Coverage (ISO 25010: Testability)
# Raw output only — coverage % is parsed heuristically by the /grade skill from
# the tool-specific format (not a SIGNAL because formats vary widely).
# ==============================================================================

section "COVERAGE"
if $has_node && has_cmd jq && jq -e '.scripts.coverage' package.json >/dev/null 2>&1; then
  timeout_wrap npm run coverage 2>&1 || true
elif $has_python && has_cmd pytest; then
  timeout_wrap pytest --cov 2>&1 || true
elif $has_go; then
  timeout_wrap go test -cover ./... 2>&1 || true
elif $has_rust && has_cmd cargo-tarpaulin; then
  timeout_wrap cargo tarpaulin --print-summary 2>&1 || true
else
  echo "(no coverage tool available for detected stack)"
fi

# ==============================================================================
# Dependency vulnerabilities (OWASP Top 10 A06 — CVSS ≥7.0 high/critical)
# ==============================================================================

section "SECURITY"
security_high=unknown
if $has_node && has_cmd npm; then
  timeout_wrap npm audit --audit-level=high 2>&1 || true
  if has_cmd jq; then
    security_high=$(timeout_wrap npm audit --json 2>/dev/null \
      | jq '(.metadata.vulnerabilities.high // 0) + (.metadata.vulnerabilities.critical // 0)' 2>/dev/null \
      || echo unknown)
  fi
elif $has_python && has_cmd pip-audit; then
  pip_audit_out=$(timeout_wrap pip-audit 2>&1 || true)
  echo "$pip_audit_out"
  # pip-audit prints one line per vulnerable package; count lines after the header
  security_high=$(echo "$pip_audit_out" | grep -cE '^\S+\s+\S+\s+\S+\s+PYSEC' || echo 0)
elif $has_rust && has_cmd cargo-audit; then
  cargo_audit_out=$(timeout_wrap cargo audit 2>&1 || true)
  echo "$cargo_audit_out"
  security_high=$(echo "$cargo_audit_out" | grep -cE '^Crate:' || echo 0)
elif $has_go && has_cmd govulncheck; then
  gv_out=$(timeout_wrap govulncheck ./... 2>&1 || true)
  echo "$gv_out"
  security_high=$(echo "$gv_out" | grep -cE '^Vulnerability #' || echo 0)
elif $has_ruby && has_cmd bundler-audit; then
  ba_out=$(timeout_wrap bundler-audit check 2>&1 || true)
  echo "$ba_out"
  security_high=$(echo "$ba_out" | grep -cE '^Criticality: (High|Critical)' || echo 0)
elif $has_php && has_cmd composer; then
  timeout_wrap composer audit 2>&1 || true
elif $has_dotnet && has_cmd dotnet; then
  dn_out=$(timeout_wrap dotnet list package --vulnerable --include-transitive 2>&1 || true)
  echo "$dn_out"
  security_high=$(echo "$dn_out" | grep -cE '>\s*\S+\s+\S+\s+\S+\s+(High|Critical)' || echo 0)
else
  echo "(no dependency audit tool available for detected stack)"
fi
signal security_high "$security_high"
signal security_scope project

# ==============================================================================
# Secrets (OWASP A07, CWE-798) — prefer gitleaks, fall back to regex.
# ==============================================================================

section "SECRETS"
secret_hits=0
secret_tool=none
if has_cmd gitleaks; then
  secret_tool=gitleaks
  gl_report=$(mktemp)
  timeout_wrap gitleaks detect --source . --no-git --redact \
    --report-format json --report-path "$gl_report" >/dev/null 2>&1 || true
  if [ -s "$gl_report" ] && has_cmd jq; then
    secret_hits=$(jq 'length' "$gl_report" 2>/dev/null || echo unknown)
  elif [ -s "$gl_report" ]; then
    # JSON exists but no jq — assume at least 1 if file is non-empty JSON array
    secret_hits=$(grep -c '"RuleID"' "$gl_report" 2>/dev/null || echo unknown)
  else
    secret_hits=0
  fi
  rm -f "$gl_report"
elif has_cmd rg; then
  secret_tool=rg-fallback
  secret_hits=$(rg -c --no-messages \
    -e 'AKIA[0-9A-Z]{16}' \
    -e 'sk-[A-Za-z0-9]{20,}' \
    -e 'ghp_[A-Za-z0-9]{36}' \
    -e 'xox[baprs]-[A-Za-z0-9-]{10,}' \
    -e '-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----' \
    --glob '!.git/' --glob '!node_modules/' --glob '!vendor/' 2>/dev/null \
    | awk -F: '{sum+=$NF} END {print sum+0}')
else
  secret_hits=unknown
  echo "(neither gitleaks nor ripgrep available — cannot scan for secrets)"
fi
echo "secret_tool=$secret_tool secret_hits=$secret_hits"
signal secrets "$secret_hits"
signal secrets_tool "$secret_tool"
signal secrets_scope project

# ==============================================================================
# Cyclomatic complexity (McCabe / NIST SP 500-235 / SonarQube) — lizard
# ==============================================================================

section "COMPLEXITY"
lizard_warning_count=unknown
lizard_avg_ccn=unknown
lizard_max_ccn=unknown
if has_cmd lizard; then
  lizard_full=$(timeout_wrap lizard . 2>/dev/null || true)
  echo "$lizard_full" | tail -25
  # Warning count: functions exceeding CCN 15 (lizard default)
  lizard_warning_count=$(timeout_wrap lizard -w . 2>/dev/null | grep -c "warning:" || echo 0)
  # Average CCN: parse the summary "Total" row
  # Last line with format: "<total_nloc> <avg_nloc> <avg_ccn> <avg_token> <fun_cnt> <warn_cnt> <fun_rt> <nloc_rt>"
  lizard_avg_ccn=$(echo "$lizard_full" \
    | awk '/^[[:space:]]*[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+/ {ccn=$3} END {print (ccn=="" ? "unknown" : ccn)}')
else
  echo "(lizard not installed — complexity scoring will be judged, not measured)"
  echo "Install: pip install lizard"
fi
signal lizard_warning_count "$lizard_warning_count"
signal lizard_avg_ccn        "$lizard_avg_ccn"
signal lizard_max_ccn        "$lizard_max_ccn"
signal complexity_scope project

# ==============================================================================
# Duplication (SonarQube default 3% threshold) — jscpd
# ==============================================================================

section "DUPLICATION"
duplication_pct=unknown
if has_cmd jscpd; then
  jscpd_dir=$(mktemp -d)
  timeout_wrap jscpd --silent --reporters json --output "$jscpd_dir" . >/dev/null 2>&1 || true
  if [ -f "$jscpd_dir/jscpd-report.json" ] && has_cmd jq; then
    duplication_pct=$(jq -r '.statistics.total.percentage // "unknown"' "$jscpd_dir/jscpd-report.json" 2>/dev/null || echo unknown)
    echo "duplication_pct=$duplication_pct%"
  else
    echo "(jscpd ran but produced no report — treating as unknown)"
  fi
  rm -rf "$jscpd_dir"
else
  echo "(jscpd not installed — duplication scoring will be judged, not measured)"
  echo "Install: npm install -g jscpd"
fi
signal duplication_pct "$duplication_pct"
signal duplication_scope project

# ==============================================================================
# File sizes (god-file detection)
# ==============================================================================

section "FILE SIZES (top 10)"
largest_file_lines=0
if has_cmd rg; then
  tmp=$(rg --files \
    -g '*.ts' -g '*.tsx' -g '*.js' -g '*.jsx' -g '*.mjs' -g '*.cjs' \
    -g '*.py' -g '*.go' -g '*.rs' \
    -g '*.java' -g '*.kt' -g '*.scala' \
    -g '*.rb' -g '*.php' -g '*.ex' -g '*.exs' \
    -g '*.cs' -g '*.fs' -g '*.vb' \
    -g '*.swift' -g '*.cpp' -g '*.cc' -g '*.c' -g '*.h' -g '*.hpp' \
    2>/dev/null \
    | while IFS= read -r f; do wc -l "$f" 2>/dev/null; done \
    | sort -rn)
  echo "$tmp" | head -10
  largest_file_lines=$(echo "$tmp" | head -1 | awk '{print $1+0}')
else
  find . -type f \( \
      -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \
      -o -name '*.py' -o -name '*.go' -o -name '*.rs' \
      -o -name '*.java' -o -name '*.kt' -o -name '*.rb' -o -name '*.php' \
      -o -name '*.ex' -o -name '*.exs' -o -name '*.cs' -o -name '*.swift' \
      -o -name '*.cpp' -o -name '*.c' -o -name '*.h' \
    \) \
    -not -path './.git/*' -not -path './node_modules/*' -not -path './vendor/*' \
    -print0 2>/dev/null \
    | xargs -0 wc -l 2>/dev/null \
    | sort -rn \
    | head -11
fi
signal largest_file_lines "$largest_file_lines"
signal largest_file_lines_scope project

# ==============================================================================
# DORA-readiness / Operational Readiness enablers
# ==============================================================================

section "OPERATIONAL READINESS ENABLERS"

# Deployment artifacts
deploy_artifact_count=0
has_dockerfile=false; has_compose=false; has_k8s=false
has_ci_github=false; has_ci_gitlab=false; has_ci_circle=false
has_ci_jenkins=false; has_ci_azure=false

[ -f Dockerfile ] && has_dockerfile=true && deploy_artifact_count=$((deploy_artifact_count + 1))
{ [ -f docker-compose.yml ] || [ -f docker-compose.yaml ]; } && has_compose=true
{ [ -d k8s ] || [ -d kubernetes ] || [ -d helm ] || [ -d charts ]; } && has_k8s=true && deploy_artifact_count=$((deploy_artifact_count + 1))

[ -d .github/workflows ] && has_ci_github=true
[ -f .gitlab-ci.yml ]    && has_ci_gitlab=true
[ -d .circleci ]         && has_ci_circle=true
[ -f Jenkinsfile ]       && has_ci_jenkins=true
[ -f azure-pipelines.yml ] && has_ci_azure=true
if $has_ci_github || $has_ci_gitlab || $has_ci_circle || $has_ci_jenkins || $has_ci_azure; then
  deploy_artifact_count=$((deploy_artifact_count + 1))
fi

echo "dockerfile=$has_dockerfile compose=$has_compose k8s=$has_k8s"
echo "ci: github=$has_ci_github gitlab=$has_ci_gitlab circle=$has_ci_circle jenkins=$has_ci_jenkins azure=$has_ci_azure"
signal has_dockerfile       "$has_dockerfile"
signal has_compose          "$has_compose"
signal has_k8s              "$has_k8s"
signal has_ci               "$( { $has_ci_github || $has_ci_gitlab || $has_ci_circle || $has_ci_jenkins || $has_ci_azure; } && echo true || echo false)"
signal deploy_artifact_count "$deploy_artifact_count"

# ==============================================================================
# Heuristic evidence (for LLM judgment — NOT direct score inputs)
# ==============================================================================

# Build a project-wide file list for the heuristics helper.
heuristics_files=$(mktemp)
trap 'rm -f "$heuristics_files"' EXIT
if has_cmd rg; then
  rg --files \
    -g '*.ts' -g '*.tsx' -g '*.js' -g '*.jsx' -g '*.mjs' -g '*.cjs' \
    -g '*.py' -g '*.go' -g '*.rs' \
    -g '*.java' -g '*.kt' -g '*.scala' \
    -g '*.rb' -g '*.php' -g '*.ex' -g '*.exs' \
    -g '*.cs' -g '*.fs' \
    -g '*.swift' -g '*.cpp' -g '*.cc' -g '*.c' -g '*.h' -g '*.hpp' \
    2>/dev/null > "$heuristics_files" || true
fi

HEUR="$(dirname "$0")/heuristics.sh"
if [ -x "$HEUR" ] && [ -s "$heuristics_files" ]; then
  bash "$HEUR" "$heuristics_files"
else
  echo "(heuristics.sh missing or no source files found — skipping evidence collection)" >&2
fi

echo
echo "=== DONE ==="
