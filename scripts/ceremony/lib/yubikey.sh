#!/usr/bin/env bash
# YubiKey PIV provisioning (real hardware or simulate mode for CI/Docker).
set -euo pipefail

_sim_root() {
  printf '%s/sim-yubikeys\n' "${CEREMONY_ROOT}"
}

_sim_serial_for_env() {
  local env="$1"
  local copy="${2:-}"
  case "${env}" in
    dev) printf 'sim-dev-0001\n' ;;
    prod)
      if [[ -n "${copy}" ]]; then
        printf 'sim-prod-%04d\n' "${copy}"
      else
        printf 'sim-prod-0001\n'
      fi
      ;;
    *) die "unknown env for simulate serial: ${env}" ;;
  esac
}

yubikey_require_tools() {
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    return 0
  fi
  require_cmd ykman
  require_cmd pcscd
  if [[ ! -f "${CEREMONY_PKCS11_LIB}" ]]; then
    die "PKCS#11 library not found: ${CEREMONY_PKCS11_LIB} (install ykcs11)"
  fi
}

yubikey_list_devices() {
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    find "$(_sim_root)" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort || true
    return 0
  fi
  ykman info 2>/dev/null | awk '/Serial number:/ {print $3}'
}

yubikey_wait_for_device() {
  local prompt="${1:-Insert a YubiKey and press Enter...}"
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    return 0
  fi
  printf '%s\n' "${prompt}" >&2
  read -r _
  local serial
  serial="$(ykman info 2>/dev/null | awk '/Serial number:/ {print $3}')"
  [[ -n "${serial}" ]] || die "no YubiKey detected"
  printf '%s' "${serial}"
}

_reset_sim_device() {
  local serial="$1"
  local dir="$(_sim_root)/${serial}"
  rm -rf "${dir}"
  mkdir_p "${dir}"
}

_sim_import_key() {
  local serial="$1"
  local key_pem="$2"
  local touch_policy="$3"
  local dir="$(_sim_root)/${serial}"
  mkdir_p "${dir}"
  cp "${key_pem}" "${dir}/slot-${CEREMONY_SLOT}.pem"
  printf '%s\n' "${touch_policy}" > "${dir}/touch-policy"
  openssl ec -in "${key_pem}" -pubout -out "${dir}/slot-${CEREMONY_SLOT}.pub.pem" 2>/dev/null
}

_piv_reset_if_requested() {
  local serial="$1"
  if [[ "${CEREMONY_PIV_RESET:-0}" != "1" ]]; then
    return 0
  fi
  log "PIV reset requested for serial ${serial} (destructive)"
  ykman --device "${serial}" piv reset -f
}

_configure_piv_access() {
  local serial="$1"
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    return 0
  fi
  load_operator_credentials
  ykman --device "${serial}" piv access change-pin -P "${PIV_PIN}" 2>/dev/null \
    || ykman --device "${serial}" piv access change-pin --pin 123456 -P "${PIV_PIN}"
  ykman --device "${serial}" piv access change-puk -p "${PIV_PUK}" 2>/dev/null \
    || ykman --device "${serial}" piv access change-puk --puk 12345678 -p "${PIV_PUK}"
  ykman --device "${serial}" piv access change-management-key -m "${PIV_MANAGEMENT_KEY}" 2>/dev/null \
    || ykman --device "${serial}" piv access change-management-key \
      --management-key 010203040506070801020304050607080102030405060708 \
      -m "${PIV_MANAGEMENT_KEY}"
}

_import_signing_key() {
  local serial="$1"
  local key_pem="$2"
  local touch_policy="$3"
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    _sim_import_key "${serial}" "${key_pem}" "${touch_policy}"
    return 0
  fi
  load_operator_credentials
  _piv_reset_if_requested "${serial}"
  _configure_piv_access "${serial}"
  ykman --device "${serial}" piv keys import "${CEREMONY_SLOT}" "${key_pem}" \
    -P "${PIV_PIN}" \
    -m "${PIV_MANAGEMENT_KEY}" \
    --algorithm eccp256 \
    --touch-policy "${touch_policy}" \
    --pin-policy once
  ykman --device "${serial}" piv export-certificate "${CEREMONY_SLOT}" \
    "${CEREMONY_ARTIFACTS}/piv-${serial}-${CEREMONY_SLOT}.crt" 2>/dev/null \
    || log "no certificate on slot ${CEREMONY_SLOT} (expected for imported keys)"
}

public_key_pem_from_private() {
  local key_pem="$1"
  local out="$2"
  openssl ec -in "${key_pem}" -pubout -out "${out}" 2>/dev/null
}

export_public_key_pem() {
  local serial="$1"
  local out="$2"
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    cp "$(_sim_root)/${serial}/slot-${CEREMONY_SLOT}.pub.pem" "${out}"
    return 0
  fi
  load_operator_credentials
  ykman --device "${serial}" piv keys export "${CEREMONY_SLOT}" "${out}"
}

_principal_from_pem() {
  local key_pem="$1"
  local name="$2"
  local tmp_home principal
  tmp_home="$(mktemp -d)"
  if command -v icp >/dev/null 2>&1; then
    HOME="${tmp_home}" DO_NOT_TRACK=1 icp identity import "${name}" \
      --from-pem "${key_pem}" --storage plaintext >/dev/null 2>&1
    principal="$(HOME="${tmp_home}" DO_NOT_TRACK=1 icp identity principal --identity "${name}" 2>/dev/null)"
  elif command -v dfx >/dev/null 2>&1; then
    HOME="${tmp_home}" dfx identity import "${name}" "${key_pem}" --storage-mode plaintext >/dev/null
    principal="$(HOME="${tmp_home}" dfx identity get-principal --identity "${name}")"
  else
    rm -rf "${tmp_home}"
    die "icp or dfx is required to derive IC principals"
  fi
  rm -rf "${tmp_home}"
  [[ -n "${principal}" ]] || die "empty principal for ${name}"
  printf '%s' "${principal}"
}

_principal_from_hsm() {
  local serial="$1"
  local name="$2"
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    _principal_from_pem "$(_sim_root)/${serial}/slot-${CEREMONY_SLOT}.pem" "${name}"
    return 0
  fi
  if ! command -v dfx >/dev/null 2>&1; then
    die "dfx required to derive principal from YubiKey HSM identity"
  fi
  load_operator_credentials
  local tmp_home
  tmp_home="$(mktemp -d)"
  export DFX_HSM_PIN="${PIV_PIN}"
  export YKCS11_DEVICE="${serial}"
  HOME="${tmp_home}" dfx identity new "${name}" \
    --storage-mode password-protected \
    --hsm-key-id "${CEREMONY_HSM_KEY_ID}" \
    --hsm-pkcs11-lib-path "${CEREMONY_PKCS11_LIB}" \
    </dev/null 2>/dev/null || true
  # password-protected may prompt — use plaintext stub for ceremony export only
  HOME="${tmp_home}" dfx identity new "${name}" \
    --storage-mode plaintext \
    --hsm-key-id "${CEREMONY_HSM_KEY_ID}" \
    --hsm-pkcs11-lib-path "${CEREMONY_PKCS11_LIB}"
  HOME="${tmp_home}" DFX_HSM_PIN="${PIV_PIN}" dfx identity get-principal --identity "${name}"
  rm -rf "${tmp_home}"
}

provision_dev_yubikey() {
  local key_pem="${CEREMONY_SECRETS}/dev-signing-key.pem"
  [[ -f "${key_pem}" ]] || die "missing ${key_pem}"
  local serial
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    serial="$(_sim_serial_for_env dev)"
    _reset_sim_device "${serial}"
  else
    serial="$(yubikey_wait_for_device "Insert the DEV YubiKey 5C Nano, then press Enter")"
  fi
  log "provisioning DEV YubiKey serial=${serial} touch=never"
  local pub="${CEREMONY_ARTIFACTS}/dev-public.pem"
  public_key_pem_from_private "${key_pem}" "${pub}"
  _import_signing_key "${serial}" "${key_pem}" never
  local principal
  principal="$(_principal_from_hsm "${serial}" "realms-ceremony-dev")"
  update_manifest "dev" "${principal}" "${pub}" "never" "${serial}"
  printf '%s\n' "${serial}" > "${CEREMONY_ARTIFACTS}/dev-serial.txt"
  log "DEV principal: ${principal}"
}

provision_prod_yubikey_copy() {
  local copy_num="$1"
  local key_pem="${CEREMONY_SECRETS}/prod-signing-key.pem"
  [[ -f "${key_pem}" ]] || die "missing ${key_pem}"
  local serial
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    serial="$(_sim_serial_for_env prod "${copy_num}")"
    _reset_sim_device "${serial}"
  else
    serial="$(yubikey_wait_for_device "Insert PROD YubiKey copy ${copy_num}/3, then press Enter")"
  fi
  log "provisioning PROD YubiKey copy ${copy_num}/3 serial=${serial} touch=cached"
  local pub="${CEREMONY_ARTIFACTS}/prod-public-${copy_num}.pem"
  if [[ "${copy_num}" == "1" ]]; then
    public_key_pem_from_private "${key_pem}" "${pub}"
  else
    cp "${CEREMONY_ARTIFACTS}/prod-public-1.pem" "${pub}"
  fi
  _import_signing_key "${serial}" "${key_pem}" cached
  local principal
  principal="$(_principal_from_hsm "${serial}" "realms-ceremony-prod-${copy_num}")"
  # All copies must share the same principal.
  if [[ -f "${CEREMONY_ARTIFACTS}/prod-principal.txt" ]]; then
    local expected
    expected="$(cat "${CEREMONY_ARTIFACTS}/prod-principal.txt")"
    [[ "${principal}" == "${expected}" ]] \
      || die "prod copy ${copy_num} principal mismatch (expected ${expected}, got ${principal})"
  else
    printf '%s\n' "${principal}" > "${CEREMONY_ARTIFACTS}/prod-principal.txt"
    update_manifest "prod" "${principal}" "${pub}" "cached" "${serial}"
  fi
  printf '%s\n' "${serial}" >> "${CEREMONY_ARTIFACTS}/prod-serials.txt"
  log "PROD copy ${copy_num} principal: ${principal}"
}

verify_prod_principals_match() {
  local key_pem="${CEREMONY_SECRETS}/prod-signing-key.pem"
  [[ -f "${key_pem}" ]] || return 0
  local expected
  expected="$(cat "${CEREMONY_ARTIFACTS}/prod-principal.txt" 2>/dev/null || true)"
  [[ -n "${expected}" ]] || die "prod principal not recorded"
  local p
  p="$(_principal_from_pem "${key_pem}" "realms-ceremony-prod-verify")"
  [[ "${p}" == "${expected}" ]] || die "prod key PEM principal mismatch"
  log "prod principal consistency check OK"
}
