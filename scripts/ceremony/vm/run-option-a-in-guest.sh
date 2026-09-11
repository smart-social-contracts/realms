#!/usr/bin/env bash
# Host-side: run Option A inside the QEMU live session (mount 9p + launch ceremony terminal).
# Uses the serial console — works on Wayland hosts where paste-into-qemu.sh cannot type.
#
# Usage (VM already running with serial from run-ubuntu-2204-vm-interactive.sh):
#   ./vm/run-option-a-in-guest.sh
#
# Or restart VM and run Option A automatically:
#   ./vm/run-option-a-in-guest.sh --restart-vm
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CEREMONY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VM_DIR="${SCRIPT_DIR}/cache"
SERIAL_PORT="${CEREMONY_VM_SERIAL_PORT:-4445}"
BOOT_WAIT="${CEREMONY_OPTION_A_BOOT_WAIT:-75}"
RESTART=0

log() { printf '[option-a] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --restart-vm) RESTART=1 ;;
    --boot-wait) BOOT_WAIT="${2:-}"; shift 2; continue ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

qemu_running() {
  pgrep -f 'qemu-system-x86_64.*realms-ceremony-live' >/dev/null 2>&1
}

stop_qemu() {
  local pid
  pid="$(pgrep -f 'qemu-system-x86_64.*realms-ceremony-live' | head -1 || true)"
  [[ -n "${pid}" ]] || return 0
  log "stopping QEMU (pid ${pid})"
  kill "${pid}" 2>/dev/null || true
  sleep 2
  kill -9 "${pid}" 2>/dev/null || true
}

start_vm_bg() {
  log "starting interactive VM in background (serial on localhost:${SERIAL_PORT})"
  nohup "${SCRIPT_DIR}/run-ubuntu-2204-vm-interactive.sh" \
    >"${VM_DIR}/interactive-vm.log" 2>&1 &
  echo $! > "${VM_DIR}/interactive-vm-launcher.pid"
}

if [[ "${RESTART}" == "1" ]]; then
  stop_qemu
  start_vm_bg
elif ! qemu_running; then
  log "no running ceremony VM — starting one"
  start_vm_bg
else
  if ! ss -tln 2>/dev/null | grep -q ":${SERIAL_PORT} "; then
    die "VM is running without serial (port ${SERIAL_PORT} closed). Re-run with --restart-vm"
  fi
  log "using running ceremony VM (serial localhost:${SERIAL_PORT})"
fi

log "Option A: mount virtio-9p → /opt/realms-ceremony, then launch ceremony terminal"
python3 "${SCRIPT_DIR}/serial_guest_cmd.py" \
  --port "${SERIAL_PORT}" \
  --boot-wait "${BOOT_WAIT}"

log "OK — check the VM window for the ceremony terminal"
