#!/usr/bin/env bash
# Run INSIDE the ceremony VM. Copies public ceremony artifacts out of the tmpfs
# workspace onto the 9p mount so they survive VM shutdown. Never copies secrets
# (signing key PEMs, operator credentials) — those stay in the ceremony.
set -euo pipefail

SRC="${CEREMONY_ROOT:-/run/realms-ceremony}/artifacts"
DEST="${1:-/opt/realms-ceremony/artifacts}"

[[ -d "${SRC}" ]] || { echo "no ceremony artifacts at ${SRC}" >&2; exit 1; }

# Copies 2..N of an environment only appended to <env>-serials.txt; make sure the
# manifest names every provisioned key before it leaves the machine.
for serials in "${SRC}"/*-serials.txt; do
  [[ -f "${serials}" ]] || continue
  env_id="$(basename "${serials}" -serials.txt)"
  list="$(jq -R -s 'split("\n") | map(select(length > 0))' "${serials}")"
  tmp="$(mktemp)"
  jq --arg env "${env_id}" --argjson list "${list}" \
    'if .environments[$env] then .environments[$env].yubikey_serials = $list else . end' \
    "${SRC}/manifest.json" > "${tmp}"
  mv "${tmp}" "${SRC}/manifest.json"
  chmod 600 "${SRC}/manifest.json"
  echo "manifest: ${env_id} serials = $(tr '\n' ' ' < "${serials}")"
done

mkdir -p "${DEST}"
for f in manifest.json ceremony-config.json *-public.pem *-principal.txt *-serials.txt; do
  for path in "${SRC}"/${f}; do
    [[ -f "${path}" ]] || continue
    cp "${path}" "${DEST}/"
    chmod 644 "${DEST}/$(basename "${path}")"
    echo "saved $(basename "${path}")"
  done
done

if compgen -G "${DEST}/*.pem" > /dev/null && grep -rlq 'PRIVATE KEY' "${DEST}" 2>/dev/null; then
  echo "REFUSING: a private key reached ${DEST}" >&2
  exit 1
fi
echo "artifacts saved to ${DEST}"
