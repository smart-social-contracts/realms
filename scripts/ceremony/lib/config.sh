#!/usr/bin/env bash
# Load ceremony-config.json (environments, YubiKey layout, PIV settings).
set -euo pipefail

CEREMONY_CONFIG_FILE="${CEREMONY_CONFIG_FILE:-}"

_config_path() {
  if [[ -n "${CEREMONY_CONFIG_FILE}" && -f "${CEREMONY_CONFIG_FILE}" ]]; then
    printf '%s' "${CEREMONY_CONFIG_FILE}"
    return 0
  fi
  if [[ -f "${SCRIPT_DIR}/ceremony-config.json" ]]; then
    printf '%s' "${SCRIPT_DIR}/ceremony-config.json"
    return 0
  fi
  die "ceremony config not found — set CEREMONY_CONFIG_FILE or add ${SCRIPT_DIR}/ceremony-config.json"
}

_config_jq_env() {
  local env_id="$1"
  local filter="$2"
  jq -r --arg id "${env_id}" "${filter}" "$(_config_path)"
}

load_ceremony_config() {
  require_cmd jq
  local cfg
  cfg="$(_config_path)"
  jq -e '.environments | length > 0' "${cfg}" >/dev/null \
    || die "config must define at least one environment: ${cfg}"

  local id touch copies
  while IFS= read -r id; do
    [[ -n "${id}" ]] || continue
    [[ "${id}" =~ ^[a-z][a-z0-9_-]*$ ]] \
      || die "environment id must be lowercase alphanumeric (got: ${id})"
    touch="$(config_env_touch_policy "${id}")"
    [[ "${touch}" == "never" || "${touch}" == "always" || "${touch}" == "cached" ]] \
      || die "invalid touch_policy for ${id} (use never|always|cached)"
    copies="$(config_env_copies "${id}")"
    [[ "${copies}" =~ ^[0-9]+$ && "${copies}" -ge 1 ]] \
      || die "yubikey.copies must be >= 1 for ${id}"
  done < <(config_env_ids_ordered)

  CEREMONY_SLOT="$(jq -r '.piv.slot // "9c"' "${cfg}")"
  CEREMONY_HSM_KEY_ID="$(jq -r '.piv.pkcs11_key_id // "02"' "${cfg}")"
  CEREMONY_PKCS11_LIB="$(jq -r '.piv.pkcs11_lib // "/usr/lib/x86_64-linux-gnu/libykcs11.so"' "${cfg}")"
  CEREMONY_EC_CURVE="$(jq -r '.piv.ec_curve // "prime256v1"' "${cfg}")"
  CEREMONY_PIN_POLICY="$(jq -r '.piv.pin_policy // "once"' "${cfg}")"
  case "${CEREMONY_PIN_POLICY}" in
    never|once|always) ;;
    *) die "invalid piv.pin_policy '${CEREMONY_PIN_POLICY}' (use never|once|always)" ;;
  esac

  mkdir_p "${CEREMONY_ARTIFACTS}"
  cp "${cfg}" "${CEREMONY_ARTIFACTS}/ceremony-config.json"
  chmod 600 "${CEREMONY_ARTIFACTS}/ceremony-config.json"
  log "ceremony config: ${cfg} ($(config_env_count) environment(s))"
  local env_id touch copies label
  while IFS= read -r env_id; do
    [[ -n "${env_id}" ]] || continue
    touch="$(config_env_touch_policy "${env_id}")"
    copies="$(config_env_copies "${env_id}")"
    label="$(config_env_yubikey_label "${env_id}")"
    log_detail "${env_id}: ${label}, ${copies} key(s), touch=${touch} ($(touch_policy_describe "${touch}"))"
  done < <(config_env_ids_ordered)
}

config_env_count() {
  jq '.environments | length' "$(_config_path)"
}

config_env_ids_ordered() {
  jq -r '.environments[].id' "$(_config_path)"
}

config_env_touch_policy() {
  _config_jq_env "$1" '.environments[] | select(.id == $id) | .yubikey.touch_policy'
}

config_env_copies() {
  _config_jq_env "$1" '.environments[] | select(.id == $id) | .yubikey.copies'
}

config_env_yubikey_label() {
  _config_jq_env "$1" '.environments[] | select(.id == $id) | .yubikey.label'
}

config_env_description() {
  _config_jq_env "$1" '.environments[] | select(.id == $id) | .description // ""'
}

config_env_signing_key_basename() {
  _config_jq_env "$1" '.environments[] | select(.id == $id) | .signing_key'
}

config_env_signing_key_path() {
  printf '%s/%s' "${CEREMONY_SECRETS}" "$(config_env_signing_key_basename "$1")"
}

config_env_export_private_pem() {
  local v
  v="$(_config_jq_env "$1" '.environments[] | select(.id == $id) | .export_private_pem // false')"
  [[ "${v}" == "true" ]]
}

config_env_exists() {
  local env_id="$1"
  [[ "$(jq -r --arg id "${env_id}" '[.environments[] | select(.id == $id)] | length' "$(_config_path)")" == "1" ]]
}

config_env_insert_prompt() {
  local env_id="$1"
  local copy_num="${2:-1}"
  local total label touch
  total="$(config_env_copies "${env_id}")"
  label="$(config_env_yubikey_label "${env_id}")"
  touch="$(config_env_touch_policy "${env_id}")"
  if [[ "${total}" == "1" ]]; then
    printf 'Insert %s for %s (touch policy: %s), then press Enter' \
      "${label}" "${env_id}" "${touch}"
  else
    printf 'Insert %s for %s copy %s/%s (touch policy: %s), then press Enter' \
      "${label}" "${env_id}" "${copy_num}" "${total}" "${touch}"
  fi
}
