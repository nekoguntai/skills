#!/usr/bin/env bash
# diff_scan.sh — emit diff-scoped quality signals for a given file list.
#
# Called by the /grade skill in diff mode (`/grade --diff <base>`) to score
# only files changed between HEAD and a base ref. Mirrors grade.sh's signal
# format, but every signal emitted here is tagged `*_scope=diff` so the skill
# can merge diff-scoped signals over the project-wide equivalents.
#
# Not in scope (by design — always project-wide via grade.sh):
#   - tests (a failing test elsewhere still fails)
#   - typecheck (needs cross-file context)
#   - coverage (only meaningful in aggregate)
#   - dependency audit (package-level, not file-level)
#   - deploy artifacts / CI presence (filesystem-level)
#
# In scope (diff-scoped):
#   - lint (scoped to changed files if tool supports it)
#   - secrets (gitleaks on changed files)
#   - complexity (lizard on changed files)
#   - duplication (jscpd on changed files)
#   - file sizes (changed files only)
#   - all heuristic evidence signals (scoped via heuristics.sh)

set -u

files_path="${1:?usage: diff_scan.sh <file_list>}"
if [ ! -f "$files_path" ]; then
  echo "error: file list not found: $files_path" >&2
  exit 1
fi

GRADE_TIMEOUT="${GRADE_TIMEOUT:-120}"
section() { printf '\n=== %s ===\n' "$1"; }
signal()  { printf 'SIGNAL: %s=%s\n' "$1" "$2"; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }
timeout_wrap() {
  if has_cmd timeout; then timeout "$GRADE_TIMEOUT" "$@"
  else "$@"; fi
}
classify_rc() {
  case "$1" in 0) echo pass ;; 124) echo timeout ;; *) echo fail ;; esac
}

section "DIFF SCOPE"
file_count=$(grep -cv '^$' "$files_path" 2>/dev/null || echo 0)
echo "changed_files=$file_count"
signal diff_file_count "$file_count"

# Language-specific subsets for lint scoping
py_files=$(grep -E '\.py$'                        "$files_path" 2>/dev/null || true)
ts_files=$(grep -E '\.(ts|tsx|js|jsx|mjs|cjs)$'   "$files_path" 2>/dev/null || true)
go_files=$(grep -E '\.go$'                        "$files_path" 2>/dev/null || true)
rs_files=$(grep -E '\.rs$'                        "$files_path" 2>/dev/null || true)
java_files=$(grep -E '\.java$'                    "$files_path" 2>/dev/null || true)
kt_files=$(grep -E '\.kt$'                        "$files_path" 2>/dev/null || true)
rb_files=$(grep -E '\.rb$'                        "$files_path" 2>/dev/null || true)

# ==============================================================================
# Lint (diff-scoped)
# ==============================================================================
section "LINT (diff-scoped)"
lint_result=missing
if [ -n "$py_files" ] && has_cmd ruff; then
  mapfile -t arr <<< "$py_files"
  timeout_wrap ruff check "${arr[@]}" 2>&1; lint_result=$(classify_rc $?)
elif [ -n "$py_files" ] && has_cmd flake8; then
  mapfile -t arr <<< "$py_files"
  timeout_wrap flake8 "${arr[@]}" 2>&1; lint_result=$(classify_rc $?)
elif [ -n "$ts_files" ] && has_cmd npx; then
  mapfile -t arr <<< "$ts_files"
  timeout_wrap npx --no-install eslint "${arr[@]}" 2>&1; lint_result=$(classify_rc $?)
elif [ -n "$go_files" ] && has_cmd golangci-lint; then
  timeout_wrap golangci-lint run 2>&1; lint_result=$(classify_rc $?)
elif [ -n "$rs_files" ]; then
  timeout_wrap cargo clippy -- -D warnings 2>&1; lint_result=$(classify_rc $?)
elif [ -n "$rb_files" ] && has_cmd rubocop; then
  mapfile -t arr <<< "$rb_files"
  timeout_wrap rubocop "${arr[@]}" 2>&1; lint_result=$(classify_rc $?)
else
  echo "(no lintable files in diff or no linter available)"
fi
signal lint "$lint_result"
signal lint_scope diff

# ==============================================================================
# Secrets (diff-scoped) — prefer gitleaks
# ==============================================================================
section "SECRETS (diff-scoped)"
secret_hits=0
secret_tool=none
if has_cmd gitleaks; then
  secret_tool=gitleaks
  # gitleaks doesn't take a file list directly; run on each path
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    gl_report=$(mktemp)
    timeout_wrap gitleaks detect --source "$f" --no-git --redact \
      --report-format json --report-path "$gl_report" >/dev/null 2>&1 || true
    if [ -s "$gl_report" ] && has_cmd jq; then
      hits=$(jq 'length' "$gl_report" 2>/dev/null || echo 0)
      secret_hits=$((secret_hits + hits))
    fi
    rm -f "$gl_report"
  done < "$files_path"
elif has_cmd rg; then
  secret_tool=rg-fallback
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -f "$f" ] || continue
    hits=$(rg -c --no-messages \
      -e 'AKIA[0-9A-Z]{16}' \
      -e 'sk-[A-Za-z0-9]{20,}' \
      -e 'ghp_[A-Za-z0-9]{36}' \
      -e 'xox[baprs]-[A-Za-z0-9-]{10,}' \
      -e '-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----' \
      "$f" 2>/dev/null || echo 0)
    secret_hits=$((secret_hits + hits))
  done < "$files_path"
else
  secret_hits=unknown
fi
echo "secret_tool=$secret_tool secret_hits_in_diff=$secret_hits"
signal secrets "$secret_hits"
signal secrets_tool "$secret_tool"
signal secrets_scope diff

# ==============================================================================
# Complexity (diff-scoped) — lizard on changed files
# ==============================================================================
section "COMPLEXITY (diff-scoped)"
lizard_warning_count=unknown
lizard_avg_ccn=unknown
if has_cmd lizard; then
  existing=$(mktemp)
  while IFS= read -r f; do
    [ -n "$f" ] && [ -f "$f" ] && printf '%s\n' "$f"
  done < "$files_path" > "$existing"
  if [ -s "$existing" ]; then
    mapfile -t arr < "$existing"
    lizard_full=$(timeout_wrap lizard "${arr[@]}" 2>/dev/null || true)
    echo "$lizard_full" | tail -15
    lizard_warning_count=$(timeout_wrap lizard -w "${arr[@]}" 2>/dev/null | grep -c "warning:" || echo 0)
    lizard_avg_ccn=$(echo "$lizard_full" \
      | awk '/^[[:space:]]*[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+/ {ccn=$3} END {print (ccn=="" ? "unknown" : ccn)}')
  fi
  rm -f "$existing"
else
  echo "(lizard not installed — install: pip install lizard)"
fi
signal lizard_warning_count "$lizard_warning_count"
signal lizard_avg_ccn        "$lizard_avg_ccn"
signal complexity_scope diff

# ==============================================================================
# Duplication (diff-scoped) — jscpd on changed files
# ==============================================================================
section "DUPLICATION (diff-scoped)"
duplication_pct=unknown
if has_cmd jscpd; then
  existing=$(mktemp)
  while IFS= read -r f; do
    [ -n "$f" ] && [ -f "$f" ] && printf '%s\n' "$f"
  done < "$files_path" > "$existing"
  if [ -s "$existing" ]; then
    jscpd_dir=$(mktemp -d)
    mapfile -t arr < "$existing"
    timeout_wrap jscpd --silent --reporters json --output "$jscpd_dir" "${arr[@]}" >/dev/null 2>&1 || true
    if [ -f "$jscpd_dir/jscpd-report.json" ] && has_cmd jq; then
      duplication_pct=$(jq -r '.statistics.total.percentage // "unknown"' "$jscpd_dir/jscpd-report.json" 2>/dev/null || echo unknown)
    fi
    rm -rf "$jscpd_dir"
  fi
  rm -f "$existing"
  echo "duplication_pct=$duplication_pct%"
else
  echo "(jscpd not installed — install: npm install -g jscpd)"
fi
signal duplication_pct "$duplication_pct"
signal duplication_scope diff

# ==============================================================================
# File sizes (diff-scoped)
# ==============================================================================
section "FILE SIZES (diff-scoped, top 10)"
largest=0
sizes=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ -f "$f" ] || continue
  line=$(wc -l "$f" 2>/dev/null) || continue
  sizes+="${line}"$'\n'
done < "$files_path"
if [ -n "$sizes" ]; then
  sorted=$(printf '%s' "$sizes" | sort -rn)
  echo "$sorted" | head -10
  largest=$(echo "$sorted" | head -1 | awk '{print $1+0}')
fi
signal largest_file_lines "$largest"
signal largest_file_lines_scope diff

# ==============================================================================
# Heuristic evidence (diff-scoped)
# ==============================================================================
HEUR="$(dirname "$0")/heuristics.sh"
if [ -x "$HEUR" ]; then
  bash "$HEUR" "$files_path"
else
  echo "(heuristics.sh missing — skipping evidence)" >&2
fi

echo
echo "=== DIFF DONE ==="
