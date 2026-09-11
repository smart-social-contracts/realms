#!/usr/bin/env bash
# One-shot: install dfx from host HTTP push, then run provision-prod.
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v dfx >/dev/null 2>&1; then
  echo "[run] installing dfx from host (http://10.0.2.2:8890/)"
  curl -fsSL http://10.0.2.2:8890/install-dfx.sh | sudo bash -s 8890
fi
echo "[run] starting provision-prod"
exec sudo ./realms-key-ceremony.sh provision-prod
