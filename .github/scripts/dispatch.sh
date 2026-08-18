#!/bin/bash
# Ping cascade consumers. Lines are: owner/repo event_type
set -euo pipefail
if [ -z "${CASCADE_TOKEN:-}" ]; then
  echo "CASCADE_TOKEN is not set. Add it as an org or repo secret so this workflow can ping other repos. Skipping."
  exit 0
fi
export GH_TOKEN="$CASCADE_TOKEN"
if [ ! -f "${1:-}" ]; then
  echo "usage: dispatch.sh targets.txt" >&2
  exit 2
fi
source_repo="${SOURCE_REPO:-unknown}"
source_sha="${SOURCE_SHA:-unknown}"
while read -r repo event; do
  [ -z "${repo:-}" ] && continue
  [ "${repo:0:1}" = "#" ] && continue
  echo "dispatch $event -> $repo"
  gh api --method POST "repos/${repo}/dispatches" --input - <<JSON
{"event_type":"${event}","client_payload":{"source":"${source_repo}","sha":"${source_sha}"}}
JSON
done < "$1"
