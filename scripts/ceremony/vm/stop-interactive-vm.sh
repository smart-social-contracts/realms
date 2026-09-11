#!/usr/bin/env bash
# Stop the interactive ceremony QEMU VM and serial bootstrap helper.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VM_DIR="${SCRIPT_DIR}/cache"

log() { printf '[stop-vm] %s\n' "$*" >&2; }

stop_pid_file() {
  local label="$1" file="$2"
  [[ -f "${file}" ]] || return 0
  local pid
  pid="$(cat "${file}")"
  if kill -0 "${pid}" 2>/dev/null; then
    log "stopping ${label} (pid ${pid})"
    kill "${pid}" 2>/dev/null || true
    sleep 2
    kill -9 "${pid}" 2>/dev/null || true
  fi
  rm -f "${file}"
}

stop_pid_file "serial bootstrap" "${VM_DIR}/serial_bootstrap.pid"
stop_pid_file "QEMU" "${VM_DIR}/interactive-qemu.pid"

while read -r pid; do
  [[ -n "${pid}" ]] || continue
  if kill -0 "${pid}" 2>/dev/null; then
    log "stopping QEMU (pid ${pid})"
    kill "${pid}" 2>/dev/null || true
    sleep 2
    kill -9 "${pid}" 2>/dev/null || true
  fi
done < <(pgrep -f 'qemu-system-x86_64.*realms-ceremony-live' || true)

log "done"
