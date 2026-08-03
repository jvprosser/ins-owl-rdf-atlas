#!/usr/bin/env bash
# Vendor shared code + assets into each Agent Studio tool folder for upload.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$(cd "$ROOT/../src" && pwd)"
ASSETS="$ROOT/runtime_assets"

# Refresh assets from repo root when present
REPO="$(cd "$ROOT/../.." && pwd)"
if [[ -d "$REPO/ontology" ]]; then
  rsync -a --delete "$REPO/ontology/" "$ASSETS/ontology/"
  rsync -a --delete "$REPO/probes/" "$ASSETS/probes/"
  rsync -a --delete "$REPO/playbook/" "$ASSETS/playbook/"
fi

for tool in build_claim_graph validate_claim_graph route_claim; do
  dest="$ROOT/$tool"
  rsync -a --delete "$ROOT/shared/" "$dest/shared/"
  rsync -a --delete "$ASSETS/" "$dest/runtime_assets/"
  rsync -a --delete "$SRC/ins_claims_agent/" "$dest/ins_claims_agent/"
  echo "Bundled $tool"
done
