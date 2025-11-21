#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="${SCRIPT_DIR}/../web/client"

if [ ! -d "$CLIENT_DIR" ]; then
  echo "error: UI client directory not found at $CLIENT_DIR" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm is required but not installed" >&2
  exit 1
fi

pushd "$CLIENT_DIR" >/dev/null

if [ "${SKIP_NPM_INSTALL:-0}" != "1" ]; then
  if [ "${CI:-}" = "true" ]; then
    npm ci
  else
    npm install
  fi
else
  echo "Skipping npm install because SKIP_NPM_INSTALL=1"
fi

npm run build

popd >/dev/null

echo "UI assets built in $CLIENT_DIR/dist"
