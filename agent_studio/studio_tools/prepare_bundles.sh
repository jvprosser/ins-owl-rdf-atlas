#!/usr/bin/env bash
# Vendor shared code + assets into each Agent Studio tool folder for upload.
# Uses only POSIX cp/rm (no rsync).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$(cd "$ROOT/../src" && pwd)"
ASSETS="$ROOT/runtime_assets"
REPO="$(cd "$ROOT/../.." && pwd)"

copy_tree() {
  # copy_tree SRC_DIR DEST_DIR  — replace DEST with a fresh copy of SRC
  local src="$1"
  local dest="$2"
  rm -rf "$dest"
  mkdir -p "$(dirname "$dest")"
  cp -R "$src" "$dest"
}

# Refresh assets from repo root when present
if [[ -d "$REPO/ontology" ]]; then
  mkdir -p "$ASSETS"
  copy_tree "$REPO/ontology" "$ASSETS/ontology"
  copy_tree "$REPO/probes" "$ASSETS/probes"
  copy_tree "$REPO/playbook" "$ASSETS/playbook"
fi

for tool in build_claim_graph validate_claim_graph route_claim; do
  dest="$ROOT/$tool"
  copy_tree "$ROOT/shared" "$dest/shared"
  copy_tree "$ASSETS" "$dest/runtime_assets"
  copy_tree "$SRC/ins_claims_agent" "$dest/ins_claims_agent"
  echo "Bundled $tool"
done
