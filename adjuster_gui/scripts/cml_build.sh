#!/usr/bin/env bash
#
# One-command build for a Cloudera AI (CML) Session — no root required.
#
# Installs a prebuilt Node.js into $HOME (persistent project storage), builds the
# React frontend into frontend/dist, and installs the Python backend deps. After
# this runs, the CML Application command is:
#   python adjuster_gui/backend/main.py
# when the Cloudera AI project is this repo, or:
#   python backend/main.py
# when the project root is adjuster_gui itself.
#
# Usage (from a CML Session terminal, repo root or adjuster_gui):
#   bash adjuster_gui/scripts/cml_build.sh
#
set -euo pipefail

NODE_VERSION="${NODE_VERSION:-v20.18.1}"

# adjuster_gui root = parent of this script's directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$APP_ROOT"

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }

# --- 1. Node.js (prebuilt tarball into $HOME, no root) -----------------------
case "$(uname -m)" in
  x86_64|amd64) NODE_ARCH="linux-x64" ;;
  aarch64|arm64) NODE_ARCH="linux-arm64" ;;
  *) echo "Unsupported CPU arch: $(uname -m)" >&2; exit 1 ;;
esac

NODE_HOME="$HOME/node-${NODE_VERSION}-${NODE_ARCH}"
export PATH="$NODE_HOME/bin:$PATH"

if [ -x "$NODE_HOME/bin/node" ]; then
  log "Node already installed: $("$NODE_HOME/bin/node" -v) ($NODE_HOME)"
else
  log "Installing Node ${NODE_VERSION} (${NODE_ARCH}) into \$HOME"
  TARBALL="node-${NODE_VERSION}-${NODE_ARCH}.tar.xz"
  URL="https://nodejs.org/dist/${NODE_VERSION}/${TARBALL}"
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  curl -fsSL "$URL" -o "$TMP/$TARBALL"
  tar -xf "$TMP/$TARBALL" -C "$HOME"
fi

log "Using node $(node -v), npm $(npm -v)"

# --- 2. Frontend build -------------------------------------------------------
log "Installing frontend dependencies"
cd "$APP_ROOT/frontend"
npm install --no-fund --no-audit

log "Building frontend -> frontend/dist"
npm run build
cd "$APP_ROOT"

# --- 3. Backend Python deps --------------------------------------------------
log "Installing backend Python dependencies"
python3 -m pip install --user -r backend/requirements.txt

# --- Done --------------------------------------------------------------------
log "Build complete."
cat <<EOF

Next steps in Cloudera AI:
  * Create an Application. Command depends on the project root:
      - this repo:          python adjuster_gui/backend/main.py
      - adjuster_gui only:  python backend/main.py
  * It binds \$CDSW_APP_PORT automatically and serves frontend/dist.
  * Health check path: /health

The workflow URL and bearer token stay in the browser gear dialog.
They are not written into the project.

Tip: add Node to your PATH in future sessions with:
  export PATH="$NODE_HOME/bin:\$PATH"
EOF
