#!/usr/bin/env bash
# trend.sh - manage grade history for the $grade skill.
#
# Usage:
#   trend.sh slug
#   trend.sh prev <slug> [mode]
#   trend.sh append <slug> <json> [mode]
#   trend.sh compare <previous-json> <current-json>
#
# mode is one of: full (default) | diff
#
# Default history location:
#   <repo-root>/docs/plans/grade-history/<slug>.jsonl
#   <repo-root>/docs/plans/grade-history/<slug>.diff.jsonl
#
# Override with GRADE_HISTORY_DIR when needed.
set -e

repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

history_dir() {
  if [ -n "${GRADE_HISTORY_DIR:-}" ]; then
    printf '%s\n' "$GRADE_HISTORY_DIR"
    return
  fi

  root="$(repo_root)"
  if git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '%s\n' "$root/docs/plans/grade-history"
  else
    printf '%s\n' "${HOME}/.codex/grade-history"
  fi
}

HIST_DIR="$(history_dir)"
mkdir -p "$HIST_DIR"

hist_file_for() {
  local slug="$1" mode="${2:-full}"
  case "$mode" in
    full) echo "$HIST_DIR/$slug.jsonl" ;;
    diff) echo "$HIST_DIR/$slug.diff.jsonl" ;;
    *) echo "unknown mode: $mode (expected 'full' or 'diff')" >&2; exit 2 ;;
  esac
}

compare_entries() {
  prev_json="${1:-}"
  current_json="${2:-}"
  if [ -z "$prev_json" ]; then
    echo "- No prior run to compare."
    return 0
  fi
  if ! command -v jq >/dev/null 2>&1; then
    echo "- Trend comparison requires jq."
    return 0
  fi

  rows="$(
    jq -r -n --argjson p "$prev_json" --argjson c "$current_json" '
      def n: try tonumber catch null;
      def grade_rank:
        if . == "A" then 5 elif . == "B" then 4 elif . == "C" then 3
        elif . == "D" then 2 elif . == "F" then 1 else null end;
      def confidence_rank:
        if . == "High" then 3 elif . == "Medium" then 2 elif . == "Low" then 1 else null end;
      def status_rank:
        if . == "pass" then 3 elif . == "timeout" then 2
        elif . == "missing" then 1 elif . == "fail" then 0 else null end;
      def known:
        . != null and (. | tostring) != "unknown" and (. | tostring) != "missing";
      def bucket($name; $value):
        ($value | n) as $x
        | if $x == null then null
          elif $name == "coverage" then
            if $x >= 80 then 3 elif $x >= 60 then 2 elif $x >= 40 then 1 else 0 end
          elif $name == "security_high" then
            if $x == 0 then 2 elif $x <= 2 then 1 else 0 end
          elif $name == "secrets" then
            if $x == 0 then 1 else 0 end
          elif $name == "largest_file_lines" then
            if $x < 500 then 2 elif $x <= 1000 then 1 else 0 end
          elif $name == "lizard_warning_count" then
            if $x == 0 then 3 elif $x <= 5 then 2 elif $x <= 15 then 1 else 0 end
          elif $name == "duplication_pct" then
            if $x < 3 then 2 elif $x <= 5 then 1 else 0 end
          elif $name == "deploy_artifact_count" then
            if $x >= 2 then 2 elif $x == 1 then 1 else 0 end
          elif $name == "health_endpoint_count" then
            if $x >= 1 then 1 else 0 end
          elif $name == "observability_lib_present" or $name == "validation_lib_present" then
            if $x >= 1 then 1 else 0 end
          else null end;
      def annotate_bucket($name; $prev; $cur; $label):
        (bucket($name; $prev)) as $prev_bucket
        | (bucket($name; $cur)) as $cur_bucket
        | if ($label == "improved" or $label == "regressed") and $prev_bucket != null and $cur_bucket != null then
            if $prev_bucket != $cur_bucket then "\($label) - threshold crossing"
            else "\($label) - within bucket" end
          else $label end;
      def classify($name; $dir; $prev; $cur):
        if ($prev == $cur) then empty
        elif (($prev | known) | not) and ($cur | known) then "newly measured"
        elif ($prev | known) and (($cur | known) | not) then "lost evidence"
        elif $dir == "lower" and (($prev | n) != null) and (($cur | n) != null) then
          if ($cur | n) < ($prev | n) then annotate_bucket($name; $prev; $cur; "improved")
          elif ($cur | n) > ($prev | n) then annotate_bucket($name; $prev; $cur; "regressed")
          else empty end
        elif $dir == "higher" and (($prev | n) != null) and (($cur | n) != null) then
          if ($cur | n) > ($prev | n) then annotate_bucket($name; $prev; $cur; "improved")
          elif ($cur | n) < ($prev | n) then annotate_bucket($name; $prev; $cur; "regressed")
          else empty end
        elif $dir == "grade" and (($prev | grade_rank) != null) and (($cur | grade_rank) != null) then
          if ($cur | grade_rank) > ($prev | grade_rank) then "improved"
          elif ($cur | grade_rank) < ($prev | grade_rank) then "regressed"
          else empty end
        elif $dir == "confidence" and (($prev | confidence_rank) != null) and (($cur | confidence_rank) != null) then
          if ($cur | confidence_rank) > ($prev | confidence_rank) then "improved confidence"
          elif ($cur | confidence_rank) < ($prev | confidence_rank) then "lower confidence"
          else empty end
        elif $dir == "status" and (($prev | status_rank) != null) and (($cur | status_rank) != null) then
          if ($cur | status_rank) > ($prev | status_rank) then "improved"
          elif ($cur | status_rank) < ($prev | status_rank) then "regressed"
          else empty end
        elif $dir == "review" then "changed - inspect"
        else "changed - inspect" end;
      def row($group; $name; $prev; $cur; $dir):
        (classify($name; $dir; $prev; $cur)) as $classification
        | select($classification != null and $classification != "")
        | [$group, $name, (($prev // "unknown") | tostring), (($cur // "unknown") | tostring), $classification] | @tsv;
      row("score"; "overall"; $p.overall; $c.overall; "higher"),
      row("score"; "grade"; $p.grade; $c.grade; "grade"),
      row("score"; "confidence"; $p.confidence; $c.confidence; "confidence"),
      row("domain"; "correctness"; $p.domains.correctness; $c.domains.correctness; "higher"),
      row("domain"; "reliability"; $p.domains.reliability; $c.domains.reliability; "higher"),
      row("domain"; "maintainability"; $p.domains.maintainability; $c.domains.maintainability; "higher"),
      row("domain"; "security"; $p.domains.security; $c.domains.security; "higher"),
      row("domain"; "performance"; $p.domains.performance; $c.domains.performance; "higher"),
      row("domain"; "test_quality"; $p.domains.test_quality; $c.domains.test_quality; "higher"),
      row("domain"; "operational_readiness"; $p.domains.operational_readiness; $c.domains.operational_readiness; "higher"),
      row("gate"; "tests"; $p.signals.tests; $c.signals.tests; "status"),
      row("gate"; "lint"; $p.signals.lint; $c.signals.lint; "status"),
      row("gate"; "typecheck"; $p.signals.typecheck; $c.signals.typecheck; "status"),
      row("signal"; "coverage"; $p.signals.coverage; $c.signals.coverage; "higher"),
      row("signal"; "security_high"; $p.signals.security_high; $c.signals.security_high; "lower"),
      row("signal"; "secrets"; $p.signals.secrets; $c.signals.secrets; "lower"),
      row("signal"; "largest_file_lines"; $p.signals.largest_file_lines; $c.signals.largest_file_lines; "lower"),
      row("signal"; "lizard_warning_count"; $p.signals.lizard_warning_count; $c.signals.lizard_warning_count; "lower"),
      row("signal"; "lizard_avg_ccn"; $p.signals.lizard_avg_ccn; $c.signals.lizard_avg_ccn; "lower"),
      row("signal"; "lizard_max_ccn"; $p.signals.lizard_max_ccn; $c.signals.lizard_max_ccn; "lower"),
      row("signal"; "duplication_pct"; $p.signals.duplication_pct; $c.signals.duplication_pct; "lower"),
      row("signal"; "deploy_artifact_count"; $p.signals.deploy_artifact_count; $c.signals.deploy_artifact_count; "higher"),
      row("signal"; "health_endpoint_count"; $p.signals.health_endpoint_count; $c.signals.health_endpoint_count; "higher"),
      row("signal"; "observability_lib_present"; $p.signals.observability_lib_present; $c.signals.observability_lib_present; "higher"),
      row("signal"; "validation_lib_present"; $p.signals.validation_lib_present; $c.signals.validation_lib_present; "higher"),
      row("signal"; "suppression_count"; $p.signals.suppression_count; $c.signals.suppression_count; "lower"),
      row("signal"; "blocking_io_count"; $p.signals.blocking_io_count; $c.signals.blocking_io_count; "lower"),
      row("signal"; "test_file_count"; $p.signals.test_file_count; $c.signals.test_file_count; "higher"),
      row("signal"; "test_sleep_count"; $p.signals.test_sleep_count; $c.signals.test_sleep_count; "lower"),
      row("signal"; "timeout_retry_count"; $p.signals.timeout_retry_count; $c.signals.timeout_retry_count; "review"),
      row("signal"; "logging_call_count"; $p.signals.logging_call_count; $c.signals.logging_call_count; "review")
    ' 2>/dev/null
  )"

  if [ -z "$rows" ]; then
    echo "- No material deltas detected against the previous recorded run."
    return 0
  fi

  printf '| Area | Signal | Previous | Current | Interpretation |\n'
  printf '| --- | --- | ---: | ---: | --- |\n'
  printf '%s\n' "$rows" | while IFS="$(printf '\t')" read -r area name prev current interpretation; do
    printf '| %s | `%s` | `%s` | `%s` | %s |\n' "$area" "$name" "$prev" "$current" "$interpretation"
  done
}

cmd="${1:-}"
case "$cmd" in
  slug)
    root="$(repo_root)"
    basename "$root" | tr -c '[:alnum:]._-' '_'
    ;;
  prev)
    slug="${2:?slug required}"
    mode="${3:-full}"
    f="$(hist_file_for "$slug" "$mode")"
    if [ -f "$f" ]; then
      tail -n1 "$f"
    fi
    ;;
  append)
    slug="${2:?slug required}"
    json="${3:?json required}"
    mode="${4:-full}"
    f="$(hist_file_for "$slug" "$mode")"
    printf '%s\n' "$json" >> "$f"
    echo "appended to $f"
    ;;
  compare)
    compare_entries "${2:-}" "${3:?current json required}"
    ;;
  *)
    echo "usage: trend.sh slug | prev <slug> [mode] | append <slug> <json> [mode] | compare <previous-json> <current-json>" >&2
    exit 1
    ;;
esac
