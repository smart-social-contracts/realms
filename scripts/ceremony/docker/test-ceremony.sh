#!/usr/bin/env bash
# Run inside Docker — exercises the full simulate ceremony flow.
set -euo pipefail

CEREMONY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export CEREMONY_ROOT="/tmp/realms-ceremony-test"
export CEREMONY_SIMULATE=1
export CEREMONY_FORCE_OFFLINE=1
export CEREMONY_USE_TMPFS=0

cd "${CEREMONY_DIR}"

echo "== simulate: run-offline =="
./realms-key-ceremony.sh run-offline

manifest="${CEREMONY_ROOT}/artifacts/manifest.json"
[[ -f "${manifest}" ]] || { echo "missing manifest"; exit 1; }

echo "== validate manifest =="
jq -e '.environments.dev.principal | length > 20' "${manifest}" >/dev/null
jq -e '.environments.prod.principal | length > 20' "${manifest}" >/dev/null
jq -e '.environments.dev.touch_policy == "never"' "${manifest}" >/dev/null
jq -e '.environments.prod.touch_policy == "cached"' "${manifest}" >/dev/null
jq -e '.simulate' "${manifest}" >/dev/null

dev_p="$(jq -r '.environments.dev.principal' "${manifest}")"
prod_p="$(jq -r '.environments.prod.principal' "${manifest}")"
[[ "${dev_p}" != "${prod_p}" ]] || { echo "dev and prod principals must differ"; exit 1; }

echo "== validate prod copies share principal =="
# prod-principal.txt written during provision
[[ -f "${CEREMONY_ROOT}/artifacts/prod-principal.txt" ]] || exit 1
[[ "$(wc -l < "${CEREMONY_ROOT}/artifacts/prod-serials.txt")" -eq 3 ]] || exit 1

echo "== export-pem (opt-in) =="
export_dir="${CEREMONY_ROOT}/exported-dev-identity"
if CEREMONY_EXPORT_PEM_I_UNDERSTAND=1 ./realms-key-ceremony.sh export-pem dev "${export_dir}" >/tmp/export-pem.log; then
  :
else
  echo "export-pem failed"; cat /tmp/export-pem.log; exit 1
fi
[[ -f "${export_dir}/identity.pem" ]] || { echo "missing exported identity.pem"; exit 1; }
openssl ec -in "${export_dir}/identity.pem" -check -noout
tmp_home="$(mktemp -d)"
HOME="${tmp_home}" DO_NOT_TRACK=1 icp identity import export-verify \
  --from-pem "${export_dir}/identity.pem" --storage plaintext >/dev/null
exported_p="$(HOME="${tmp_home}" DO_NOT_TRACK=1 icp identity principal --identity export-verify)"
rm -rf "${tmp_home}"
[[ "${exported_p}" == "${dev_p}" ]] || { echo "exported PEM principal mismatch: ${exported_p} vs ${dev_p}"; exit 1; }

explicit_pem="${export_dir}/explicit.pem"
CEREMONY_EXPORT_PEM_I_UNDERSTAND=1 ./realms-key-ceremony.sh export-pem dev "${explicit_pem}" >/dev/null
[[ -f "${explicit_pem}" ]] || { echo "missing explicit.pem export"; exit 1; }
cmp -s "${export_dir}/identity.pem" "${explicit_pem}" || { echo "explicit.pem differs from identity.pem"; exit 1; }

if ./realms-key-ceremony.sh export-pem dev "${CEREMONY_ROOT}/no-ack" 2>/dev/null; then
  echo "export-pem without opt-in should fail"; exit 1
fi

echo "== simulate: destroy =="
./realms-key-ceremony.sh destroy
[[ ! -d "${CEREMONY_ROOT}/secrets" ]] || [[ -z "$(ls -A "${CEREMONY_ROOT}/secrets" 2>/dev/null || true)" ]]

echo "PASS: ceremony simulate flow"
