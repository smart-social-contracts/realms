#!/usr/bin/env bash
# Export a self-contained verification bundle to the ceremony USB data partition.
#
# The bundle must work on a laptop that has never seen this repo, so it carries
# the verification tooling alongside the artifacts. It contains public material
# only — never a signing key, never the operator PIN/PUK.
set -euo pipefail

# shellcheck source=usb_labels.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/usb_labels.sh"
CEREMONY_BUNDLE_NAME="${CEREMONY_BUNDLE_NAME:-realms-key-verification}"

_bundle_is_usable_disk() {
  local dev="$1"
  [[ -b "${dev}" ]] || return 1
  # Loop images are leftover VM tests, not the ceremony USB.
  if [[ "${CEREMONY_ALLOW_LOOP_DATA:-0}" != "1" ]]; then
    [[ "$(lsblk -ndo TYPE "${dev}" 2>/dev/null || true)" != "loop" ]] || return 1
  fi
  return 0
}

_bundle_lookup_label() {
  local label="$1" dev=""
  if command -v blkid >/dev/null 2>&1; then
    dev="$(blkid -L "${label}" 2>/dev/null || true)"
  fi
  if [[ -z "${dev}" ]]; then
    local by_label="/dev/disk/by-label/${label}"
    [[ -b "${by_label}" ]] && dev="$(readlink -f "${by_label}")"
  fi
  _bundle_is_usable_disk "${dev}" || return 1
  printf '%s' "${dev}"
}

_bundle_data_device() {
  local label dev
  local -a labels=("${CEREMONY_DATA_LABEL}")
  local -a aliases=()
  # shellcheck disable=SC2206
  aliases=(${CEREMONY_DATA_LABEL_ALIASES})
  labels+=("${aliases[@]}")
  for label in "${labels[@]}"; do
    [[ -n "${label}" ]] || continue
    if dev="$(_bundle_lookup_label "${label}")"; then
      printf '%s' "${dev}"
      return 0
    fi
  done
  return 1
}

# Echoes the mount point of the USB data partition, mounting it if necessary.
_bundle_mount_point() {
  local dev mp
  dev="$(_bundle_data_device)" || return 1
  mp="$(findmnt -n -o TARGET --source "${dev}" 2>/dev/null | head -1 || true)"
  if [[ -n "${mp}" ]]; then
    printf '%s' "${mp}"
    return 0
  fi
  mp="/media/realms-ceremony-data"
  mkdir -p "${mp}"
  # New sticks are exFAT; older test sticks may still be NTFS.
  mount "${dev}" "${mp}" 2>/dev/null \
    || mount -t exfat "${dev}" "${mp}" 2>/dev/null \
    || mount -t ntfs-3g "${dev}" "${mp}" 2>/dev/null \
    || return 1
  printf '%s' "${mp}"
}

# QEMU interactive VM: /opt/realms-ceremony is the host checkout (virtio-9p).
_bundle_host_share_dir() {
  local root="${CEREMONY_SCRIPT_DIR:-}"
  [[ -n "${root}" && -d "${root}" && -w "${root}" ]] || return 1
  findmnt -n -o FSTYPE --target "${root}" 2>/dev/null | grep -qx '9p' || return 1
  printf '%s/artifacts' "${root}"
}

# USB "CEREMONY DATA" when present; otherwise the 9p share (test VM).
# Simulate never writes to a real stick — those principals are not hardware keys.
ceremony_resolve_bundle_dir() {
  if [[ -n "${CEREMONY_BUNDLE_DIR:-}" ]]; then
    printf '%s' "${CEREMONY_BUNDLE_DIR}"
    return 0
  fi
  local mp share
  if [[ "${CEREMONY_SIMULATE:-0}" == "1" ]]; then
    # Its own subtree: a dry run must never overwrite a real ceremony's output.
    printf '%s/artifacts/simulate' "${CEREMONY_SCRIPT_DIR}"
    return 0
  fi
  if mp="$(_bundle_mount_point)"; then
    printf '%s/%s' "${mp}" "${CEREMONY_BUNDLE_NAME}"
    return 0
  fi
  if share="$(_bundle_host_share_dir)"; then
    printf '%s' "${share}"
    return 0
  fi
  return 1
}

# Private PEMs (dev transitional). Never the public verification bundle.
# USB → <CEREMONY DATA>/realms-key-secrets/; VM → artifacts/private/;
# simulate → artifacts/simulate/private/, so a dry run cannot clobber real keys.
ceremony_resolve_secrets_dir() {
  if [[ -n "${CEREMONY_SECRETS_EXPORT_DIR:-}" ]]; then
    printf '%s' "${CEREMONY_SECRETS_EXPORT_DIR}"
    return 0
  fi
  local mp share
  if [[ "${CEREMONY_SIMULATE:-0}" == "1" ]]; then
    printf '%s/artifacts/simulate/private' "${CEREMONY_SCRIPT_DIR}"
    return 0
  fi
  if mp="$(_bundle_mount_point)"; then
    printf '%s/realms-key-secrets' "${mp}"
    return 0
  fi
  if share="$(_bundle_host_share_dir)"; then
    printf '%s/private' "${share}"
    return 0
  fi
  return 1
}

ceremony_export_configured_pems() {
  local dest_dir env_id dest_pem src exported=0 want=0
  while IFS= read -r env_id; do
    [[ -n "${env_id}" ]] || continue
    if config_env_export_private_pem "${env_id}"; then
      want=1
      break
    fi
  done < <(config_env_ids_ordered)
  [[ "${want}" -eq 1 ]] || return 0

  dest_dir="$(ceremony_resolve_secrets_dir)" \
    || die "export_private_pem is set but there is no USB data volume and no 9p share to write the PEM"

  while IFS= read -r env_id; do
    [[ -n "${env_id}" ]] || continue
    config_env_export_private_pem "${env_id}" || continue
    if [[ "${env_id}" == "prod" && "${CEREMONY_EXPORT_PROD_PEM_I_UNDERSTAND:-0}" != "1" ]]; then
      die "refusing to export a production private PEM. Remove export_private_pem from prod, or set CEREMONY_EXPORT_PROD_PEM_I_UNDERSTAND=1"
    fi
    mkdir -p "${dest_dir}"
    chmod 700 "${dest_dir}" 2>/dev/null || true
    src="$(config_env_signing_key_path "${env_id}")"
    if [[ ! -f "${src}" ]]; then
      log_detail "skip ${env_id} PEM export — signing key already destroyed"
      continue
    fi
    dest_pem="${dest_dir}/${env_id}-identity.pem"
    log "export_private_pem=${env_id} → ${dest_pem}"
    CEREMONY_EXPORT_PEM_I_UNDERSTAND=1 export_signing_key_pem "${env_id}" "${dest_pem}" >/dev/null
    manifest_set_exported_pem "${env_id}" "${dest_pem}"
    exported=$((exported + 1))
  done < <(config_env_ids_ordered)

  if [[ "${exported}" -gt 0 ]]; then
    printf '%s\n' \
      "WARNING: private signing PEMs. Prefer the YubiKey for day-to-day use." \
      "Do not copy these files onto the public realms-key-verification bundle." \
      > "${dest_dir}/README.txt"
    chmod 600 "${dest_dir}/"* 2>/dev/null || true
    log "exported ${exported} private PEM(s) to ${dest_dir}"
  fi
}

_bundle_write_readme() {
  local dest="$1"
  local manifest="${dest}/manifest.json"
  {
    cat <<'HEADER'
# Verify the ceremony YubiKeys

Public material only — no signing key and no PIN is stored here.

Run this on any trusted laptop, one YubiKey at a time.

## Requirements

    sudo apt install yubikey-manager python3 jq openssl exfatprogs
    sudo systemctl unmask pcscd.socket   # if "start" says the unit is masked
    sudo systemctl start pcscd

## Verify

HEADER
    local env_id
    while IFS= read -r env_id; do
      [[ -n "${env_id}" ]] || continue
      printf '    ./verify-yubikeys.sh --manifest manifest.json --env %s\n' "${env_id}"
    done < <(jq -r '.environments | keys[]' "${manifest}")
    cat <<'FOOTER'

Insert one key, run the matching command, then swap and repeat. Every check must
print PASS; the script exits non-zero if anything fails.

Keys with firmware older than 5.3 expose no PIV slot metadata. For those the
script cannot read the slot policies and instead asks for the PIV PIN, has the
card sign a challenge, and verifies that signature against the public key in
manifest.json. A touch may be required.

## Expected values

FOOTER
    jq -r '.environments | to_entries[]
           | "  \(.key):\n    principal: \(.value.principal)\n    serials:   \((.value.yubikey_serials // [.value.yubikey_serial]) | join(", "))\n    touch:     \(.value.touch_policy)\n    PIV slot:  \(.value.piv_slot)\n"' \
      "${manifest}"
    cat <<'TAIL'
## Registering the identity for use

See operator-dfx-identity.txt (if present) for the dfx HSM identity commands.
TAIL
  } > "${dest}/README-VERIFY.md"
}

# Fails loudly rather than silently skipping: a ceremony whose verification
# bundle never reached the USB is a ceremony you cannot check afterwards.
ceremony_export_verification_bundle() {
  local dest="${1:-}"
  require_cmd jq
  [[ -f "${CEREMONY_ARTIFACTS}/manifest.json" ]] \
    || die "no manifest to export — run provisioning first"

  if [[ -z "${dest}" ]]; then
    dest="$(ceremony_resolve_bundle_dir)" || die \
      "cannot write the verification bundle: no '${CEREMONY_DATA_LABEL}' USB volume and no 9p share at ${CEREMONY_SCRIPT_DIR:-<unknown>}"
  fi

  mkdir -p "${dest}/lib"
  log "exporting verification bundle to ${dest}"

  local f path
  for f in manifest.json ceremony-config.json operator-dfx-identity.txt \
           '*-public.pem' '*-principal.txt' '*-serials.txt'; do
    for path in "${CEREMONY_ARTIFACTS}"/${f}; do
      [[ -f "${path}" ]] || continue
      install -m 644 "${path}" "${dest}/$(basename "${path}")"
      log_detail "$(basename "${path}")"
    done
  done

  install -m 755 "${CEREMONY_SCRIPT_DIR}/verify-yubikeys.sh" "${dest}/verify-yubikeys.sh"
  install -m 644 "${CEREMONY_LIB_DIR}/ic_principal.py" "${dest}/lib/ic_principal.py"
  install -m 644 "${CEREMONY_LIB_DIR}/piv_slot_info.py" "${dest}/lib/piv_slot_info.py"
  install -m 644 "${CEREMONY_LIB_DIR}/piv_sign.py" "${dest}/lib/piv_sign.py"
  log_detail "verify-yubikeys.sh + lib/"

  _bundle_write_readme "${dest}"
  log_detail "README-VERIFY.md"

  # Last line of defence: a signing key or PIN must never reach the USB.
  if grep -rlE 'PRIVATE KEY|PIV_PIN|PIV_PUK|PIV_MANAGEMENT_KEY' \
      --exclude-dir=private --exclude-dir=realms-key-secrets \
      --exclude='*-identity.pem' "${dest}" >/dev/null 2>&1; then
    grep -rlE 'PRIVATE KEY|PIV_PIN|PIV_PUK|PIV_MANAGEMENT_KEY' \
      --exclude-dir=private --exclude-dir=realms-key-secrets \
      --exclude='*-identity.pem' "${dest}" >&2
    die "secret material reached ${dest} — bundle rejected"
  fi

  sync
  log "verification bundle ready: ${dest}"
  log_detail "take this to a trusted laptop and follow README-VERIFY.md"
}
