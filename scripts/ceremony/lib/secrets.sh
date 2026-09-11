#!/usr/bin/env bash
# Secret generation, tmpfs workspace, and secure destruction.
set -euo pipefail

random_digits() {
  local n="$1"
  openssl rand -hex 8 | tr -dc '0-9' | head -c "${n}"
}

random_hex() {
  local bytes="$1"
  openssl rand -hex "${bytes}"
}

init_secure_workspace() {
  mkdir_p "${CEREMONY_ROOT}" "${CEREMONY_SECRETS}" "${CEREMONY_ARTIFACTS}"

  if [[ "${CEREMONY_USE_TMPFS:-1}" == "1" ]] && [[ -w "$(dirname "${CEREMONY_ROOT}")" ]]; then
    if ! mountpoint -q "${CEREMONY_ROOT}" 2>/dev/null; then
      if [[ "${EUID}" -eq 0 ]] || command -v sudo >/dev/null 2>&1; then
        log "mounting tmpfs at ${CEREMONY_ROOT}"
        if [[ "${EUID}" -eq 0 ]]; then
          mount -t tmpfs -o size=64m,mode=700 tmpfs "${CEREMONY_ROOT}" || log "tmpfs mount failed (continuing on disk)"
        else
          sudo mount -t tmpfs -o size=64m,mode=700 tmpfs "${CEREMONY_ROOT}" || log "tmpfs mount failed (continuing on disk)"
        fi
        mkdir_p "${CEREMONY_SECRETS}" "${CEREMONY_ARTIFACTS}"
      else
        log "no sudo — using disk workspace (prefer tmpfs on the live USB)"
      fi
    fi
  fi
  chmod 700 "${CEREMONY_ROOT}" "${CEREMONY_SECRETS}" "${CEREMONY_ARTIFACTS}" 2>/dev/null || true
}

validate_piv_pin() {
  local pin="$1" label="$2"
  [[ "${#pin}" -ge 6 && "${#pin}" -le 8 ]] \
    || die "${label} must be 6–8 characters (got ${#pin})"
}

validate_piv_management_key() {
  local mgmt="$1"
  [[ "${#mgmt}" -eq 48 ]] || die "PIV_MANAGEMENT_KEY must be 48 hex chars (24 bytes)"
  [[ "${mgmt}" =~ ^[0-9a-fA-F]+$ ]] || die "PIV_MANAGEMENT_KEY must be hexadecimal"
}

write_operator_credentials_file() {
  local pin="$1" puk="$2" mgmt="$3" source_note="$4"
  umask 077
  cat > "${CEREMONY_SECRETS}/operator-credentials.txt" <<EOF
# Realms key ceremony — RECORD ON PAPER, then shred this file during destroy.
# ${source_note}
# $(date -u +%Y-%m-%dT%H:%M:%SZ)

PIV_PIN=${pin}
PIV_PUK=${puk}
PIV_MANAGEMENT_KEY=${mgmt}
EOF
  chmod 600 "${CEREMONY_SECRETS}/operator-credentials.txt"
  log "operator credentials written to ${CEREMONY_SECRETS}/operator-credentials.txt"
}

generate_operator_pins() {
  local pin puk mgmt
  pin="$(random_digits 6)"
  puk="$(random_digits 8)"
  mgmt="$(random_hex 24)"
  write_operator_credentials_file "${pin}" "${puk}" "${mgmt}" "Generated randomly"
}

load_operator_credentials_file() {
  local src="$1"
  [[ -f "${src}" ]] || die "credentials file not found: ${src}"
  [[ -r "${src}" ]] || die "credentials file not readable: ${src}"
  local pin="" puk="" mgmt=""
  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%%#*}"
    line="$(echo "${line}" | tr -d '[:space:]')"
    [[ -n "${line}" ]] || continue
    case "${line}" in
      PIV_PIN=*) pin="${line#PIV_PIN=}" ;;
      PIV_PUK=*) puk="${line#PIV_PUK=}" ;;
      PIV_MANAGEMENT_KEY=*) mgmt="${line#PIV_MANAGEMENT_KEY=}" ;;
      *) die "unknown line in credentials file (expected PIV_PIN/PIV_PUK/PIV_MANAGEMENT_KEY): ${line}" ;;
    esac
  done < "${src}"
  [[ -n "${pin}" ]] || die "credentials file missing PIV_PIN"
  [[ -n "${puk}" ]] || die "credentials file missing PIV_PUK"
  validate_piv_pin "${pin}" "PIV_PIN"
  validate_piv_pin "${puk}" "PIV_PUK"
  if [[ -z "${mgmt}" ]]; then
    mgmt="$(random_hex 24)"
    log "PIV_MANAGEMENT_KEY not set in file — generated random 24-byte key"
  else
    validate_piv_management_key "${mgmt}"
    mgmt="$(printf '%s' "${mgmt}" | tr '[:upper:]' '[:lower:]')"
  fi
  write_operator_credentials_file "${pin}" "${puk}" "${mgmt}" "Loaded from ${src}"
}

prepare_operator_credentials() {
  if [[ -n "${CEREMONY_OPERATOR_CREDENTIALS_FILE:-}" ]]; then
    load_operator_credentials_file "${CEREMONY_OPERATOR_CREDENTIALS_FILE}"
  else
    generate_operator_pins
  fi
}

load_operator_credentials() {
  [[ -f "${CEREMONY_SECRETS}/operator-credentials.txt" ]] || die "missing ${CEREMONY_SECRETS}/operator-credentials.txt — run offline-generate first"
  # shellcheck disable=SC1090
  source "${CEREMONY_SECRETS}/operator-credentials.txt"
  [[ -n "${PIV_PIN:-}" && -n "${PIV_PUK:-}" && -n "${PIV_MANAGEMENT_KEY:-}" ]] \
    || die "operator-credentials.txt is incomplete"
}

generate_ec_key_pem() {
  local out="$1"
  openssl ecparam -name "${CEREMONY_EC_CURVE}" -genkey -noout -out "${out}"
  chmod 600 "${out}"
}

signing_key_pem_path() {
  local env_id="$1"
  if declare -F config_env_signing_key_path >/dev/null 2>&1 && config_env_exists "${env_id}" 2>/dev/null; then
    config_env_signing_key_path "${env_id}"
    return 0
  fi
  case "${env_id}" in
    dev) printf '%s/dev-signing-key.pem\n' "${CEREMONY_SECRETS}" ;;
    prod) printf '%s/prod-signing-key.pem\n' "${CEREMONY_SECRETS}" ;;
    *) die "unknown environment for signing key: ${env_id}" ;;
  esac
}

resolve_dfx_identity_pem_path() {
  local dest="$1"
  if [[ "${dest}" == *.pem ]]; then
    mkdir_p "$(dirname "${dest}")"
    printf '%s\n' "${dest}"
    return 0
  fi
  mkdir_p "${dest}"
  printf '%s/identity.pem\n' "${dest%/}"
}

install_signing_key_pem_copy() {
  local src="$1"
  local dest_pem="$2"
  [[ -f "${src}" ]] || die "missing ${src} — run offline-generate first"
  install -m 600 "${src}" "${dest_pem}"
}

shred_path() {
  local path="$1"
  [[ -e "${path}" ]] || return 0
  if command -v shred >/dev/null 2>&1; then
    shred -u -z -n 3 "${path}" 2>/dev/null || rm -f "${path}"
  else
    rm -f "${path}"
  fi
}

destroy_ceremony_state() {
  log "destroying ceremony workspace"
  if [[ -d "${CEREMONY_SECRETS}" ]]; then
    find "${CEREMONY_SECRETS}" -type f -print0 2>/dev/null | while IFS= read -r -d '' f; do
      shred_path "${f}"
    done
  fi
  if [[ -d "${CEREMONY_ARTIFACTS}" ]]; then
    # Manifest may be copied out before destroy; shred local copy anyway.
    find "${CEREMONY_ARTIFACTS}" -type f -print0 2>/dev/null | while IFS= read -r -d '' f; do
      shred_path "${f}"
    done
  fi
  rm -f "${CEREMONY_ROOT}/.phase" 2>/dev/null || true
  if mountpoint -q "${CEREMONY_ROOT}" 2>/dev/null; then
    if [[ "${EUID}" -eq 0 ]]; then
      umount "${CEREMONY_ROOT}" || true
    elif command -v sudo >/dev/null 2>&1; then
      sudo umount "${CEREMONY_ROOT}" || true
    fi
  fi
  history -c 2>/dev/null || true
  log "ceremony workspace destroyed"
}
