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
#   export-pem       Opt-in: copy dev/prod signing key to a dfx identity.pem path.
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
# shellcheck source=lib/config.sh
source "${SCRIPT_DIR}/lib/config.sh"
# shellcheck source=lib/dfx.sh
source "${SCRIPT_DIR}/lib/dfx.sh"
# shellcheck source=lib/packages.sh
source "${SCRIPT_DIR}/lib/packages.sh"
# shellcheck source=lib/yubikey.sh
source "${SCRIPT_DIR}/lib/yubikey.sh"

ceremony_bootstrap() {
  init_secure_workspace
  load_ceremony_config
}

usage() {
  cat <<'EOF'
Usage: realms-key-ceremony.sh <command>

Commands:
  online-setup       Install ceremony dependencies (requires internet).
  check-offline      Fail if any network probe succeeds.
  offline-generate   Generate dev/prod P-256 keys + operator PINs (offline only).
                     Optional: --credentials-file PATH (your PIV_PIN / PIV_PUK; see operator-credentials.example).
  provision-dev      Import dev key (per ceremony-config.json).
  provision-prod     Import prod key to all prod copies (per config).
  provision-env ID   Import one environment from config (e.g. dev, prod, staging).
  finalize           Validate manifest and print next steps for operators.
  export-pem         Opt-in export of dev/prod signing key to identity.pem (see below).
  destroy            Securely wipe ceremony workspace.
  run-offline        Full offline flow (generate + provision every environment in config).

  Global options (offline-generate, run-offline):
    --config PATH              Ceremony layout JSON (default: ./ceremony-config.json).
    --credentials-file PATH    Operator PIV_PIN / PIV_PUK file (see operator-credentials.example).

  export-pem <dev|prod> <path>
      <path> = dfx identity directory (writes identity.pem) or explicit *.pem file.
      Requires CEREMONY_EXPORT_PEM_I_UNDERSTAND=1 and offline-generate completed.

Environment:
  CEREMONY_ROOT          Workspace path (default: /run/realms-ceremony)
  CEREMONY_SIMULATE=1    Software-only mode for Docker tests (no YubiKey).
  CEREMONY_FORCE_OFFLINE=1   Skip online check (tests only).
  CEREMONY_FORCE_ONLINE=1    Skip offline requirement (tests only).
  CEREMONY_PIV_RESET=1     Reset PIV before import (destructive).
  CEREMONY_USE_TMPFS=0     Disable tmpfs mount (Docker tests).
  CEREMONY_EXPORT_PEM_I_UNDERSTAND=1   Required for export-pem (acknowledges PEM-on-disk risk).
  CEREMONY_CONFIG_FILE                 Ceremony layout JSON (default: ceremony-config.json).
  CEREMONY_OPERATOR_CREDENTIALS_FILE   Optional path to PIV_PIN/PIV_PUK file (same format as secrets file).

Copy public artifacts out before destroy:
  ${CEREMONY_ARTIFACTS}/manifest.json
  ${CEREMONY_SECRETS}/operator-credentials.txt  (record on paper first!)
EOF
}

cmd_online_setup() {
  log_banner "online-setup"
  log_detail "installs ykman, pcscd, icp-cli, dfx, openssl, jq (skipped when already in the live image)"
  log_detail "YubiKey touch: not applicable (no hardware operations yet)"
  ensure_root_or_sudo
  log_step "1" "install ceremony packages (Ubuntu 22.04 Desktop live)"
  export DEBIAN_FRONTEND=noninteractive
  local apt=(apt-get)
  if [[ "${EUID}" -ne 0 ]]; then
    apt=(sudo apt-get)
  fi
  if ceremony_packages_present && { command -v dfx >/dev/null 2>&1 || ceremony_dfx >/dev/null 2>&1; }; then
    log_detail "ceremony packages already present in this live image — skipping apt"
  else
    require_online
    prepare_live_session_for_apt
    "${apt[@]}" update -qq
    "${apt[@]}" install -y --no-install-recommends "${CEREMONY_APT_PACKAGES[@]}"
  fi
  if ! command -v icp >/dev/null 2>&1; then
    log_detail "icp-cli not installed — dfx is enough for HSM principal verification"
  fi
  install_dfx_for_ceremony
  if [[ ! -f "${CEREMONY_PKCS11_LIB}" ]]; then
    die "PKCS#11 library missing after install: ${CEREMONY_PKCS11_LIB} (expected package ykcs11)"
  fi
  command -v ykman >/dev/null 2>&1 || die "ykman not available after online-setup"
  command -v dfx >/dev/null 2>&1 || ceremony_dfx >/dev/null 2>&1 \
    || die "dfx not available after online-setup — run bin/install-dfx-local.sh"
  if [[ "${EUID}" -eq 0 ]]; then
    systemctl enable --now pcscd 2>/dev/null || service pcscd start 2>/dev/null || true
  else
    sudo systemctl enable --now pcscd 2>/dev/null || sudo service pcscd start 2>/dev/null || true
  fi
  ceremony_bootstrap
  write_manifest_header
  phase_marker "online-complete"
  log "online-setup complete"
  log_user "Disconnect Wi‑Fi/Ethernet, then run: ./realms-key-ceremony.sh check-offline"
  log_user "Next: ./realms-key-ceremony.sh offline-generate [--credentials-file PATH]"
}

cmd_check_offline() {
  log_banner "check-offline"
  log_detail "probes network — must be disconnected before key generation"
  ceremony_bootstrap
  require_offline
  phase_marker "offline-ready"
  log "offline check passed — safe to generate keys and provision YubiKeys"
}

parse_offline_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --config)
        [[ -n "${2:-}" ]] || die "--config requires a path"
        CEREMONY_CONFIG_FILE="${2}"
        shift 2
        ;;
      --credentials-file)
        [[ -n "${2:-}" ]] || die "--credentials-file requires a path"
        CEREMONY_OPERATOR_CREDENTIALS_FILE="${2}"
        shift 2
        ;;
      *) die "unknown option: $1" ;;
    esac
  done
}

cmd_offline_generate() {
  parse_offline_args "$@"
  log_banner "offline-generate"
  log_detail "creates signing keys + operator PINs in RAM — no YubiKey involved yet"
  log_detail "YubiKey touch: not applicable"
  ceremony_bootstrap
  if [[ "$(read_phase)" == "none" && "${CEREMONY_SIMULATE}" == "1" ]]; then
    write_manifest_header
    phase_marker "online-complete"
  fi
  require_phase_at_least "online-complete"
  require_offline
  require_cmd openssl
  write_manifest_header
  log_step "1" "prepare operator credentials (PIV PIN / PUK / management key)"
  prepare_operator_credentials
  log_user "Record ${CEREMONY_SECRETS}/operator-credentials.txt on paper when shown at finalize"
  local env_id
  log_step "2" "generate P-256 signing keys (one per environment in config)"
  while IFS= read -r env_id; do
    [[ -n "${env_id}" ]] || continue
    local key_path
    key_path="$(config_env_signing_key_path "${env_id}")"
    log_detail "${env_id} → $(basename "${key_path}")"
    generate_ec_key_pem "${key_path}"
  done < <(config_env_ids_ordered)
  phase_marker "generated"
  log "offline-generate complete"
  log_user "Provision YubiKeys next — dev first, then prod (see touch policy in logs):"
  log_user "  sudo ./realms-key-ceremony.sh provision-dev"
  log_user "  sudo ./realms-key-ceremony.sh provision-prod"
}

cmd_provision_env() {
  local env_id="${1:-}"
  [[ -n "${env_id}" ]] || die "usage: provision-env <environment-id>"
  config_env_exists "${env_id}" || die "unknown environment: ${env_id}"
  ceremony_bootstrap
  require_phase_at_least "generated"
  require_offline
  yubikey_require_tools
  if [[ "${CEREMONY_SIMULATE}" != "1" ]]; then
    log_detail "host tip: if ykman cannot see the key in a VM, run on host: sudo systemctl stop pcscd"
  fi
  provision_environment "${env_id}"
  verify_environment_principals_match "${env_id}"
  log "provision-env ${env_id} complete ($(config_env_copies "${env_id}") copy/copies)"
}

cmd_provision_dev() {
  cmd_provision_env "dev"
}

cmd_provision_prod() {
  cmd_provision_env "prod"
}

cmd_finalize() {
  log_banner "finalize"
  log_detail "validates manifest and prints operator next steps — no YubiKey touch"
  ceremony_bootstrap
  require_cmd jq
  local manifest="${CEREMONY_ARTIFACTS}/manifest.json"
  [[ -f "${manifest}" ]] || die "missing manifest — run provisioning first"
  local env_id copies count
  while IFS= read -r env_id; do
    [[ -n "${env_id}" ]] || continue
    jq -e --arg env "${env_id}" '.environments[$env].principal' "${manifest}" >/dev/null \
      || die "manifest missing principal for ${env_id}"
    copies="$(config_env_copies "${env_id}")"
    if [[ -f "${CEREMONY_ARTIFACTS}/${env_id}-serials.txt" ]]; then
      count="$(wc -l < "${CEREMONY_ARTIFACTS}/${env_id}-serials.txt" | tr -d ' ')"
      [[ "${count}" == "${copies}" ]] \
        || die "expected ${copies} ${env_id} serials, found ${count}"
    fi
  done < <(config_env_ids_ordered)
  if [[ "${CEREMONY_SIMULATE}" != "1" ]]; then
    {
      echo "# Register these HSM-backed dfx identities on operator workstations (PEM never on disk)."
      echo
      while IFS= read -r env_id; do
        [[ -n "${env_id}" ]] || continue
        echo "# ${env_id}: $(config_env_description "${env_id}")"
        echo "# YubiKey: $(config_env_yubikey_label "${env_id}") (touch $(config_env_touch_policy "${env_id}"), $(config_env_copies "${env_id}") copy/copies)"
        echo "dfx identity new realms-${env_id} \\"
        echo "  --hsm-key-id ${CEREMONY_HSM_KEY_ID} \\"
        echo "  --hsm-pkcs11-lib-path ${CEREMONY_PKCS11_LIB}"
        echo "export DFX_HSM_PIN='<PIV PIN from operator-credentials.txt>'"
        echo
      done < <(config_env_ids_ordered)
    } > "${CEREMONY_ARTIFACTS}/operator-dfx-identity.txt"
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

cmd_export_pem() {
  local env="${1:-}"
  local dest="${2:-}"
  [[ -n "${env}" && -n "${dest}" ]] \
    || die "usage: export-pem <environment-id> <destination-dir-or-identity.pem>"
  ceremony_bootstrap
  config_env_exists "${env}" || die "unknown environment: ${env}"
  require_phase_at_least "generated"
  require_offline
  export_signing_key_pem "${env}" "${dest}"
}

cmd_run_offline() {
  parse_offline_args "$@"
  log_banner "run-offline (full ceremony)"
  ceremony_bootstrap
  while IFS= read -r env_id; do
    [[ -n "${env_id}" ]] || continue
    log_detail "planned: provision-env ${env_id} ($(config_env_yubikey_label "${env_id}"), touch=$(config_env_touch_policy "${env_id}"))"
  done < <(config_env_ids_ordered)
  cmd_check_offline
  cmd_offline_generate
  local env_id
  while IFS= read -r env_id; do
    [[ -n "${env_id}" ]] || continue
    cmd_provision_env "${env_id}"
  done < <(config_env_ids_ordered)
  cmd_finalize
  log "run-offline complete"
  log_user "Copy artifacts off the machine, record PINs on paper, then: ./realms-key-ceremony.sh destroy"
}

main() {
  local cmd="${1:-}"
  case "${cmd}" in
    online-setup) cmd_online_setup ;;
    check-offline) cmd_check_offline ;;
    offline-generate) shift; cmd_offline_generate "$@" ;;
    provision-dev) cmd_provision_dev ;;
    provision-prod) cmd_provision_prod ;;
    provision-env) shift; cmd_provision_env "${1:-}" ;;
    finalize) cmd_finalize ;;
    export-pem) shift; cmd_export_pem "$@" ;;
    destroy) cmd_destroy ;;
    run-offline) shift; cmd_run_offline "$@" ;;
    -h|--help|help|"") usage ;;
    *) die "unknown command: ${cmd} (try --help)" ;;
  esac
}

main "$@"
