#!/usr/bin/env bash
# trend.sh — manage grade history for the /grade skill
#
# Usage:
#   trend.sh slug                       Print repo slug for current directory
#   trend.sh prev <slug> [mode]         Print previous history entry (last JSONL line)
#   trend.sh append <slug> <json> [mode]
#                                       Append a new JSONL entry for this run
#
# mode is one of: full (default) | diff
# History is stored at:
#   ~/.claude/grade-history/<slug>.jsonl        (full mode)
#   ~/.claude/grade-history/<slug>.diff.jsonl   (diff mode)
#
# History lives outside the plugin install directory so it persists across
# plugin updates and is user-scoped rather than plugin-scoped. Full-mode and
# diff-mode trajectories are kept separate so that trend lines don't mix
# apples and oranges (a diff grade is systematically different from a
# full-repo grade on the same commit).
set -e

HIST_DIR="${HOME}/.claude/grade-history"
mkdir -p "$HIST_DIR"

hist_file_for() {
  local slug="$1" mode="${2:-full}"
  case "$mode" in
    full) echo "$HIST_DIR/$slug.jsonl" ;;
    diff) echo "$HIST_DIR/$slug.diff.jsonl" ;;
    *) echo "unknown mode: $mode (expected 'full' or 'diff')" >&2; exit 2 ;;
  esac
}

cmd="${1:-}"
case "$cmd" in
  slug)
    root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    basename "$root" | tr -c '[:alnum:]._-' '_'
    ;;
  prev)
    slug="${2:?slug required}"
    mode="${3:-full}"
    f=$(hist_file_for "$slug" "$mode")
    if [ -f "$f" ]; then
      tail -n1 "$f"
    fi
    ;;
  append)
    slug="${2:?slug required}"
    json="${3:?json required}"
    mode="${4:-full}"
    f=$(hist_file_for "$slug" "$mode")
    printf '%s\n' "$json" >> "$f"
    echo "appended to $f"
    ;;
  *)
    echo "usage: trend.sh slug | prev <slug> [mode] | append <slug> <json> [mode]" >&2
    exit 1
    ;;
esac
