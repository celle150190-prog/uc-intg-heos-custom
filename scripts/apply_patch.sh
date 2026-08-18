#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_DIR="${1:-../uc-intg-heos}"
REMOTE_FILE="$UPSTREAM_DIR/uc_intg_heos/remote.py"
PATCH_FILE="$(cd "$(dirname "$0")/.." && pwd)/patches/remote_denon_ui.patch"

if [[ ! -f "$REMOTE_FILE" ]]; then
  echo "HEOS v2.1.2 source tree not found: $REMOTE_FILE" >&2
  exit 1
fi

cd "$UPSTREAM_DIR"
git apply --check "$PATCH_FILE"
git apply "$PATCH_FILE"
echo "Patch applied successfully to $REMOTE_FILE"
