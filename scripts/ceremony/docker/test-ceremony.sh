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
jq -e '.simulate == true' "${manifest}" >/dev/null

dev_p="$(jq -r '.environments.dev.principal' "${manifest}")"
prod_p="$(jq -r '.environments.prod.principal' "${manifest}")"
[[ "${dev_p}" != "${prod_p}" ]] || { echo "dev and prod principals must differ"; exit 1; }

echo "== validate prod copies share principal =="
# prod-principal.txt written during provision
[[ -f "${CEREMONY_ROOT}/artifacts/prod-principal.txt" ]] || exit 1
[[ "$(wc -l < "${CEREMONY_ROOT}/artifacts/prod-serials.txt")" -eq 3 ]] || exit 1

echo "== simulate: destroy =="
./realms-key-ceremony.sh destroy
[[ ! -d "${CEREMONY_ROOT}/secrets" ]] || [[ -z "$(ls -A "${CEREMONY_ROOT}/secrets" 2>/dev/null || true)" ]]

echo "PASS: ceremony simulate flow"
