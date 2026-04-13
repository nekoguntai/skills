#!/usr/bin/env bash
# heuristics.sh — lightweight evidence collector for LLM judgment.
#
# This script is NOT a scoring engine. It emits numeric hints that the /grade
# skill passes to the LLM as evidence when it has to make a *judged* call on a
# criterion that no static tool can measure reliably (Fault Tolerance, Time
# Behavior, test flakiness, etc.). The LLM then uses Explore to inspect the
# specific sites flagged by these counts and scores the criterion with an
# ISO 25010-anchored justification.
#
# Signals that DO drive mechanical scoring live in grade.sh and are backed by
# real tools (lizard, jscpd, gitleaks, native test/lint/audit runners). Nothing
# emitted from this script is used for a mechanical threshold — it's context.
#
# Usage: heuristics.sh <file_list>
#   <file_list>: path to a text file with one source file path per line.

set -u

files_path="${1:?usage: heuristics.sh <file_list>}"
if [ ! -f "$files_path" ]; then
  echo "error: file list not found: $files_path" >&2
  exit 1
fi

section() { printf '\n=== %s ===\n' "$1"; }
signal()  { printf 'SIGNAL: %s=%s\n' "$1" "$2"; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }

section "EVIDENCE (heuristic — for LLM judgment, not direct scoring)"

if ! has_cmd rg; then
  echo "(ripgrep not available — skipping heuristic evidence)"
  for k in suppression_count timeout_retry_count blocking_io_count \
           validation_lib_present observability_lib_present \
           logging_call_count health_endpoint_count test_file_count \
           test_sleep_count; do
    signal "$k" unknown
  done
  exit 0
fi

# Filter incoming list to existing files.
existing_files=$(mktemp)
test_files=$(mktemp)
trap 'rm -f "$existing_files" "$test_files"' EXIT

while IFS= read -r f; do
  [ -n "$f" ] && [ -f "$f" ] && printf '%s\n' "$f"
done < "$files_path" > "$existing_files"

total_file_count=$(wc -l < "$existing_files" | tr -d ' ')
if [ "$total_file_count" -eq 0 ]; then
  echo "(file list empty — emitting zero signals)"
  for k in suppression_count timeout_retry_count blocking_io_count \
           logging_call_count health_endpoint_count test_file_count \
           test_sleep_count; do
    signal "$k" 0
  done
  signal validation_lib_present 0
  signal observability_lib_present 0
  exit 0
fi

count_pattern() {
  local pattern="$1"
  xargs -a "$existing_files" rg -c --no-messages -e "$pattern" 2>/dev/null \
    | awk -F: '{sum+=$NF} END {print sum+0}'
}
any_match() {
  local pattern="$1"
  if xargs -a "$existing_files" rg -l --no-messages -e "$pattern" 2>/dev/null | head -1 | grep -q .; then
    echo 1
  else
    echo 0
  fi
}

# -------- Suppression markers (cross-language) --------
# Counts TODO/FIXME/XXX/HACK + language-specific suppression directives.
# The LLM interprets density vs codebase size when scoring.
suppression_count=$(count_pattern '\b(TODO|FIXME|XXX|HACK)\b|@ts-ignore|eslint-disable|# type: ignore|# noqa|//nolint|#\[allow|@SuppressWarnings|@Suppress|rubocop:disable|#pragma warning|// swiftlint:disable')
echo "suppression_count=$suppression_count"
signal suppression_count "$suppression_count"

# -------- Resilience patterns (Reliability: Fault Tolerance evidence) --------
timeout_retry_count=$(count_pattern '\b(timeout|retry|backoff|AbortController|withTimeout|setTimeout|ExponentialBackoff|CircuitBreaker|Polly|resilience4j)\b')
echo "timeout_retry_count=$timeout_retry_count"
signal timeout_retry_count "$timeout_retry_count"

# -------- Blocking I/O in code (Performance: Time Behavior evidence) --------
# Cross-language: sync fs, sync HTTP, sleep calls
blocking_io_count=$(count_pattern '\breadFileSync\(|\bwriteFileSync\(|\brequests\.get\(|\burllib\.request|\btime\.sleep\(|\bThread\.sleep|\bFile\.ReadAllText\(|\bscanner\.nextLine')
echo "blocking_io_count=$blocking_io_count"
signal blocking_io_count "$blocking_io_count"

# -------- Validation library presence (Security: Integrity evidence) --------
validation_lib_present=$(any_match '\b(pydantic|zod|joi|yup|valibot|ajv)\b|go-playground/validator|javax\.validation|FluentValidation|DataAnnotations|dry-validation|Ecto\.Changeset')
echo "validation_lib_present=$validation_lib_present"
signal validation_lib_present "$validation_lib_present"

# -------- Observability library presence (Operational Readiness enabler) --------
observability_lib_present=$(any_match '\b(prometheus|opentelemetry|datadog|honeycomb|sentry|newrelic|statsd|micrometer|applicationinsights)\b')
echo "observability_lib_present=$observability_lib_present"
signal observability_lib_present "$observability_lib_present"

# -------- Logging calls (Operational Readiness evidence) --------
logging_call_count=$(count_pattern '\blogger\.|\blogging\.|\bwinston\b|\bpino\b|\bslog\.|\bconsole\.log\(|\blogrus\.|\bzap\.|\btracing::|\bSerilog\b|\bLoggerFactory\b|Log\.info|Log\.error')
echo "logging_call_count=$logging_call_count"
signal logging_call_count "$logging_call_count"

# -------- Health endpoints (Operational Readiness enabler) --------
health_endpoint_count=$(count_pattern '"/(health|healthz|ready|readyz|livez)"|@app\.route.*health|GetMapping.*health|HealthCheck')
echo "health_endpoint_count=$health_endpoint_count"
signal health_endpoint_count "$health_endpoint_count"

# -------- Test file presence (Test Quality evidence) --------
test_file_count=$(grep -cE '(\.test\.|\.spec\.|/test_|/tests?/|__tests__|Tests?/|_test\.go$|_test\.rs$)' "$existing_files" 2>/dev/null || echo 0)
grep -E '(\.test\.|\.spec\.|/test_|/tests?/|__tests__|Tests?/|_test\.go$|_test\.rs$)' "$existing_files" > "$test_files" 2>/dev/null || true
echo "test_file_count=$test_file_count total_file_count=$total_file_count"
signal test_file_count "$test_file_count"

# -------- Flaky test patterns (Test Quality: flakiness evidence) --------
test_sleep_count=0
if [ -s "$test_files" ]; then
  test_sleep_count=$(xargs -a "$test_files" rg -c --no-messages -e '\bsleep\(|setTimeout\([^,]+,\s*[0-9]+\)|\btime\.sleep\(|Thread\.sleep\(' 2>/dev/null \
    | awk -F: '{sum+=$NF} END {print sum+0}')
fi
echo "test_sleep_count=$test_sleep_count"
signal test_sleep_count "$test_sleep_count"

echo
echo "=== EVIDENCE DONE ==="
