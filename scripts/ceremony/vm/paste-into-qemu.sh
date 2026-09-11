#!/usr/bin/env bash
# Paste a shell command into the focused QEMU window (host clipboard → guest terminal).
# QEMU GTK does not share clipboard with the guest — use this from a HOST terminal.
#
# Usage:
#   ./vm/paste-into-qemu.sh 'sudo mount -t 9p -o trans=virtio realms_ceremony /opt/realms-ceremony'
#   echo 'bash /opt/realms-ceremony/usb/launch-ceremony-terminal.sh' | ./vm/paste-into-qemu.sh
#
set -euo pipefail

WINDOW_NAME="${CEREMONY_QEMU_WINDOW_NAME:-realms-ceremony-live}"
DELAY_MS="${CEREMONY_QEMU_TYPE_DELAY_MS:-8}"
TEXT="${1:-}"

if [[ -z "${TEXT}" ]]; then
  TEXT="$(cat)"
fi
[[ -n "${TEXT}" ]] || { echo "usage: $0 'command to type'" >&2; exit 1; }

if ! command -v xdotool >/dev/null 2>&1; then
  echo "install xdotool on the host: sudo apt install xdotool" >&2
  echo "or type the command manually in the VM terminal:" >&2
  echo "  ${TEXT}" >&2
  exit 1
fi

wid="$(xdotool search --name "${WINDOW_NAME}" | head -1)"
if [[ -z "${wid}" ]]; then
  echo "QEMU window not found (name ~ ${WINDOW_NAME})" >&2
  exit 1
fi

xdotool windowactivate --sync "${wid}"
sleep 0.4
xdotool type --delay "${DELAY_MS}" -- "${TEXT}"
xdotool key Return
echo "[paste-into-qemu] sent to QEMU window ${wid}"
