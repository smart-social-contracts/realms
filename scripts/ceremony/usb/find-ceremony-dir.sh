#!/usr/bin/env bash
# Print the absolute path to the ceremony scripts (attached from host or embedded on USB).
set -euo pipefail

CEREMONY_TARGET="${CEREMONY_TARGET:-/opt/realms-ceremony}"

_script="${BASH_SOURCE[0]}"
while [[ -L "${_script}" ]]; do
  _dir="$(cd "$(dirname "${_script}")" && pwd)"
  _script="$(readlink "${_script}")"
  [[ "${_script}" == /* ]] || _script="${_dir}/${_script}"
done
_bootstrap_usb="$(cd "$(dirname "${_script}")" && pwd)"

if [[ -f "${CEREMONY_TARGET}/realms-key-ceremony.sh" ]]; then
  printf '%s\n' "${CEREMONY_TARGET}"
  exit 0
fi

if [[ -f "${_bootstrap_usb}/realms-key-ceremony.sh" ]]; then
  printf '%s\n' "$(cd "${_bootstrap_usb}/.." && pwd)"
  exit 0
fi

_attach="${_bootstrap_usb}/attach-ceremony-from-host.sh"
if [[ -f "${_attach}" ]]; then
  if [[ "${EUID}" -eq 0 ]]; then
    exec bash "${_attach}"
  fi
  if command -v sudo >/dev/null 2>&1; then
    exec sudo bash "${_attach}"
  fi
  printf 'ceremony not attached — run: sudo bash %s\n' "${_attach}" >&2
  exit 1
fi

_candidates=(
  /cdrom/realms-ceremony
  /run/live/mount/medium/realms-ceremony
  /lib/live/mount/medium/realms-ceremony
  /isodevice/realms-ceremony
)
for d in "${_candidates[@]}"; do
  if [[ -f "${d}/realms-key-ceremony.sh" ]]; then
    printf '%s\n' "${d}"
    exit 0
  fi
done

printf 'realms-ceremony directory not found — boot from the prepared ceremony USB or attach from host\n' >&2
exit 1
