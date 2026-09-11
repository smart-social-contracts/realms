#!/usr/bin/env bash
# icp-cli is an optional cross-check for PEM → IC principal derivation.
# The authoritative derivation is offline (lib/ic_principal.py); dfx cannot
# import openssl prime256v1 PEMs, so it is not used for this at all.
set -euo pipefail

CEREMONY_ICP_CLI_VERSION="${CEREMONY_ICP_CLI_VERSION:-1.3.0}"

install_icp_for_ceremony() {
  if command -v icp >/dev/null 2>&1; then
    log_detail "icp already installed ($(icp --version 2>&1 | head -1))"
    return 0
  fi
  if ! command -v npm >/dev/null 2>&1; then
    log_detail "npm unavailable — skipping optional icp-cli cross-check tool"
    return 0
  fi
  log "installing icp-cli ${CEREMONY_ICP_CLI_VERSION} (optional principal cross-check)"
  if npm install -g "@icp-sdk/icp-cli@${CEREMONY_ICP_CLI_VERSION}"; then
    log_detail "icp installed at $(command -v icp)"
  else
    log_detail "icp-cli install failed — continuing (offline derivation is authoritative)"
  fi
}
