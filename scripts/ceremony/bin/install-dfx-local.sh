#!/usr/bin/env bash
# Install bundled dfx from this repo (works offline — no HTTP/network needed).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CEREMONY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${CEREMONY_DIR}/lib/common.sh"
# shellcheck source=../lib/dfx.sh
source "${CEREMONY_DIR}/lib/dfx.sh"

if [[ "${EUID}" -ne 0 ]]; then
  exec sudo "$0" "$@"
fi

[[ -x "${SCRIPT_DIR}/dfx" ]] || die "bundled dfx missing at ${SCRIPT_DIR}/dfx (fetch on host: ./vm/push-ceremony-scripts.sh --daemon)"
install_dfx_local
dfx --version
log "dfx ready — re-run: sudo ./realms-key-ceremony.sh provision-prod"
