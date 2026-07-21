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

files_path="${1:?usage: diff_scan.sh <file_list> [base_ref]}"
if [ ! -f "$files_path" ]; then
  echo "error: file list not found: $files_path" >&2
  exit 1
fi

GRADE_TIMEOUT="${GRADE_TIMEOUT:-120}"
section() { printf '\n=== %s ===\n' "$1"; }
signal()  { printf 'SIGNAL: %s=%s\n' "$1" "$2"; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }
count_nonempty_lines() {
  awk 'NF { c++ } END { print c + 0 }' "$1" 2>/dev/null || echo 0
}
timeout_wrap() {
  if has_cmd timeout; then timeout "$GRADE_TIMEOUT" "$@"
  else "$@"; fi
}
classify_rc() {
  case "$1" in 0) echo pass ;; 124) echo timeout ;; *) echo fail ;; esac
}
parse_lizard_max_ccn() {
  awk '
    /^[[:space:]]*[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+/ {
      if (!found || $2 + 0 > max) max = $2 + 0
      found = 1
    }
    END { print found ? max : "unknown" }
  '
}
numeric_delta() {
  awk -v current="$1" -v base="$2" '
    function isnum(v) { return v ~ /^-?[0-9]+([.][0-9]+)?$/ }
    BEGIN {
      if (isnum(current) && isnum(base)) print current - base
      else print "unknown"
    }
  '
}

section "DIFF SCOPE"
file_count=$(count_nonempty_lines "$files_path")
echo "changed_files=$file_count"
signal diff_file_count "$file_count"
base_ref="${2:-}"
base_dir=""
base_files=""
current_files=$(mktemp)
comparable_current_files=$(mktemp)
comparable_base_files=$(mktemp)
current_only_files=$(mktemp)
base_only_files=$(mktemp)
while IFS= read -r f; do
  [ -n "$f" ] && [ -f "$f" ] && printf '%s\n' "$f"
done < "$files_path" > "$current_files"
if [ -n "$base_ref" ] && git rev-parse --verify "$base_ref" >/dev/null 2>&1; then
  base_dir=$(mktemp -d)
  base_files=$(mktemp)
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel="${f#./}"
    out="$base_dir/$rel"
    mkdir -p "$(dirname "$out")"
    if git show "$base_ref:$rel" > "$out" 2>/dev/null; then
      printf '%s\n' "$out" >> "$base_files"
      if [ -f "$f" ]; then
        printf '%s\n' "$f" >> "$comparable_current_files"
        printf '%s\n' "$out" >> "$comparable_base_files"
      else
        printf '%s\n' "$f" >> "$base_only_files"
      fi
    elif [ -f "$f" ]; then
      printf '%s\n' "$f" >> "$current_only_files"
    fi
  done < "$files_path"
  base_file_count=$(count_nonempty_lines "$base_files")
  echo "base_ref=$base_ref base_changed_files=$base_file_count"
  signal diff_base_ref "$base_ref"
  signal diff_base_file_count "$base_file_count"
else
  signal diff_base_ref "${base_ref:-unknown}"
  signal diff_base_file_count unknown
fi
current_file_count=$(count_nonempty_lines "$current_files")
comparable_file_count=$(count_nonempty_lines "$comparable_current_files")
current_only_file_count=$(count_nonempty_lines "$current_only_files")
base_only_file_count=$(count_nonempty_lines "$base_only_files")
echo "current_files=$current_file_count comparable_files=$comparable_file_count current_only=$current_only_file_count base_only=$base_only_file_count"
signal diff_current_file_count "$current_file_count"
signal diff_comparable_file_count "$comparable_file_count"
signal diff_current_only_file_count "$current_only_file_count"
signal diff_base_only_file_count "$base_only_file_count"
cleanup() {
  [ -n "$base_files" ] && [ -f "$base_files" ] && rm -f "$base_files"
  [ -n "$base_dir" ] && [ -d "$base_dir" ] && rm -r "$base_dir"
  rm -f "$current_files" "$comparable_current_files" "$comparable_base_files" "$current_only_files" "$base_only_files"
}
trap cleanup EXIT

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
lizard_max_ccn=unknown
comparable_lizard_warning_count=unknown
comparable_lizard_avg_ccn=unknown
comparable_lizard_max_ccn=unknown
base_lizard_warning_count=unknown
base_lizard_avg_ccn=unknown
base_lizard_max_ccn=unknown
if has_cmd lizard; then
  if [ -s "$current_files" ]; then
    mapfile -t arr < "$current_files"
    lizard_full=$(timeout_wrap lizard "${arr[@]}" 2>/dev/null || true)
    echo "$lizard_full" | tail -15
    lizard_warning_count=$(timeout_wrap lizard -w "${arr[@]}" 2>/dev/null | awk '/warning:/ { c++ } END { print c + 0 }')
    lizard_avg_ccn=$(echo "$lizard_full" \
      | awk '/^[[:space:]]*[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+/ {ccn=$3} END {print (ccn=="" ? "unknown" : ccn)}')
    lizard_max_ccn=$(echo "$lizard_full" | parse_lizard_max_ccn)
  fi
  if [ -s "$comparable_current_files" ]; then
    mapfile -t comparable_arr < "$comparable_current_files"
    comparable_lizard_full=$(timeout_wrap lizard "${comparable_arr[@]}" 2>/dev/null || true)
    comparable_lizard_warning_count=$(timeout_wrap lizard -w "${comparable_arr[@]}" 2>/dev/null | awk '/warning:/ { c++ } END { print c + 0 }')
    comparable_lizard_avg_ccn=$(echo "$comparable_lizard_full" \
      | awk '/^[[:space:]]*[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+/ {ccn=$3} END {print (ccn=="" ? "unknown" : ccn)}')
    comparable_lizard_max_ccn=$(echo "$comparable_lizard_full" | parse_lizard_max_ccn)
  fi
  if [ -s "$comparable_base_files" ]; then
    mapfile -t base_arr < "$comparable_base_files"
    base_lizard_full=$(timeout_wrap lizard "${base_arr[@]}" 2>/dev/null || true)
    base_lizard_warning_count=$(timeout_wrap lizard -w "${base_arr[@]}" 2>/dev/null | awk '/warning:/ { c++ } END { print c + 0 }')
    base_lizard_avg_ccn=$(echo "$base_lizard_full" \
      | awk '/^[[:space:]]*[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+/ {ccn=$3} END {print (ccn=="" ? "unknown" : ccn)}')
    base_lizard_max_ccn=$(echo "$base_lizard_full" | parse_lizard_max_ccn)
  fi
else
  echo "(lizard not installed — install: pip install lizard)"
fi
signal lizard_warning_count "$lizard_warning_count"
signal lizard_avg_ccn        "$lizard_avg_ccn"
signal lizard_max_ccn        "$lizard_max_ccn"
signal comparable_lizard_warning_count "$comparable_lizard_warning_count"
signal comparable_lizard_avg_ccn       "$comparable_lizard_avg_ccn"
signal comparable_lizard_max_ccn       "$comparable_lizard_max_ccn"
signal base_lizard_warning_count "$base_lizard_warning_count"
signal base_lizard_avg_ccn       "$base_lizard_avg_ccn"
signal base_lizard_max_ccn       "$base_lizard_max_ccn"
signal lizard_warning_delta      "$(numeric_delta "$comparable_lizard_warning_count" "$base_lizard_warning_count")"
signal lizard_avg_ccn_delta      "$(numeric_delta "$comparable_lizard_avg_ccn" "$base_lizard_avg_ccn")"
signal lizard_max_ccn_delta      "$(numeric_delta "$comparable_lizard_max_ccn" "$base_lizard_max_ccn")"
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
base_largest=unknown
comparable_largest=unknown
sizes=""
while IFS= read -r f; do
  line=$(wc -l "$f" 2>/dev/null) || continue
  sizes+="${line}"$'\n'
done < "$current_files"
if [ -n "$sizes" ]; then
  sorted=$(printf '%s' "$sizes" | sort -rn)
  echo "$sorted" | head -10
  largest=$(echo "$sorted" | head -1 | awk '{print $1+0}')
fi
if [ -s "$comparable_current_files" ]; then
  comparable_sizes=""
  while IFS= read -r f; do
    line=$(wc -l "$f" 2>/dev/null) || continue
    comparable_sizes+="${line}"$'\n'
  done < "$comparable_current_files"
  if [ -n "$comparable_sizes" ]; then
    comparable_largest=$(printf '%s' "$comparable_sizes" | sort -rn | head -1 | awk '{print $1+0}')
  fi
fi
if [ -s "$comparable_base_files" ]; then
  base_sizes=""
  while IFS= read -r f; do
    line=$(wc -l "$f" 2>/dev/null) || continue
    base_sizes+="${line}"$'\n'
  done < "$comparable_base_files"
  if [ -n "$base_sizes" ]; then
    base_largest=$(printf '%s' "$base_sizes" | sort -rn | head -1 | awk '{print $1+0}')
  fi
fi
signal largest_file_lines "$largest"
signal comparable_largest_file_lines "$comparable_largest"
signal base_largest_file_lines "$base_largest"
signal largest_file_lines_delta "$(numeric_delta "$comparable_largest" "$base_largest")"
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
