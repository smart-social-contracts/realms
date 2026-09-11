#!/usr/bin/env bash
# Verify a provisioned ceremony YubiKey on an ordinary workstation. Needs no
# ceremony workspace, no private key, no PIN and no touch: PIV slot metadata
# (firmware 5.3+) reports the policies and the slot's public key, from which the
# IC principal is re-derived and compared with the ceremony manifest.
#
#   ./verify-yubikeys.sh                              # auto: nearby manifest, --env prod
#   ./verify-yubikeys.sh --env dev
#   ./verify-yubikeys.sh --manifest artifacts/manifest.json --env prod
#   ./verify-yubikeys.sh --principal 72g7v-...-bqe --touch-policy cached
#
# Insert one key at a time and re-run per key. With no --manifest/--principal,
# looks for ./manifest.json then <script>/artifacts/manifest.json.
#
# Expected key type, PIN policy and whether a slot certificate is required all
# come from the manifest. Override with --key-type / --pin-policy /
# --no-cert-check when checking a key provisioned by another ceremony.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRINCIPAL_HELPER="${SCRIPT_DIR}/lib/ic_principal.py"
SLOT_HELPER="${SCRIPT_DIR}/lib/piv_slot_info.py"
SIGN_HELPER="${SCRIPT_DIR}/lib/piv_sign.py"

SLOT="${CEREMONY_SLOT:-9c}"
EXPECTED_PRINCIPAL=""
EXPECTED_TOUCH=""
EXPECTED_PIN_POLICY=""
EXPECTED_KEY_TYPE=""
EXPECTED_SERIALS=""
EXPECTED_PUBKEY=""
REQUIRE_CERT=""
MANIFEST=""
ENV_ID="prod"

die() { printf '[verify] ERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '[verify] %s\n' "$*"; }
ok() { printf '[verify]   PASS  %s\n' "$*"; }
bad() { printf '[verify]   FAIL  %s\n' "$*" >&2; }

usage() { sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0; }

_find_default_manifest() {
  local candidate
  for candidate in \
      "${PWD}/manifest.json" \
      "${SCRIPT_DIR}/artifacts/manifest.json" \
      "${SCRIPT_DIR}/manifest.json"; do
    if [[ -f "${candidate}" ]]; then
      printf '%s' "${candidate}"
      return 0
    fi
  done
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --principal) EXPECTED_PRINCIPAL="$2"; shift 2 ;;
    --manifest) MANIFEST="$2"; shift 2 ;;
    --env) ENV_ID="$2"; shift 2 ;;
    --slot) SLOT="$2"; shift 2 ;;
    --touch-policy) EXPECTED_TOUCH="$2"; shift 2 ;;
    --pin-policy) EXPECTED_PIN_POLICY="$2"; shift 2 ;;
    --key-type) EXPECTED_KEY_TYPE="$2"; shift 2 ;;
    --no-cert-check) REQUIRE_CERT="false"; shift ;;
    -h|--help) usage ;;
    *) die "unknown argument: $1" ;;
  esac
done

for cmd in openssl python3 jq; do
  command -v "${cmd}" >/dev/null 2>&1 || die "required command not found: ${cmd}"
done
[[ -f "${PRINCIPAL_HELPER}" ]] || die "missing ${PRINCIPAL_HELPER}"
[[ -f "${SLOT_HELPER}" ]] || die "missing ${SLOT_HELPER}"
[[ -f "${SIGN_HELPER}" ]] || die "missing ${SIGN_HELPER}"

# A realms/basilisk venv hides Debian's yubikey-manager. Prefer any python that
# can import ykman, then the system interpreter that `apt` installed it into.
PYTHON=""
for py in python3 /usr/bin/python3 /usr/bin/python3.10 /usr/bin/python3.12; do
  command -v "${py}" >/dev/null 2>&1 || continue
  if "${py}" -c 'from ykman.device import list_all_devices' >/dev/null 2>&1; then
    PYTHON="${py}"
    break
  fi
done
[[ -n "${PYTHON}" ]] || die "python cannot import ykman (the CLI is not enough). Install: sudo apt install yubikey-manager — then retry. If a project venv is active, deactivate it or this script will use /usr/bin/python3 once that package is present."

if [[ -z "${MANIFEST}" && -z "${EXPECTED_PRINCIPAL}" ]]; then
  MANIFEST="$(_find_default_manifest)" || true
  [[ -n "${MANIFEST}" ]] && log "using manifest ${MANIFEST} (env ${ENV_ID})"
fi
if [[ -n "${MANIFEST}" ]]; then
  [[ -f "${MANIFEST}" ]] || die "no such manifest: ${MANIFEST}"
  jq -e --arg e "${ENV_ID}" '.environments[$e]' "${MANIFEST}" >/dev/null 2>&1 \
    || die "manifest has no environment '${ENV_ID}'"
  EXPECTED_PRINCIPAL="$(jq -r --arg e "${ENV_ID}" '.environments[$e].principal' "${MANIFEST}")"
  SLOT="$(jq -r --arg e "${ENV_ID}" '.environments[$e].piv_slot // "9c"' "${MANIFEST}")"
  # dev is touch=never, prod is touch=cached — never hardcode one of them.
  [[ -n "${EXPECTED_TOUCH}" ]] \
    || EXPECTED_TOUCH="$(jq -r --arg e "${ENV_ID}" '.environments[$e].touch_policy' "${MANIFEST}")"
  # Recorded by the ceremony; the defaults only cover manifests written before
  # these fields existed, so an older bundle still verifies.
  [[ -n "${EXPECTED_PIN_POLICY}" ]] \
    || EXPECTED_PIN_POLICY="$(jq -r --arg e "${ENV_ID}" '.environments[$e].pin_policy // "once"' "${MANIFEST}")"
  [[ -n "${EXPECTED_KEY_TYPE}" ]] \
    || EXPECTED_KEY_TYPE="$(jq -r --arg e "${ENV_ID}" '.environments[$e].key_type // "ECCP256"' "${MANIFEST}")"
  [[ -n "${REQUIRE_CERT}" ]] \
    || REQUIRE_CERT="$(jq -r --arg e "${ENV_ID}" '.environments[$e].slot_certificate // true' "${MANIFEST}")"
  EXPECTED_SERIALS="$(jq -r --arg e "${ENV_ID}" \
    '(.environments[$e].yubikey_serials // [.environments[$e].yubikey_serial]) | join(" ")' "${MANIFEST}")"
  EXPECTED_PUBKEY="$(jq -r --arg e "${ENV_ID}" '.environments[$e].public_key_pem // empty' "${MANIFEST}")"
fi
: "${EXPECTED_PIN_POLICY:=once}"
: "${EXPECTED_KEY_TYPE:=ECCP256}"
: "${REQUIRE_CERT:=true}"
[[ -n "${EXPECTED_PRINCIPAL}" ]] || die "pass --principal <id> or --manifest <file>"
[[ -n "${EXPECTED_TOUCH}" ]] || die "pass --touch-policy <never|cached|always> or --manifest <file>"

slot_json="$("${PYTHON}" "${SLOT_HELPER}" "${SLOT}" "${EXPECTED_KEY_TYPE}" || true)"
[[ -n "${slot_json}" ]] || die "could not read PIV slot metadata"
if err="$(jq -r '.error // empty' <<< "${slot_json}")" && [[ -n "${err}" ]]; then
  if [[ "${err}" == missing\ python* ]]; then
    die "${err}"
  fi
  die "${err} (is pcscd running? is a key inserted? is a VM still holding the USB device?)"
fi
count="$(jq '.devices | length' <<< "${slot_json}")"
[[ "${count}" == "1" ]] || die "${count} YubiKeys detected — insert exactly one at a time"

serial="$(jq -r '.devices[0].serial' <<< "${slot_json}")"
firmware="$(jq -r '.devices[0].firmware' <<< "${slot_json}")"
dev_err="$(jq -r '.devices[0].error // empty' <<< "${slot_json}")"
log "YubiKey ${serial} (firmware ${firmware}) — checking ${ENV_ID} in PIV slot ${SLOT}"

failures=0
check() {
  local label="$1" expected="$2" actual="$3"
  local e a
  e="$(tr '[:lower:]' '[:upper:]' <<< "${expected}")"
  a="$(tr '[:lower:]' '[:upper:]' <<< "${actual}")"
  if [[ "${e}" == "${a}" ]]; then
    ok "${label}: ${actual}"
  else
    bad "${label}: expected ${expected}, got ${actual:-<none>}"
    failures=$((failures + 1))
  fi
}

if [[ -z "${dev_err}" ]]; then
  check "key type" "${EXPECTED_KEY_TYPE}" "$(jq -r '.devices[0].key_type // ""' <<< "${slot_json}")"
  check "PIN policy" "${EXPECTED_PIN_POLICY}" "$(jq -r '.devices[0].pin_policy // ""' <<< "${slot_json}")"
  check "touch policy" "${EXPECTED_TOUCH}" "$(jq -r '.devices[0].touch_policy // ""' <<< "${slot_json}")"
else
  log "  SKIP  slot policies: no PIV metadata on firmware ${firmware} (needs 5.3+)"
  log "        (${dev_err})"
  probe="$(jq -r '.devices[0].probe // empty' <<< "${slot_json}")"
  present="$(jq -r '.devices[0].key_present // empty' <<< "${slot_json}")"
  case "${present}" in
    true)  ok "slot ${SLOT} holds a private key — ${probe}" ;;
    false) bad "slot ${SLOT} is EMPTY — ${probe}; this card was reset or never provisioned"
           failures=$((failures + 1)) ;;
    *)     log "        slot probe inconclusive (${probe:-no result})" ;;
  esac
fi

if [[ "$(jq -r '.devices[0].has_certificate // false' <<< "${slot_json}")" == "true" ]]; then
  ok "slot certificate present (ykcs11 / dfx --hsm can see the key)"
elif [[ "${REQUIRE_CERT}" == "true" ]]; then
  bad "slot ${SLOT} holds no certificate — ykcs11 cannot expose the key, so dfx --hsm / icp signing will not find it"
  failures=$((failures + 1))
else
  log "  SKIP  slot certificate: not expected by this manifest"
fi

if [[ -n "${EXPECTED_SERIALS}" ]]; then
  if [[ " ${EXPECTED_SERIALS} " == *" ${serial} "* ]]; then
    ok "serial listed for ${ENV_ID}"
  else
    bad "serial ${serial} is not a ${ENV_ID} key (expected one of: ${EXPECTED_SERIALS})"
    failures=$((failures + 1))
  fi
fi

pub="$(mktemp)"
msg="$(mktemp)"
sig="$(mktemp)"
trap 'rm -f "${pub}" "${msg}" "${sig}"' EXIT
jq -r '.devices[0].public_key_pem // empty' <<< "${slot_json}" > "${pub}"

if [[ -s "${pub}" ]]; then
  # `openssl pkey`, not `openssl ec`: an RSA or P-384 slot must not fail here.
  principal="$(openssl pkey -pubin -in "${pub}" -pubout -outform DER 2>/dev/null \
    | "${PYTHON}" "${PRINCIPAL_HELPER}")"
  check "IC principal" "${EXPECTED_PRINCIPAL}" "${principal}"
else
  # Pre-5.3 firmware cannot hand back the public key, so prove possession the
  # other way: make the card sign, and verify against the manifest public key.
  [[ -n "${EXPECTED_PUBKEY}" ]] \
    || die "firmware ${firmware} exposes no public key — need --manifest to verify by signature"
  printf '%s' "${EXPECTED_PUBKEY}" > "${pub}"
  printf 'realms-verify-%s' "${serial}" > "${msg}"
  pin="${CEREMONY_VERIFY_PIN:-}"
  if [[ -z "${pin}" ]]; then
    read -rsp "[verify] PIV PIN for ${serial}: " pin
    printf '\n'
  fi
  # Retrying an empty PIN three times only misreports it as a missed touch.
  [[ -n "${pin}" ]] \
    || die "no PIN entered — firmware ${firmware} can only be verified by an on-card signature, which needs the PIV PIN (or CEREMONY_VERIFY_PIN)"
  err="$(mktemp)"
  trap 'rm -f "${pub}" "${msg}" "${sig}" "${err}"' EXIT
  _sign_challenge() {
    # Prefer yubikit (already required) so a verification laptop does not need
    # yubico-piv-tool. Keep that CLI as a fallback when present.
    if printf '%s' "${pin}" | "${PYTHON}" "${SIGN_HELPER}" "${SLOT}" "${msg}" "${sig}" \
        "${EXPECTED_KEY_TYPE}" 2>"${err}"; then
      return 0
    fi
    if command -v yubico-piv-tool >/dev/null 2>&1; then
      YKCS11_DEVICE="${serial}" yubico-piv-tool -v 1 -a verify-pin --sign \
        -s "${SLOT}" -H SHA256 -A "${EXPECTED_KEY_TYPE}" -P "${pin}" \
        -i "${msg}" -o "${sig}" >/dev/null 2>"${err}"
      return $?
    fi
    return 1
  }
  signed=0
  for attempt in 1 2 3; do
    log "signing a challenge on-card — touch the key NOW if it blinks (attempt ${attempt}/3)"
    if _sign_challenge; then
      signed=1
      break
    fi
    log "        card refused to sign: $(tr '\n' ' ' < "${err}" | sed 's/  */ /g')"
  done
  if [[ "${signed}" != "1" ]]; then
    if grep -qiE 'pin|auth' "${err}"; then
      bad "card never signed: $(tr '\n' ' ' < "${err}" | sed 's/  */ /g')"
    else
      bad "card never signed — with touch policy '${EXPECTED_TOUCH}' it waits ~15s for a touch on the metal contact"
    fi
    failures=$((failures + 1))
  elif openssl dgst -sha256 -verify "${pub}" -signature "${sig}" "${msg}" >/dev/null 2>&1; then
    ok "IC principal: on-card signature verifies against ${EXPECTED_PRINCIPAL}"
  else
    bad "card signed with a different key than the ${ENV_ID} public key"
    failures=$((failures + 1))
  fi
fi

if [[ "${failures}" -eq 0 ]]; then
  log "YubiKey ${serial}: OK — holds the ${ENV_ID} signing key"
else
  die "YubiKey ${serial}: ${failures} check(s) failed"
fi
