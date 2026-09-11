#!/usr/bin/env bash
# Attach live ceremony scripts from the QEMU host (virtio-9p, then HTTP push).
set -euo pipefail

CEREMONY_TARGET="${CEREMONY_TARGET:-/opt/realms-ceremony}"
CEREMONY_PUSH_PORT="${CEREMONY_PUSH_PORT:-8890}"
CEREMONY_HOST_GATEWAY="${CEREMONY_HOST_GATEWAY:-10.0.2.2}"

log() { printf '[auto-attach] %s\n' "$*" >&2; }

if [[ -f "${CEREMONY_TARGET}/realms-key-ceremony.sh" ]]; then
  log "already attached at ${CEREMONY_TARGET}"
  exit 0
fi

for attach in \
  /opt/realms-ceremony/usb/attach-ceremony-from-host.sh \
  /cdrom/realms-ceremony/usb/attach-ceremony-from-host.sh \
  /run/live/mount/medium/realms-ceremony/usb/attach-ceremony-from-host.sh; do
  if [[ -x "${attach}" ]]; then
    if sudo -n bash "${attach}"; then
      exit 0
    fi
  fi
done

base="http://${CEREMONY_HOST_GATEWAY}:${CEREMONY_PUSH_PORT}"
if command -v curl >/dev/null 2>&1 \
  && curl -fsSL --max-time 15 "${base}/install-ceremony-update.sh" -o /dev/null; then
  log "using HTTP push from host (${base})"
  curl -fsSL "${base}/install-ceremony-update.sh" | sudo bash -s "${CEREMONY_PUSH_PORT}"
  exit 0
fi

log "attach failed — on the host run: ./vm/run-ubuntu-2204-vm-interactive.sh"
exit 1
