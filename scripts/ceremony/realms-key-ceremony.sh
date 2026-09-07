#!/usr/bin/env bash
# Realms YubiKey key ceremony — run on Ubuntu 22.04 Desktop live USB ("Try Ubuntu").
#
# Phases:
#   online-setup     Install packages while internet is available.
#   check-offline    Verify network is disconnected.
#   offline-generate Generate dev+prod key material (offline only).
#   provision-dev    Load dev key onto the 5C Nano (touch never).
#   provision-prod   Load prod key onto 3× 5 NFC (touch cached).
#   finalize         Verify principals, write operator instructions.
#   destroy          Shred secrets and unmount tmpfs.
#   run-offline      check-offline → offline-generate → provision-* (interactive).
#
# Simulation (Docker/CI — no hardware):
#   CEREMONY_SIMULATE=1 CEREMONY_FORCE_OFFLINE=1 ./realms-key-ceremony.sh run-offline
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=lib/network.sh
source "${SCRIPT_DIR}/lib/network.sh"
# shellcheck source=lib/secrets.sh
source "${SCRIPT_DIR}/lib/secrets.sh"
# shellcheck source=lib/yubikey.sh
source "${SCRIPT_DIR}/lib/yubikey.sh"

usage() {
  cat <<'EOF'
Usage: realms-key-ceremony.sh <command>

Commands:
  online-setup       Install ceremony dependencies (requires internet).
  check-offline      Fail if any network probe succeeds.
  offline-generate   Generate dev/prod P-256 keys + operator PINs (offline only).
  provision-dev      Import dev key to the dev YubiKey (touch never).
  provision-prod     Import prod key to three prod YubiKeys (touch cached).
  finalize           Validate manifest and print next steps for operators.
  destroy            Securely wipe ceremony workspace.
  run-offline        Full offline flow (generate + provision dev + 3× prod).

Environment:
  CEREMONY_ROOT          Workspace path (default: /run/realms-ceremony)
  CEREMONY_SIMULATE=1    Software-only mode for Docker tests (no YubiKey).
  CEREMONY_FORCE_OFFLINE=1   Skip online check (tests only).
  CEREMONY_FORCE_ONLINE=1    Skip offline requirement (tests only).
  CEREMONY_PIV_RESET=1     Reset PIV before import (destructive).
  CEREMONY_USE_TMPFS=0     Disable tmpfs mount (Docker tests).

Copy public artifacts out before destroy:
  ${CEREMONY_ARTIFACTS}/manifest.json
  ${CEREMONY_SECRETS}/operator-credentials.txt  (record on paper first!)
EOF
}

cmd_online_setup() {
  require_online
  ensure_root_or_sudo
  log "installing ceremony packages (Ubuntu 22.04 Desktop live)"
  export DEBIAN_FRONTEND=noninteractive
  local apt=(apt-get)
  if [[ "${EUID}" -ne 0 ]]; then
    apt=(sudo apt-get)
  fi
  "${apt[@]}" update -qq
  "${apt[@]}" install -y --no-install-recommends \
    openssl \
    jq \
    curl \
    ca-certificates \
    pcscd \
    libpcsclite1 \
    yubikey-manager \
    yubikey-manager-qt \
    ykcs11 \
    yubico-piv-tool \
    coreutils \
    util-linux \
    mount \
    libdbus-1-3 \
    nodejs \
    npm
  if ! command -v icp >/dev/null 2>&1; then
    log "installing icp-cli (principal export after provisioning)"
    npm install -g @icp-sdk/icp-cli@1.3.0
  fi
  if [[ ! -f "${CEREMONY_PKCS11_LIB}" ]]; then
    die "PKCS#11 library missing after install: ${CEREMONY_PKCS11_LIB} (expected package ykcs11)"
  fi
  command -v icp >/dev/null 2>&1 || die "icp-cli not available after online-setup"
  command -v ykman >/dev/null 2>&1 || die "ykman not available after online-setup"
  if [[ "${EUID}" -eq 0 ]]; then
    systemctl enable --now pcscd 2>/dev/null || service pcscd start 2>/dev/null || true
  else
    sudo systemctl enable --now pcscd 2>/dev/null || sudo service pcscd start 2>/dev/null || true
  fi
  init_secure_workspace
  write_manifest_header
  phase_marker "online-complete"
  log "online-setup complete — disconnect network, then run: check-offline && offline-generate"
}

cmd_check_offline() {
  init_secure_workspace
  require_offline
  phase_marker "offline-ready"
  log "offline check passed"
}

cmd_offline_generate() {
  init_secure_workspace
  if [[ "$(read_phase)" == "none" && "${CEREMONY_SIMULATE}" == "1" ]]; then
    write_manifest_header
    phase_marker "online-complete"
  fi
  require_phase_at_least "online-complete"
  require_offline
  require_cmd openssl
  write_manifest_header
  generate_operator_pins
  log "generating dev signing key (P-256)"
  generate_ec_key_pem "${CEREMONY_SECRETS}/dev-signing-key.pem"
  log "generating prod signing key (P-256)"
  generate_ec_key_pem "${CEREMONY_SECRETS}/prod-signing-key.pem"
  phase_marker "generated"
  log "offline-generate complete — run provision-dev, then provision-prod"
}

cmd_provision_dev() {
  init_secure_workspace
  require_phase_at_least "generated"
  require_offline
  yubikey_require_tools
  provision_dev_yubikey
  log "provision-dev complete"
}

cmd_provision_prod() {
  init_secure_workspace
  require_phase_at_least "generated"
  require_offline
  yubikey_require_tools
  local i
  for i in 1 2 3; do
    provision_prod_yubikey_copy "${i}"
  done
  verify_prod_principals_match
  log "provision-prod complete (3 identical copies)"
}

cmd_finalize() {
  init_secure_workspace
  require_cmd jq
  local manifest="${CEREMONY_ARTIFACTS}/manifest.json"
  [[ -f "${manifest}" ]] || die "missing manifest — run provisioning first"
  jq -e '.environments.dev.principal and .environments.prod.principal' "${manifest}" >/dev/null \
    || die "manifest missing dev/prod principals"
  if [[ -f "${CEREMONY_ARTIFACTS}/prod-serials.txt" ]]; then
    local count
    count="$(wc -l < "${CEREMONY_ARTIFACTS}/prod-serials.txt" | tr -d ' ')"
    [[ "${count}" == "3" ]] || die "expected 3 prod serials, found ${count}"
  fi
  if [[ "${CEREMONY_SIMULATE}" != "1" ]]; then
    cat > "${CEREMONY_ARTIFACTS}/operator-dfx-identity.txt" <<EOF
# Register these HSM-backed dfx identities on operator workstations (PEM never on disk).

# Dev (test/staging/demo) — touch never on YubiKey 5C Nano
dfx identity new realms-dev \\
  --hsm-key-id ${CEREMONY_HSM_KEY_ID} \\
  --hsm-pkcs11-lib-path ${CEREMONY_PKCS11_LIB}
export DFX_HSM_PIN='<PIV PIN from operator-credentials.txt>'

# Prod — touch cached on YubiKey 5 NFC (daily + backups)
dfx identity new realms-prod \\
  --hsm-key-id ${CEREMONY_HSM_KEY_ID} \\
  --hsm-pkcs11-lib-path ${CEREMONY_PKCS11_LIB}
EOF
  fi
  phase_marker "finalized"
  log "finalize complete"
  log "COPY BEFORE DESTROY:"
  log "  ${manifest}"
  log "  ${CEREMONY_ARTIFACTS}/operator-dfx-identity.txt (if present)"
  log "RECORD ON PAPER then destroy:"
  log "  ${CEREMONY_SECRETS}/operator-credentials.txt"
  jq '.' "${manifest}" >&2
}

cmd_destroy() {
  destroy_ceremony_state
}

cmd_run_offline() {
  cmd_check_offline
  cmd_offline_generate
  cmd_provision_dev
  cmd_provision_prod
  cmd_finalize
  log "run-offline complete — copy artifacts, record PINs, then: destroy"
}

main() {
  local cmd="${1:-}"
  case "${cmd}" in
    online-setup) cmd_online_setup ;;
    check-offline) cmd_check_offline ;;
    offline-generate) cmd_offline_generate ;;
    provision-dev) cmd_provision_dev ;;
    provision-prod) cmd_provision_prod ;;
    finalize) cmd_finalize ;;
    destroy) cmd_destroy ;;
    run-offline) cmd_run_offline ;;
    -h|--help|help|"") usage ;;
    *) die "unknown command: ${cmd} (try --help)" ;;
  esac
}

main "$@"
