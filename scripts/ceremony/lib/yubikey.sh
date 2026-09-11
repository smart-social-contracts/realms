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
  log "PIV reset on serial ${serial} (wipes PIV PIN/PUK/mgmt/slots — FIDO/OTP unchanged)"
  ykman --device "${serial}" piv reset -f
}

_piv_factory_pin() { printf '%s' "123456"; }
_piv_factory_puk() { printf '%s' "12345678"; }
_piv_factory_mgmt() { printf '%s' "010203040506070801020304050607080102030405060708"; }

_piv_pin_is() {
  local serial="$1" pin="$2"
  ykman --device "${serial}" piv access change-pin -P "${pin}" -n "${pin}" >/dev/null 2>&1
}

_piv_mgmt_is() {
  local serial="$1" mgmt="$2" pin="${3:-}"
  local pin_args=()
  [[ -n "${pin}" ]] && pin_args=(-P "${pin}")
  ykman --device "${serial}" piv access change-management-key \
    -m "${mgmt}" -n "${mgmt}" "${pin_args[@]}" >/dev/null 2>&1 \
    || ykman --device "${serial}" piv access change-management-key \
      -m "${mgmt}" -n "${mgmt}" -a AES192 "${pin_args[@]}" >/dev/null 2>&1
}

_piv_change_management_key() {
  local serial="$1" current_mgmt="$2" new_mgmt="$3"
  local pin="${PIV_PIN:-}" err="" pin_args=()
  [[ -n "${pin}" ]] && pin_args=(-P "${pin}")

  if _piv_mgmt_is "${serial}" "${new_mgmt}" "${pin}"; then
    return 0
  fi
  if ykman --device "${serial}" piv access change-management-key \
      -m "${current_mgmt}" -n "${new_mgmt}" -a AES192 "${pin_args[@]}" >/dev/null 2>&1; then
    return 0
  fi
  if ykman --device "${serial}" piv access change-management-key \
      -m "${current_mgmt}" -n "${new_mgmt}" -a AES192 >/dev/null 2>&1; then
    return 0
  fi
  if ykman --device "${serial}" piv access change-management-key \
      -m "${current_mgmt}" -n "${new_mgmt}" >/dev/null 2>&1; then
    return 0
  fi
  err="$(ykman --device "${serial}" piv access change-management-key \
    -m "${current_mgmt}" -n "${new_mgmt}" -a AES192 "${pin_args[@]}" 2>&1)" || true
  die "PIV management key change failed: ${err:-reset PIV (CEREMONY_PIV_RESET=1) or set CEREMONY_CURRENT_PIV_MANAGEMENT_KEY}"
}

_piv_reset_existing_key() {
  local serial="$1"
  CEREMONY_PIV_RESET=1
  _piv_reset_if_requested "${serial}"
}

_piv_offer_reset_existing() {
  local serial="$1"
  log "This YubiKey (serial ${serial}) already has a custom PIV PIN — not factory 123456 and not this ceremony's PIN."
  log "Ceremony must own PIV (PIN / PUK / management key) before importing the signing key."
  if [[ "${CEREMONY_PIV_RESET:-0}" == "1" ]]; then
    _piv_reset_existing_key "${serial}"
    return 0
  fi
  if [[ -n "${CEREMONY_CURRENT_PIV_PIN:-}" ]]; then
    log_detail "migrating existing PIV PIN from CEREMONY_CURRENT_PIV_PIN"
    local current_mgmt
    current_mgmt="${CEREMONY_CURRENT_PIV_MANAGEMENT_KEY:-$(_piv_factory_mgmt)}"
    ykman --device "${serial}" piv access change-pin \
      -P "${CEREMONY_CURRENT_PIV_PIN}" -n "${PIV_PIN}" \
      || die "existing PIV PIN rejected (CEREMONY_CURRENT_PIV_PIN)"
    _piv_change_management_key "${serial}" "${current_mgmt}" "${PIV_MANAGEMENT_KEY}" \
      || die "existing PIV management key rejected (set CEREMONY_CURRENT_PIV_MANAGEMENT_KEY or CEREMONY_PIV_RESET=1)"
    return 0
  fi
  if [[ -t 0 ]]; then
    log_user "Reset PIV on this key? Wipes PIV slots/PIN (FIDO/OTP unchanged). Recommended. [Y/n]"
    local ans=""
    read -r ans || true
    if [[ -z "${ans}" || "${ans}" == [Yy]* ]]; then
      _piv_reset_existing_key "${serial}"
      return 0
    fi
    log_user "Enter the current PIV PIN (or Ctrl+C and re-run with CEREMONY_PIV_RESET=1):"
    local current_pin=""
    read -r current_pin
    [[ -n "${current_pin}" ]] || die "no current PIN entered"
    ykman --device "${serial}" piv access change-pin \
      -P "${current_pin}" -n "${PIV_PIN}" \
      || die "current PIV PIN rejected"
    log_user "Enter the current PIV management key (48 hex chars), or press Enter for factory default:"
    local current_mgmt=""
    read -r current_mgmt
    current_mgmt="${current_mgmt:-$(_piv_factory_mgmt)}"
    _piv_change_management_key "${serial}" "${current_mgmt}" "${PIV_MANAGEMENT_KEY}" \
      || die "current management key rejected — re-run with CEREMONY_PIV_RESET=1"
    return 0
  fi
  die "YubiKey has a custom PIV PIN. Re-run: CEREMONY_PIV_RESET=1 sudo -E ./realms-key-ceremony.sh provision-prod"
}

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
  log_detail "[PIV] uses ceremony PIN from operator-credentials (not typed interactively unless this key is already customized)"

  if ykman --device "${serial}" piv access change-pin \
      -P "${factory_pin}" -n "${PIV_PIN}" >/dev/null 2>&1; then
    log_detail "PIV PIN set from factory default"
  elif _piv_pin_is "${serial}" "${PIV_PIN}"; then
    log_detail "PIV PIN already matches ceremony PIN"
  else
    _piv_offer_reset_existing "${serial}"
    if ! _piv_pin_is "${serial}" "${PIV_PIN}"; then
      if ykman --device "${serial}" piv access change-pin \
          -P "${factory_pin}" -n "${PIV_PIN}" >/dev/null 2>&1; then
        log_detail "PIV PIN set from factory default after reset"
      else
        die "PIV PIN is still not the ceremony PIN after reset/migrate"
      fi
    fi
  fi

  if ykman --device "${serial}" piv access change-puk \
      -p "${factory_puk}" -n "${PIV_PUK}" >/dev/null 2>&1; then
    log_detail "PIV PUK set from factory default"
  elif ykman --device "${serial}" piv access change-puk \
      -p "${PIV_PUK}" -n "${PIV_PUK}" >/dev/null 2>&1; then
    log_detail "PIV PUK already set to ceremony value"
  else
    log "warning: could not set PIV PUK (may already be customized) — unblock later with ykman piv access unblock-pin"
  fi

  if _piv_change_management_key "${serial}" "${factory_mgmt}" "${PIV_MANAGEMENT_KEY}"; then
    log_detail "PIV management key ready (factory or ceremony value)"
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
  if ! ykman --device "${serial}" piv keys import "${CEREMONY_SLOT}" "${key_pem}" \
      -P "${PIV_PIN}" \
      -m "${PIV_MANAGEMENT_KEY}" \
      --touch-policy "${touch_policy}" \
      --pin-policy "${CEREMONY_PIN_POLICY:-once}"; then
    die "PIV key import failed (wrong PIN or management key). If this YubiKey was used before: CEREMONY_PIV_RESET=1 sudo -E ./realms-key-ceremony.sh provision-prod"
  fi
  log_detail "key import complete"
}

# ykcs11 -- and therefore `dfx --hsm` / icp HSM signing -- only exposes a PIV slot
# that holds a certificate, so an imported key is invisible without one. Build it
# off-card from the offline PEM: the card never signs, so this needs no touch.
_install_slot_certificate() {
  local serial="$1"
  local key_pem="$2"
  local subject="$3"
  local cert err
  [[ "${CEREMONY_SIMULATE}" == "1" ]] && return 0
  load_operator_credentials
  cert="${CEREMONY_ARTIFACTS}/piv-${serial}-${CEREMONY_SLOT}.crt"
  err="$(mktemp)"
  if ! openssl req -new -x509 -key "${key_pem}" -sha256 -days 7300 \
      -subj "/O=Realms Key Ceremony/CN=${subject}" -out "${cert}" 2>"${err}"; then
    log_detail "slot certificate build failed: $(tr '\n' ' ' < "${err}")"
    rm -f "${err}"
    die "cannot build slot certificate for serial ${serial}"
  fi
  if ! ykman --device "${serial}" piv certificates import "${CEREMONY_SLOT}" "${cert}" \
      -m "${PIV_MANAGEMENT_KEY}" -P "${PIV_PIN}" >/dev/null 2>"${err}"; then
    log_detail "slot certificate import failed: $(tr '\n' ' ' < "${err}")"
    rm -f "${err}"
    die "cannot write slot certificate to serial ${serial}"
  fi
  rm -f "${err}"
  log_no_touch
  log_detail "slot certificate installed — PKCS#11 can now see the key"
}

public_key_pem_from_private() {
  local key_pem="$1"
  local out="$2"
  openssl ec -in "${key_pem}" -pubout -out "${out}" 2>/dev/null
}

# Read the public key the card actually holds, from PIV slot metadata. Needs
# firmware >= 5.3 but neither PIN nor touch. Deliberately not `ykman piv keys
# export`: that falls back to the slot certificate, which the ceremony writes
# itself, so it would confirm our own input rather than the card's key.
_slot_public_key_from_metadata() {
  local serial="$1"
  local out="$2"
  local helper="${CEREMONY_LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/piv_slot_info.py"
  [[ -f "${helper}" ]] || return 1
  command -v python3 >/dev/null 2>&1 || return 1
  python3 "${helper}" "${CEREMONY_SLOT}" 2>/dev/null \
    | SERIAL="${serial}" python3 -c '
import json, os, sys
want = os.environ["SERIAL"]
try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(1)
for dev in data.get("devices", []):
    if str(dev.get("serial")) == want and dev.get("public_key_pem"):
        sys.stdout.write(dev["public_key_pem"])
        sys.exit(0)
sys.exit(1)
' > "${out}" || return 1
  [[ -s "${out}" ]]
}

_public_key_fingerprint() {
  openssl ec -in "$1" -pubin -pubout -outform DER 2>/dev/null | openssl sha256
}

_yubico_piv_sign() {
  local serial="$1" msg="$2" sig="$3" err="$4"
  YKCS11_DEVICE="${serial}" yubico-piv-tool -v 1 -a verify-pin --sign \
    -s "${CEREMONY_SLOT}" -H SHA256 -A ECCP256 -P "${PIV_PIN}" \
    -i "${msg}" -o "${sig}" >/dev/null 2>"${err}"
}

# Fallback proof for cards without slot metadata: make the card sign a nonce and
# check it against the offline public key. This is the only way to prove an
# imported key (attestation covers on-card generation only), and with a
# non-`never` touch policy the card will not sign without a physical touch.
_verify_yubikey_via_signature() {
  local serial="$1"
  local key_pem="$2"
  local touch_policy="${3:-never}"
  local msg pub sig err reason
  local attempt=0 max_attempts=3 needs_touch=0
  load_operator_credentials
  require_cmd yubico-piv-tool
  msg="$(mktemp)"; pub="$(mktemp)"; sig="$(mktemp)"; err="$(mktemp)"
  printf 'realms-ceremony-verify' > "${msg}"
  public_key_pem_from_private "${key_pem}" "${pub}" \
    || die "cannot derive public key from offline signing PEM"
  touch_required_for_hsm_verify "${touch_policy}" && needs_touch=1

  while (( attempt < max_attempts )); do
    attempt=$(( attempt + 1 ))
    if (( needs_touch )); then
      log_user "Touch the YubiKey NOW — it is waiting (touch policy: ${touch_policy}, ~15s window, attempt ${attempt}/${max_attempts})"
    fi
    if _yubico_piv_sign "${serial}" "${msg}" "${sig}" "${err}"; then
      if openssl dgst -sha256 -verify "${pub}" -signature "${sig}" "${msg}" >/dev/null 2>&1; then
        rm -f "${msg}" "${pub}" "${sig}" "${err}"
        log_detail "on-card signature matches offline PEM"
        return 0
      fi
      rm -f "${msg}" "${pub}" "${sig}" "${err}"
      die "serial ${serial} signed with a different key than the offline PEM — do not use this YubiKey"
    fi
    reason="$(tr '\n' ' ' < "${err}" | sed 's/  */ /g')"
    log_detail "signing attempt ${attempt} failed: ${reason}"
    if (( attempt < max_attempts )); then
      if (( needs_touch )); then
        log_user "No touch registered. Put a finger on the YubiKey contact, then press Enter to retry..."
      else
        log_user "Signing failed. Re-seat the YubiKey if needed, then press Enter to retry..."
      fi
      read -r _ || true
    fi
  done
  rm -f "${msg}" "${pub}" "${sig}" "${err}"
  die "serial ${serial} would not sign after ${max_attempts} attempts (last error: ${reason}). With touch policy '${touch_policy}' the card refuses to sign until it is touched; retry the command and touch the metal contact while the LED blinks."
}

_ic_principal_from_cli_output() {
  # Textual principals group by 5, but the final group is shorter (3 chars for
  # the 29-byte self-authenticating form) — requiring 5 everywhere matches nothing.
  grep -E '^[a-z0-9]{5}(-[a-z0-9]{1,5})+$' <<< "$1" | head -1
}

_principal_offline_from_pem() {
  local key_pem="$1"
  local helper="${CEREMONY_LIB_DIR:-$(dirname "${BASH_SOURCE[0]}")}/ic_principal.py"
  [[ -f "${helper}" ]] || die "missing principal helper: ${helper}"
  require_cmd python3
  openssl ec -in "${key_pem}" -pubout -outform DER 2>/dev/null \
    | python3 "${helper}"
}

_principal_via_icp() {
  local key_pem="$1" name="$2" tmp_home principal
  command -v icp >/dev/null 2>&1 || return 1
  tmp_home="$(mktemp -d)"
  HOME="${tmp_home}" DO_NOT_TRACK=1 icp identity import "${name}" \
    --from-pem "${key_pem}" --storage plaintext >/dev/null 2>&1 || {
    rm -rf "${tmp_home}"
    return 1
  }
  principal="$(HOME="${tmp_home}" DO_NOT_TRACK=1 icp identity principal \
    --identity "${name}" 2>/dev/null)"
  rm -rf "${tmp_home}"
  _ic_principal_from_cli_output "${principal}"
}

_principal_from_pem() {
  local key_pem="$1"
  local name="$2"
  local principal cross
  principal="$(_principal_offline_from_pem "${key_pem}")" \
    || die "cannot derive IC principal from ${name} signing key"
  principal="$(_ic_principal_from_cli_output "${principal}")"
  [[ -n "${principal}" ]] || die "empty principal for ${name}"
  # Cross-check against icp-cli when present; the offline value stays authoritative.
  if cross="$(_principal_via_icp "${key_pem}" "${name}")" && [[ -n "${cross}" ]]; then
    [[ "${cross}" == "${principal}" ]] \
      || die "principal mismatch for ${name}: offline ${principal} vs icp ${cross}"
    log_detail "principal cross-checked with icp-cli"
  fi
  printf '%s' "${principal}"
}

_verify_yubikey_public_key_matches() {
  local serial="$1"
  local key_pem="$2"
  local touch_policy="${3:-never}"
  local on_key expected fp_on fp_exp
  on_key="$(mktemp)"
  expected="$(mktemp)"
  public_key_pem_from_private "${key_pem}" "${expected}" \
    || die "cannot derive public key from offline signing PEM"

  if [[ "${CEREMONY_SIMULATE}" == "1" ]]; then
    cp "$(_sim_root)/${serial}/slot-${CEREMONY_SLOT}.pub.pem" "${on_key}"
  elif ! _slot_public_key_from_metadata "${serial}" "${on_key}"; then
    rm -f "${on_key}" "${expected}"
    log_detail "no PIV slot metadata on serial ${serial} (firmware older than 5.3) — proving the key by on-card signature instead"
    _verify_yubikey_via_signature "${serial}" "${key_pem}" "${touch_policy}"
    return 0
  fi

  fp_on="$(_public_key_fingerprint "${on_key}")"
  fp_exp="$(_public_key_fingerprint "${expected}")"
  rm -f "${on_key}" "${expected}"
  [[ -n "${fp_on}" && "${fp_on}" == "${fp_exp}" ]] \
    || die "public key on serial ${serial} does not match the offline signing key"
  log_no_touch
  log_detail "public key read from PIV slot metadata matches offline PEM"
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
  export PKCS11_MODULE_PATH="${CEREMONY_PKCS11_LIB}"
  if ! HOME="${tmp_home}" DFX_HSM_PIN="${PIV_PIN}" YKCS11_DEVICE="${serial}" \
    PKCS11_MODULE_PATH="${CEREMONY_PKCS11_LIB}" \
    ceremony_run_dfx identity new "${name}" \
    --storage-mode plaintext \
    --hsm-key-id "${CEREMONY_HSM_KEY_ID}" \
    --hsm-pkcs11-lib-path "${CEREMONY_PKCS11_LIB}" 2>"${errfile}"; then
    if grep -qiE 'CKR_PIN_LOCKED|PIN_LOCKED|0xa4' "${errfile}"; then
      rm -rf "${tmp_home}" "${errfile}"
      die "YubiKey PIV PIN is locked (CKR_PIN_LOCKED). Unblock with PUK from operator-credentials.txt: ykman --device ${serial} piv access unblock-pin -p \"\$PIV_PUK\" -n \"\$PIV_PIN\""
    fi
    if ! grep -q 'Identity already exists' "${errfile}"; then
      log_detail "dfx HSM identity new failed: $(tr '\n' ' ' < "${errfile}")"
      rm -rf "${tmp_home}" "${errfile}"
      return 1
    fi
  fi
  rm -f "${errfile}"

  principal="$(HOME="${tmp_home}" DFX_HSM_PIN="${PIV_PIN}" YKCS11_DEVICE="${serial}" \
    PKCS11_MODULE_PATH="${CEREMONY_PKCS11_LIB}" \
    ceremony_run_dfx identity get-principal --identity "${name}" 2>/dev/null)" || principal=""
  principal="$(_ic_principal_from_cli_output "${principal}")"
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
  _verify_yubikey_public_key_matches "${serial}" "${key_pem}" "${touch_policy}"
  # Only after the card's key is proven — writing the cert first would let the
  # metadata check above read back our own file instead of the card's key.
  _install_slot_certificate "${serial}" "${key_pem}" "${name}"

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
  manifest_add_serial "${env_id}" "${serial}"
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
