#!/usr/bin/env bash
# diff-chunk.sh — chunk a large git diff into apfel-sized pieces instead of
# dumping the whole thing into an LLM's context (or skipping apfel entirely
# because the total is too big).
#
#   New files      -> skeletoned (ast-skeleton.py) + one apfel call each
#   Modified files -> delegated to apfel individually if their own diff is
#                      over $THRESHOLD_LINES; otherwise left in --stat only
#   Deleted/renamed -> just listed, no apfel call
#   Final pass     -> the digest of one-liners above (small, no code in it)
#                      goes through ONE MORE apfel call to group them into
#                      categories — this is still just text-on-text
#                      transformation, same shape as "release notes from
#                      commit log", not reasoning about the actual codebase.
#
# Still review the grouped output before it ships, same as any apfel draft.
# What genuinely needs the primary model is judgment apfel can't have from
# one-liners alone — e.g. "is this a breaking change", architecture calls.
#
# Usage: diff-chunk.sh <range>   e.g. diff-chunk.sh main...HEAD
#        diff-chunk.sh --selftest
set -euo pipefail
THRESHOLD_LINES="${THRESHOLD_LINES:-20}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# should_delegate ADDED REMOVED -> true if the combined change exceeds the threshold
should_delegate() { [ "$(( ${1:-0} + ${2:-0} ))" -gt "$THRESHOLD_LINES" ]; }

selftest() {
  should_delegate 15 3 && { echo "FAIL: 18 changed lines should be under threshold"; exit 1; }
  should_delegate 25 0 || { echo "FAIL: 25 changed lines should exceed threshold"; exit 1; }
  should_delegate 0 0 && { echo "FAIL: 0 changed lines should be under threshold"; exit 1; }
  echo "ok"
}

run() {
  local range="$1"
  command -v apfel >/dev/null || { echo "apfel not installed — brew install apfel" >&2; exit 1; }

  local digest
  digest="$(mktemp)"
  trap "rm -f '$digest'" EXIT  # expand $digest now — it's a local var, gone by the time a deferred trap would fire

  echo "## git diff --stat"
  git diff --stat "$range"
  echo

  while read -r status file; do
    case "$status" in
      A)
        summary=$(python3 "$SCRIPT_DIR/ast-skeleton.py" "$file" 2>/dev/null | apfel "One sentence: what does this add?" 2>/dev/null) \
          || summary="(couldn't skeleton this file type — see --stat above)"
        echo "### NEW: $file"
        echo "$summary"
        echo
        printf 'NEW %s: %s\n' "$file" "$summary" >> "$digest"
        ;;
      M)
        read -r added removed _ < <(git diff --numstat "$range" -- "$file")
        if should_delegate "${added:-0}" "${removed:-0}"; then
          summary=$(git diff "$range" -- "$file" | apfel "Summarize this file's change in one sentence")
          echo "### MODIFIED (delegated, +${added:-0}/-${removed:-0}): $file"
          echo "$summary"
          echo
          printf 'MODIFIED %s: %s\n' "$file" "$summary" >> "$digest"
        else
          echo "### MODIFIED (small, +${added:-0}/-${removed:-0} — see --stat above): $file"
          echo
        fi
        ;;
      D) echo "### DELETED: $file"; echo ;;
      *) echo "### $status: $file"; echo ;;
    esac
  done < <(git diff --name-status "$range")

  if [ -s "$digest" ]; then
    echo "## Grouped summary (second apfel pass over the digest — still review before it ships)"
    apfel "Group these file-change summaries into categories (e.g. Features, Fixes, Refactoring). Flag any that look related across files." < "$digest"
  fi
}

if [ "${1:-}" = "--selftest" ]; then selftest; exit 0; fi
[ $# -eq 1 ] || { echo "usage: diff-chunk.sh <range>|--selftest" >&2; exit 1; }
run "$1"
