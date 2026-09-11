#!/usr/bin/env bash
# Shared helpers for the Realms YubiKey key ceremony.
set -euo pipefail

CEREMONY_VERSION="1.0.0"
CEREMONY_SLOT="${CEREMONY_SLOT:-9c}"
# YubiKey PIV slot 9c → PKCS#11 object id 02 (dfx --hsm-key-id).
CEREMONY_HSM_KEY_ID="${CEREMONY_HSM_KEY_ID:-02}"
CEREMONY_PKCS11_LIB="${CEREMONY_PKCS11_LIB:-/usr/lib/x86_64-linux-gnu/libykcs11.so}"
CEREMONY_EC_CURVE="${CEREMONY_EC_CURVE:-prime256v1}"

# Workspace defaults (override for tests).
CEREMONY_ROOT="${CEREMONY_ROOT:-/run/realms-ceremony}"
CEREMONY_ARTIFACTS="${CEREMONY_ARTIFACTS:-${CEREMONY_ROOT}/artifacts}"
CEREMONY_SECRETS="${CEREMONY_SECRETS:-${CEREMONY_ROOT}/secrets}"
CEREMONY_SIMULATE="${CEREMONY_SIMULATE:-0}"
CEREMONY_FORCE_ONLINE="${CEREMONY_FORCE_ONLINE:-0}"
CEREMONY_FORCE_OFFLINE="${CEREMONY_FORCE_OFFLINE:-0}"

log() {
  printf '[ceremony] %s\n' "$*" >&2
}

log_banner() {
  local title="$1"
  printf '\n[ceremony] ═══ %s ═══\n' "${title}" >&2
}

log_step() {
  local n="$1"
  local msg="$2"
  printf '[ceremony]   %s. %s\n' "${n}" "${msg}" >&2
}

log_detail() {
  printf '[ceremony]      → %s\n' "$*" >&2
}

log_user() {
  printf '[ceremony] ► ACTION: %s\n' "$*" >&2
}

log_no_touch() {
  log_detail "YubiKey touch: not required for this step"
}

touch_policy_describe() {
  local policy="$1"
  case "${policy}" in
    never)
      printf '%s' "no touch when signing (dev / unattended deploys)"
      ;;
    cached)
      printf '%s' "touch once per session when signing (~15s cache after each use)"
      ;;
    always)
      printf '%s' "touch the YubiKey on every signing operation"
      ;;
    *)
      printf '%s' "policy ${policy}"
      ;;
  esac
}

touch_required_for_hsm_verify() {
  local policy="$1"
  [[ "${policy}" != "never" ]]
}

log_touch_policy() {
  local policy="$1"
  log_detail "touch policy: ${policy} — $(touch_policy_describe "${policy}")"
}

die() {
  log "ERROR: $*"
  exit 1
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "required command not found: ${cmd}"
}

ensure_root_or_sudo() {
  if [[ "${EUID}" -eq 0 ]]; then
    return 0
  fi
  if command -v sudo >/dev/null 2>&1; then
    return 0
  fi
  die "online-setup needs root or sudo for apt"
}

mkdir_p() {
  install -d -m 700 "$@"
}

phase_marker() {
  local name="$1"
  printf '%s\n' "${name}" > "${CEREMONY_ROOT}/.phase"
  log "phase -> ${name}"
}

read_phase() {
  if [[ -f "${CEREMONY_ROOT}/.phase" ]]; then
    cat "${CEREMONY_ROOT}/.phase"
  else
    printf 'none\n'
  fi
}

require_phase_at_least() {
  local expected="$1"
  local current
  current="$(read_phase)"
  case "${current}" in
    none)
      [[ "${expected}" == "online-complete" ]] && return 0
      ;;
    online-complete)
      [[ "${expected}" == "online-complete" || "${expected}" == "offline-ready" ]] && return 0
      ;;
    offline-ready)
      [[ "${expected}" == "online-complete" || "${expected}" == "offline-ready" || "${expected}" == "generated" ]] && return 0
      ;;
    generated)
      return 0
      ;;
    finalized)
      return 0
      ;;
  esac
  die "ceremony phase is '${current}', expected at least '${expected}' (run earlier phases first)"
}

write_manifest_header() {
  local path="${CEREMONY_ARTIFACTS}/manifest.json"
  mkdir_p "${CEREMONY_ARTIFACTS}"
  if [[ ! -f "${path}" ]]; then
    jq -n \
      --arg version "${CEREMONY_VERSION}" \
      --arg slot "${CEREMONY_SLOT}" \
      --arg hsm_key_id "${CEREMONY_HSM_KEY_ID}" \
      --arg pkcs11_lib "${CEREMONY_PKCS11_LIB}" \
      --arg created "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '{
        ceremony_version: $version,
        piv_slot: $slot,
        pkcs11_key_id: $hsm_key_id,
        pkcs11_lib: $pkcs11_lib,
        created_at: $created,
        simulate: false,
        environments: {}
      }' > "${path}"
  fi
}

update_manifest() {
  local env_name="$1"
  local principal="$2"
  local pubkey_path="$3"
  local touch_policy="$4"
  local serial="${5:-}"
  local path="${CEREMONY_ARTIFACTS}/manifest.json"
  local pubkey_pem
  pubkey_pem="$(cat "${pubkey_path}")"
  local tmp
  tmp="$(mktemp)"
  jq \
    --arg env "${env_name}" \
    --arg principal "${principal}" \
    --arg pubkey "${pubkey_pem}" \
    --arg touch "${touch_policy}" \
    --arg serial "${serial}" \
    --argjson simulate "${CEREMONY_SIMULATE}" \
    '.simulate = $simulate
     | .environments[$env] = {
         principal: $principal,
         public_key_pem: $pubkey,
         touch_policy: $touch,
         yubikey_serial: $serial,
         piv_slot: "'"${CEREMONY_SLOT}"'",
         pkcs11_key_id: "'"${CEREMONY_HSM_KEY_ID}"'"
       }' \
    "${path}" > "${tmp}"
  mv "${tmp}" "${path}"
  chmod 600 "${path}"
}
