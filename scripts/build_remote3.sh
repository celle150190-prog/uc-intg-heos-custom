#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_DIR="${1:-../uc-intg-heos}"
IMAGE="${PYINSTALLER_IMAGE:-unfoldedcircle/r2-pyinstaller:3.11.13}"

rm -rf "$UPSTREAM_DIR/dist" "$UPSTREAM_DIR/build"
git -C "$UPSTREAM_DIR" apply --check "$(cd "$(dirname "$0")/.." && pwd)/patches/remote_denon_ui.patch"
git -C "$UPSTREAM_DIR" apply "$(cd "$(dirname "$0")/.." && pwd)/patches/remote_denon_ui.patch"

docker run --rm --platform linux/arm64 \
  -v "$(cd "$UPSTREAM_DIR" && pwd):/workspace" \
  -w /workspace "$IMAGE" \
  bash -lc 'set -euo pipefail; DRIVER_PATH="$(find . -type f -name driver.py -print -quit)"; test -n "${DRIVER_PATH}"; python -m pip install -r requirements.txt; pyinstaller --clean --onedir --name driver "${DRIVER_PATH}"'

rm -rf ./artifacts
mkdir -p ./artifacts/bin
cp -a "$UPSTREAM_DIR/dist/driver/." ./artifacts/bin/
cp "$(cd "$(dirname "$0")/.." && pwd)/driver.json" ./artifacts/driver.json

tar czf uc-intg-heos-denon-ui-2.1.2-aarch64.tar.gz -C ./artifacts .

echo "Created uc-intg-heos-denon-ui-2.1.2-aarch64.tar.gz"
