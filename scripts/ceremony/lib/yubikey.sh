#!/usr/bin/env bash
# YubiKey PIV provisioning (real hardware or simulate mode for CI/Docker).
set -euo pipefail

_sim_root() {
  printf '%s/sim-yubikeys\n' "${CEREMONY_ROOT}"
}

_sim_serial_for_env() {
  local env_id="$1"
  local copy="${2:-1}"
  printf 'sim-%s-%04d\n' "${env_id}" "${copy}"
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
  log_no_touch
  log_user "${prompt}"
  read -r _
  local serial
  serial="$(ykman info 2>/dev/null | awk '/Serial number:/ {print $3}')"
  [[ -n "${serial}" ]] || die "no YubiKey detected — unplug/replug, stop host pcscd if in a VM, then retry"
  log_detail "detected YubiKey serial ${serial}"
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

_piv_factory_pin() { printf '%s' "123456"; }
_piv_factory_puk() { printf '%s' "12345678"; }
_piv_factory_mgmt() { printf '%s' "010203040506070801020304050607080102030405060708"; }

_configure_piv_access() {
  local serial="$1"
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    return 0
  fi
  load_operator_credentials
  local factory_pin factory_puk factory_mgmt
  factory_pin="$(_piv_factory_pin)"
  factory_puk="$(_piv_factory_puk)"
  factory_mgmt="$(_piv_factory_mgmt)"

  log_detail "[PIV] access setup on serial ${serial} (PIN / PUK / management key)"
  log_no_touch
  log_detail "[PIV] uses ceremony PIN from operator-credentials (not typed interactively)"

  # ykman: -P/-p = current, -n = new (never omit — prompts interactively).
  if ykman --device "${serial}" piv access change-pin \
      -P "${factory_pin}" -n "${PIV_PIN}" >/dev/null 2>&1; then
    log_detail "PIV PIN set from factory default"
  else
    log_detail "PIV PIN unchanged (may already be ceremony PIN)"
  fi

  if ykman --device "${serial}" piv access change-puk \
      -p "${factory_puk}" -n "${PIV_PUK}" >/dev/null 2>&1; then
    log_detail "PIV PUK set from factory default"
  elif ykman --device "${serial}" piv access change-puk \
      -p "${PIV_PUK}" -n "${PIV_PUK}" >/dev/null 2>&1; then
    log_detail "PIV PUK already set to ceremony value"
  else
    log "warning: could not set PIV PUK (may already be customized)"
  fi

  if ykman --device "${serial}" piv access change-management-key \
      -m "${factory_mgmt}" -n "${PIV_MANAGEMENT_KEY}" -a AES192 >/dev/null 2>&1; then
    log_detail "PIV management key set from factory default"
  else
    log_detail "management key unchanged (may already be ceremony key)"
  fi
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

  log_detail "[import] signing key → PIV slot ${CEREMONY_SLOT} (serial ${serial})"
  log_no_touch
  log_touch_policy "${touch_policy}"
  log_detail "[import] configures future signing behavior; physical touch is not used during import"

  # Algorithm is inferred from the PEM (ECC P-256); apt ykman has no --algorithm on import.
  ykman --device "${serial}" piv keys import "${CEREMONY_SLOT}" "${key_pem}" \
    -P "${PIV_PIN}" \
    -m "${PIV_MANAGEMENT_KEY}" \
    --touch-policy "${touch_policy}" \
    --pin-policy once
  log_detail "key import complete"

  ykman --device "${serial}" piv export-certificate "${CEREMONY_SLOT}" \
    "${CEREMONY_ARTIFACTS}/piv-${serial}-${CEREMONY_SLOT}.crt" 2>/dev/null \
    || log_detail "no X.509 certificate on slot ${CEREMONY_SLOT} (normal for imported keys)"
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

_verify_yubikey_public_key_matches() {
  local serial="$1"
  local key_pem="$2"
  local on_key expected fp_on fp_exp
  on_key="$(mktemp)"
  expected="$(mktemp)"
  export_public_key_pem "${serial}" "${on_key}"
  public_key_pem_from_private "${key_pem}" "${expected}"
  fp_on="$(openssl ec -in "${on_key}" -pubin -pubout 2>/dev/null | openssl md5)"
  fp_exp="$(openssl ec -in "${expected}" -pubin -pubout 2>/dev/null | openssl md5)"
  rm -f "${on_key}" "${expected}"
  [[ "${fp_on}" == "${fp_exp}" ]] || die "YubiKey public key does not match offline signing key"
  log_detail "YubiKey public key matches offline PEM"
}

_principal_from_hsm_dfx() {
  local serial="$1"
  local name="$2"
  local touch_policy="${3:-never}"
  ceremony_ensure_dfx
  ceremony_dfx_env
  load_operator_credentials
  local tmp_home errfile principal
  tmp_home="$(mktemp -d)"
  errfile="$(mktemp)"

  log_detail "[principal] derive IC principal via PKCS#11 (serial ${serial}, key id ${CEREMONY_HSM_KEY_ID})"
  if touch_required_for_hsm_verify "${touch_policy}"; then
    log_user "Touch the YubiKey when the LED blinks — required to verify the HSM key (touch policy: ${touch_policy})"
  else
    log_no_touch
    log_detail "[principal] touch policy is never — leave the key alone; this step is fully automatic"
  fi

  export DFX_HSM_PIN="${PIV_PIN}"
  export YKCS11_DEVICE="${serial}"
  if ! HOME="${tmp_home}" DFX_HSM_PIN="${PIV_PIN}" YKCS11_DEVICE="${serial}" \
    ceremony_run_dfx identity new "${name}" \
    --storage-mode plaintext \
    --hsm-key-id "${CEREMONY_HSM_KEY_ID}" \
    --hsm-pkcs11-lib-path "${CEREMONY_PKCS11_LIB}" 2>"${errfile}"; then
    if grep -qiE 'CKR_PIN_LOCKED|PIN_LOCKED|0xa4' "${errfile}"; then
      rm -rf "${tmp_home}" "${errfile}"
      die "YubiKey PIV PIN is locked (CKR_PIN_LOCKED). Unblock with PUK from operator-credentials.txt: ykman --device ${serial} piv access unblock-pin -p \"\$PIV_PUK\" -n \"\$PIV_PIN\""
    fi
    grep -q 'Identity already exists' "${errfile}" \
      || { cat "${errfile}" >&2; rm -rf "${tmp_home}" "${errfile}"; return 1; }
  fi
  rm -f "${errfile}"

  if ! principal="$(HOME="${tmp_home}" DFX_HSM_PIN="${PIV_PIN}" YKCS11_DEVICE="${serial}" \
    ceremony_run_dfx identity get-principal --identity "${name}" 2>&1)"; then
    printf '%s\n' "${principal}" >&2
    rm -rf "${tmp_home}"
    return 1
  fi
  rm -rf "${tmp_home}"
  [[ -n "${principal}" ]] || return 1
  printf '%s' "${principal}"
}

_principal_from_hsm() {
  local serial="$1"
  local name="$2"
  local touch_policy="${3:-never}"
  local key_pem="$4"
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    _principal_from_pem "$(_sim_root)/${serial}/slot-${CEREMONY_SLOT}.pem" "${name}"
    return 0
  fi
  [[ -f "${key_pem}" ]] || die "missing signing key PEM for HSM verify: ${key_pem}"
  _verify_yubikey_public_key_matches "${serial}" "${key_pem}"

  local principal=""
  if principal="$(_principal_from_hsm_dfx "${serial}" "${name}" "${touch_policy}" 2>/dev/null)" \
    && [[ -n "${principal}" ]]; then
    log_detail "principal derived via dfx HSM: ${principal}"
    printf '%s' "${principal}"
    return 0
  fi

  log "warning: dfx HSM principal failed — public key on YubiKey already verified; using PEM-derived IC principal"
  log_detail "tip: touch the YubiKey in the VM window when dfx prompts (prod touch policy: cached)"
  principal="$(_principal_from_pem "${key_pem}" "${name}")"
  log_detail "principal derived successfully: ${principal}"
  printf '%s' "${principal}"
}

_provision_environment_copy() {
  local env_id="$1"
  local copy_num="$2"
  local copies touch key_pem serial pub principal expected label
  copies="$(config_env_copies "${env_id}")"
  touch="$(config_env_touch_policy "${env_id}")"
  label="$(config_env_yubikey_label "${env_id}")"
  key_pem="$(config_env_signing_key_path "${env_id}")"
  [[ -f "${key_pem}" ]] || die "missing ${key_pem} — run offline-generate first"

  if [[ "${copies}" == "1" ]]; then
    log_banner "Provision ${env_id} — ${label}"
  else
    log_banner "Provision ${env_id} — ${label} (copy ${copy_num}/${copies})"
  fi
  log_touch_policy "${touch}"
  if [[ "${touch}" == "never" ]]; then
    log_detail "during this provision: no YubiKey touch at any step"
  elif [[ "${touch}" == "cached" ]]; then
    log_detail "during this provision: touch only in step (c) when verifying the HSM key"
    log_detail "after ceremony: touch once per signing session when deploying/signing"
  else
    log_detail "during this provision: touch required in step (c) when verifying the HSM key"
    log_detail "after ceremony: touch on every signing operation"
  fi

  log_step "1" "insert the correct YubiKey"
  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    serial="$(_sim_serial_for_env "${env_id}" "${copy_num}")"
    _reset_sim_device "${serial}"
    log_detail "simulate mode — virtual YubiKey ${serial}"
  else
    serial="$(yubikey_wait_for_device "$(config_env_insert_prompt "${env_id}" "${copy_num}")")"
  fi

  pub="${CEREMONY_ARTIFACTS}/${env_id}-public.pem"
  if [[ "${copy_num}" == "1" ]]; then
    log_step "2" "record expected public key from offline-generated PEM"
    public_key_pem_from_private "${key_pem}" "${pub}"
    log_detail "saved $(basename "${pub}")"
  elif [[ ! -f "${pub}" ]]; then
    die "missing ${pub} — copy 1 must be provisioned first"
  else
    log_detail "reusing public key from copy 1 ($(basename "${pub}"))"
  fi

  log_step "3" "write signing key to YubiKey (PIV setup + import)"
  _import_signing_key "${serial}" "${key_pem}" "${touch}"

  log_step "4" "verify HSM key and derive IC principal"
  principal="$(_principal_from_hsm "${serial}" "realms-ceremony-${env_id}-${copy_num}" "${touch}" "${key_pem}")"
  [[ -n "${principal}" ]] || die "empty IC principal after HSM verification"

  local principal_file="${CEREMONY_ARTIFACTS}/${env_id}-principal.txt"
  if [[ -f "${principal_file}" ]]; then
    expected="$(cat "${principal_file}")"
    log_step "5" "confirm principal matches copy 1"
    [[ "${principal}" == "${expected}" ]] \
      || die "${env_id} copy ${copy_num} principal mismatch (expected ${expected}, got ${principal})"
    log_detail "principal matches copy 1"
  else
    printf '%s\n' "${principal}" > "${principal_file}"
    update_manifest "${env_id}" "${principal}" "${pub}" "${touch}" "${serial}"
    log_step "5" "record principal and update manifest"
  fi

  printf '%s\n' "${serial}" >> "${CEREMONY_ARTIFACTS}/${env_id}-serials.txt"
  log "${env_id} copy ${copy_num}/${copies} complete — serial ${serial}, principal ${principal}"
  if [[ "${copy_num}" -lt "${copies}" ]]; then
    log_user "Remove this YubiKey and insert the next ${label} for copy $((copy_num + 1))/${copies}"
  fi
}

provision_environment() {
  local env_id="$1"
  config_env_exists "${env_id}" || die "unknown environment: ${env_id}"
  local copies i label touch
  copies="$(config_env_copies "${env_id}")"
  label="$(config_env_yubikey_label "${env_id}")"
  touch="$(config_env_touch_policy "${env_id}")"
  log_banner "provision-env ${env_id}"
  log_detail "$(config_env_description "${env_id}")"
  log_detail "hardware: ${label} × ${copies}"
  log_touch_policy "${touch}"
  rm -f "${CEREMONY_ARTIFACTS}/${env_id}-serials.txt"
  for i in $(seq 1 "${copies}"); do
    _provision_environment_copy "${env_id}" "${i}"
  done
  log "${env_id} provisioning finished (${copies} key(s))"
}

provision_dev_yubikey() {
  provision_environment "dev"
}

provision_prod_yubikey() {
  provision_environment "prod"
}

require_export_pem_opt_in() {
  if [[ "${CEREMONY_EXPORT_PEM_I_UNDERSTAND:-}" == "1" ]]; then
    return 0
  fi
  die "export-pem is opt-in only: set CEREMONY_EXPORT_PEM_I_UNDERSTAND=1 (PEM on disk bypasses hardware-only ceremony)"
}

export_signing_key_pem() {
  local env="$1"
  local dest="$2"
  local src dest_pem principal manifest expected

  require_export_pem_opt_in
  src="$(signing_key_pem_path "${env}")"
  dest_pem="$(resolve_dfx_identity_pem_path "${dest}")"

  log "WARNING: exporting ${env} private key PEM to ${dest_pem}"
  log "WARNING: PEM on disk is high risk — prefer YubiKey HSM; use only for transitional dev/CI needs"
  install_signing_key_pem_copy "${src}" "${dest_pem}"
  openssl ec -in "${dest_pem}" -check -noout >/dev/null 2>&1 \
    || die "exported PEM failed openssl ec -check: ${dest_pem}"

  principal="$(_principal_from_pem "${dest_pem}" "realms-export-${env}")"
  log "exported ${env} PEM — IC principal: ${principal}"

  manifest="${CEREMONY_ARTIFACTS}/manifest.json"
  if [[ -f "${manifest}" ]] && command -v jq >/dev/null 2>&1; then
    expected="$(jq -r --arg env "${env}" '.environments[$env].principal // empty' "${manifest}")"
    if [[ -n "${expected}" && "${expected}" != "null" ]]; then
      [[ "${principal}" == "${expected}" ]] \
        || die "exported ${env} PEM principal mismatch (manifest ${expected}, got ${principal})"
      log "export-pem principal matches manifest.environments.${env}"
    fi
  fi

  log "dfx/icp import example:"
  log "  icp identity import <name> --from-pem ${dest_pem} --storage plaintext"
  printf '%s\n' "${dest_pem}"
}

verify_environment_principals_match() {
  local env_id="$1"
  local key_pem expected p
  key_pem="$(config_env_signing_key_path "${env_id}")"
  [[ -f "${key_pem}" ]] || return 0
  expected="$(cat "${CEREMONY_ARTIFACTS}/${env_id}-principal.txt" 2>/dev/null || true)"
  [[ -n "${expected}" ]] || die "${env_id} principal not recorded"
  p="$(_principal_from_pem "${key_pem}" "realms-ceremony-${env_id}-verify")"
  [[ "${p}" == "${expected}" ]] || die "${env_id} key PEM principal mismatch"
  log "${env_id} principal consistency check OK"
}

verify_all_environment_principals() {
  local env_id
  while IFS= read -r env_id; do
    [[ -n "${env_id}" ]] || continue
    verify_environment_principals_match "${env_id}"
  done < <(config_env_ids_ordered)
}
