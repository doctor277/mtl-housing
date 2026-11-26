#!/usr/bin/env bash
# Called by .github/workflows/feeds.yml after `refresh-feeds --check --report REPORT` (M5.5).
# Usage: feeds_issue.sh REPORT RUN_URL
#
# - Empty report: nothing to do.
# - No open Issue with TITLE: open one.
# - An open Issue already: never a second one. Comment only if the report has a finding
#   ("- …" line) that the Issue's text and comments don't contain yet; otherwise skip.
set -euo pipefail

report=$1
run_url=$2
title="GTFS feeds need a refresh"

if [ ! -s "$report" ]; then
  echo "Nothing to report."
  exit 0
fi

body=$(mktemp)
{
  cat "$report"
  echo
  echo "Checked on $(date -u +%Y-%m-%d) by the weekly \`GTFS feeds\` workflow ([run]($run_url))."
} > "$body"

# List open Issues directly (not GitHub search, whose index can lag) and match the exact title.
open=$(gh issue list --state open --limit 500 --json number,title \
  --jq "map(select(.title == \"$title\")) | .[0].number // empty")

if [ -z "$open" ]; then
  gh issue create --title "$title" --body-file "$body"
  exit 0
fi

posted=$(gh issue view "$open" --json body,comments --jq '[.body] + [.comments[].body] | join("\n")' | tr -d '\r')
new=0
while IFS= read -r line; do
  case "$line" in
    "- "*) grep -qxF -- "$line" <<< "$posted" || new=1 ;;
  esac
done < "$report"

if [ "$new" = 1 ]; then
  gh issue comment "$open" --body-file "$body"
  echo "Commented on #$open: new findings."
else
  echo "Issue #$open already lists these findings; skipped."
fi
