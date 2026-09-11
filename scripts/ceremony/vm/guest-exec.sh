#!/usr/bin/env bash
# Run a shell command inside the QEMU ceremony live session from the host.
# Bootstraps openssh-server over serial if SSH is not up yet.
#
# Usage:
#   ./vm/guest-exec.sh 'sudo bash /opt/realms-ceremony/usb/attach-ceremony-from-host.sh'
#   ./vm/guest-exec.sh --attach
#   ./vm/guest-exec.sh --option-a
#   ./vm/guest-exec.sh --wait-ssh
#   ./vm/guest-exec.sh --restart-vm --option-a
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VM_DIR="${SCRIPT_DIR}/cache"
SSH_PORT="${CEREMONY_VM_SSH_PORT:-2222}"
SERIAL_PORT="${CEREMONY_VM_SERIAL_PORT:-4445}"
SSH_KEY="${VM_DIR}/guest_exec_id_ed25519"
BOOTSTRAP_LOG="${VM_DIR}/serial_bootstrap.log"
BOOTSTRAP_PID_FILE="${VM_DIR}/serial_bootstrap.pid"
ATTACH=0
OPTION_A=0
WAIT_SSH=0
RESTART_VM=0
CMD=""

log() { printf '[guest-exec] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --attach) ATTACH=1 ;;
    --option-a) OPTION_A=1 ;;
    --wait-ssh) WAIT_SSH=1 ;;
    --restart-vm) RESTART_VM=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) CMD="$*"; break ;;
  esac
  shift
done

if [[ "${ATTACH}" == "1" ]]; then
  CMD='sudo bash -c "modprobe 9p 2>/dev/null; modprobe 9pnet 2>/dev/null; modprobe 9pnet_virtio 2>/dev/null; mkdir -p /opt/realms-ceremony; mount -t 9p -o trans=virtio,version=9p2000.L realms_ceremony /opt/realms-ceremony || (curl -fsSL http://10.0.2.2:8890/install-ceremony-update.sh | bash -s 8890)"'
elif [[ "${OPTION_A}" == "1" ]]; then
  CMD='sudo bash -c "modprobe 9p 2>/dev/null; modprobe 9pnet 2>/dev/null; modprobe 9pnet_virtio 2>/dev/null; mkdir -p /opt/realms-ceremony; mount -t 9p -o trans=virtio,version=9p2000.L realms_ceremony /opt/realms-ceremony || (curl -fsSL http://10.0.2.2:8890/install-ceremony-update.sh | bash -s 8890)"; DISPLAY=:0 bash /opt/realms-ceremony/usb/launch-ceremony-terminal.sh'
fi

if [[ "${RESTART_VM}" == "1" ]]; then
  exec "${SCRIPT_DIR}/restart-interactive-vm.sh" ${OPTION_A:+--option-a}
fi

[[ -n "${CMD}" || "${WAIT_SSH}" == "1" || "${ATTACH}" == "1" || "${OPTION_A}" == "1" ]] \
  || die "usage: $0 'command' | --attach | --option-a | --wait-ssh | --restart-vm"

qemu_running() {
  pgrep -f 'qemu-system-x86_64.*realms-ceremony-live' >/dev/null 2>&1
}

ensure_ssh_key() {
  if [[ ! -f "${SSH_KEY}" ]]; then
    ssh-keygen -t ed25519 -N "" -f "${SSH_KEY}" -q
  fi
}

ssh_guest() {
  ssh -i "${SSH_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=5 -o BatchMode=yes \
    -p "${SSH_PORT}" "ubuntu@127.0.0.1" "$@"
}

ssh_ready() {
  ssh_guest true 2>/dev/null
}

start_serial_bootstrap() {
  if [[ -f "${BOOTSTRAP_PID_FILE}" ]]; then
    local pid
    pid="$(cat "${BOOTSTRAP_PID_FILE}")"
    if kill -0 "${pid}" 2>/dev/null; then
      log "serial bootstrap already running (pid ${pid})"
      return 0
    fi
  fi
  die "serial bootstrap not running — restart VM: ./vm/restart-interactive-vm.sh"
}

wait_for_ssh() {
  local tries="${CEREMONY_VM_SSH_TRIES:-90}"
  local i
  for ((i = 1; i <= tries; i++)); do
    if ssh_ready; then
      log "SSH ready on localhost:${SSH_PORT}"
      return 0
    fi
    if [[ -f "${BOOTSTRAP_PID_FILE}" ]]; then
      local pid
      pid="$(cat "${BOOTSTRAP_PID_FILE}")"
      if ! kill -0 "${pid}" 2>/dev/null; then
        if grep -q "serial bootstrap finished" "${BOOTSTRAP_LOG}" 2>/dev/null; then
          rm -f "${BOOTSTRAP_PID_FILE}"
        else
          log "serial bootstrap failed — tail:"
          tail -20 "${BOOTSTRAP_LOG}" >&2 || true
          die "serial bootstrap did not finish"
        fi
      fi
    fi
    if (( i % 6 == 0 )); then
      log "waiting for SSH... ($((i * 5))s)"
    fi
    sleep 5
  done
  die "SSH not reachable on localhost:${SSH_PORT}"
}

run_via_serial() {
  log "SSH unavailable — using serial console (guest output streams below)"
  python3 -u "${SCRIPT_DIR}/serial_guest_cmd.py" --boot-wait 0 --cmd "${CMD}"
}

main() {
  qemu_running || die "ceremony VM not running — start: ./vm/restart-interactive-vm.sh"

  if ssh_ready; then
    if [[ "${WAIT_SSH}" == "1" ]]; then
      log "SSH ready"
      exit 0
    fi
    log "running in guest via SSH: ${CMD}"
    ssh_guest "bash -lc $(printf '%q' "${CMD}")"
    return 0
  fi

  if [[ "${WAIT_SSH}" == "1" ]]; then
    wait_for_ssh
    log "SSH ready"
    exit 0
  fi

  run_via_serial
}

main
