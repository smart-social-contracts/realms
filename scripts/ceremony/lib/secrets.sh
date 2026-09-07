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

generate_operator_pins() {
  local pin puk mgmt
  # YubiKey PIV: PIN 6–8 digits, PUK 8 digits, management key 24 bytes (48 hex).
  pin="$(random_digits 6)"
  puk="$(random_digits 8)"
  mgmt="$(random_hex 24)"

  umask 077
  cat > "${CEREMONY_SECRETS}/operator-credentials.txt" <<EOF
# Realms key ceremony — RECORD ON PAPER, then shred this file during destroy.
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

PIV_PIN=${pin}
PIV_PUK=${puk}
PIV_MANAGEMENT_KEY=${mgmt}
EOF
  chmod 600 "${CEREMONY_SECRETS}/operator-credentials.txt"
  log "operator PIN/PUK/management key written to ${CEREMONY_SECRETS}/operator-credentials.txt"
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
