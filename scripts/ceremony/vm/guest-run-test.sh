#!/usr/bin/env bash
# Runs inside the Ubuntu 22.04 VM after the host copies the ceremony tree here.
# Exercises the real apt packages and network gates (simulate mode for YubiKey).
set -euo pipefail

CEREMONY_DIR="${1:-/opt/realms-ceremony}"
cd "${CEREMONY_DIR}"

log() { printf '[guest-test] %s\n' "$*" >&2; }
die() { log "FAIL: $*"; exit 1; }

log "Ubuntu (Desktop live expected):"
. /etc/os-release
[[ "${VERSION_ID}" == "22.04" ]] || die "expected Ubuntu 22.04, got ${VERSION_ID}"

log "== online-setup (real apt) =="
sudo env DO_NOT_TRACK=1 ./realms-key-ceremony.sh online-setup

log "== verify installed tools =="
command -v ykman >/dev/null || die "ykman missing"
command -v icp >/dev/null || die "icp missing"
[[ -f /usr/lib/x86_64-linux-gnu/libykcs11.so ]] || die "libykcs11.so missing"
systemctl is-active --quiet pcscd || die "pcscd not running"
icp --version >/dev/null || die "icp cannot execute"

log "== network gate: check-offline must fail while online =="
if sudo ./realms-key-ceremony.sh check-offline 2>/dev/null; then
  die "check-offline succeeded while VM still has network"
fi
log "network gate OK (rejected while online)"

log "== simulate offline ceremony (no YubiKey) =="
export CEREMONY_ROOT=/tmp/realms-ceremony-guest
export CEREMONY_SIMULATE=1
export CEREMONY_FORCE_OFFLINE=1
export CEREMONY_USE_TMPFS=0
export DO_NOT_TRACK=1
rm -rf "${CEREMONY_ROOT}"
sudo -E env \
  CEREMONY_ROOT="${CEREMONY_ROOT}" \
  CEREMONY_SIMULATE=1 \
  CEREMONY_FORCE_OFFLINE=1 \
  CEREMONY_USE_TMPFS=0 \
  DO_NOT_TRACK=1 \
  ./realms-key-ceremony.sh run-offline

sudo chown -R ubuntu:ubuntu "${CEREMONY_ROOT}"

manifest="${CEREMONY_ROOT}/artifacts/manifest.json"
[[ -f "${manifest}" ]] || die "manifest missing"
jq -e '.environments.dev.principal and .environments.prod.principal' "${manifest}" >/dev/null \
  || die "manifest principals missing"
dev_p="$(jq -r '.environments.dev.principal' "${manifest}")"
prod_p="$(jq -r '.environments.prod.principal' "${manifest}")"
[[ "${dev_p}" != "${prod_p}" ]] || die "dev and prod principals must differ"
[[ "$(wc -l < "${CEREMONY_ROOT}/artifacts/prod-serials.txt")" -eq 3 ]] || die "expected 3 prod serials"

log "== destroy =="
sudo -E env CEREMONY_ROOT="${CEREMONY_ROOT}" ./realms-key-ceremony.sh destroy

log "PASS: Ubuntu 22.04 VM ceremony test"
