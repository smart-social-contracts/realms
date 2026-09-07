#!/usr/bin/env bash
# Boot Ubuntu 22.04 **Desktop** live ISO in QEMU and run the ceremony self-test.
#
# Matches the real ceremony environment: Ubuntu 22.04 Desktop live USB ("Try Ubuntu"),
# online apt install, then offline key generation (simulated YubiKey in the test).
#
# Downloads the official Desktop ISO on first run (~5 GB). Typical runtime: 20–35 minutes.
#
# Usage:
#   ./vm/run-ubuntu-2204-vm-test.sh           # full test
#   ./vm/run-ubuntu-2204-vm-test.sh --keep-vm # leave VM running (SSH on port 2222)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CEREMONY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VM_DIR="${SCRIPT_DIR}/cache"
ISO_URL="https://releases.ubuntu.com/22.04/ubuntu-22.04.5-desktop-amd64.iso"
ISO_PATH="${VM_DIR}/ubuntu-22.04.5-desktop-amd64.iso"
SEED_PATH="${VM_DIR}/cidata.iso"
SSH_PORT="${CEREMONY_VM_SSH_PORT:-2222}"
SSH_KEY="${VM_DIR}/test_id_rsa"
RAM_MB="${CEREMONY_VM_RAM_MB:-6144}"
KEEP_VM=0

log() { printf '[vm-test] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-vm) KEEP_VM=1 ;;
    --reuse-disk)
      log "note: --reuse-disk is ignored for Desktop live ISO (always boots live session)"
      ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required: $1"
}

require_cmd qemu-system-x86_64
require_cmd genisoimage
require_cmd ssh
require_cmd curl

mkdir -p "${VM_DIR}"

download_iso() {
  if [[ -f "${ISO_PATH}" ]]; then
    log "ISO present: ${ISO_PATH}"
    return 0
  fi
  log "downloading official Ubuntu 22.04.5 Desktop ISO (~5 GB)..."
  curl -fL --progress-bar -o "${ISO_PATH}.partial" "${ISO_URL}"
  mv "${ISO_PATH}.partial" "${ISO_PATH}"
  log "ISO saved: ${ISO_PATH}"
}

build_seed_iso() {
  log "building cloud-init seed ISO (cidata) for live session"
  if [[ ! -f "${SSH_KEY}" ]]; then
    ssh-keygen -t ed25519 -N "" -f "${SSH_KEY}" -q
  fi
  local pub
  pub="$(cat "${SSH_KEY}.pub")"
  local ud="${VM_DIR}/user-data.generated"
  {
    cat "${SCRIPT_DIR}/cloud-init/user-data"
    printf 'ssh_authorized_keys:\n  - "%s"\n' "${pub}"
  } > "${ud}"
  genisoimage -output "${SEED_PATH}" -volid cidata -joliet -rock \
    -input-charset utf-8 \
    "${ud}" \
    "${SCRIPT_DIR}/cloud-init/meta-data"
}

qemu_kvm_args() {
  if [[ -r /dev/kvm ]]; then
    printf '%s\n' -enable-kvm
  fi
}

start_vm() {
  local pid_file="${VM_DIR}/qemu.pid"
  local log_file="${VM_DIR}/qemu.log"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    log "QEMU already running (pid $(cat "${pid_file}"))"
    return 0
  fi
  log "starting QEMU Desktop live (SSH -> localhost:${SSH_PORT})"
  log "serial console log: ${log_file}"
  # shellcheck disable=SC2046
  qemu-system-x86_64 \
    $(qemu_kvm_args) \
    -m "${RAM_MB}" \
    -smp 2 \
    -cpu host \
    -drive "file=${ISO_PATH},if=virtio,media=cdrom,readonly=on" \
    -drive "file=${SEED_PATH},if=virtio,format=raw" \
    -boot order=d \
    -netdev "user,id=net0,hostfwd=tcp::${SSH_PORT}-:22" \
    -device virtio-net-pci,netdev=net0 \
    -display none \
    -serial "file:${log_file}" \
    -daemonize \
    -pidfile "${pid_file}"
}

ssh_vm() {
  ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=5 -o BatchMode=yes \
    -p "${SSH_PORT}" "ubuntu@127.0.0.1" "$@"
}

wait_for_ssh() {
  # Desktop live + cloud-init + openssh-server install can take a while.
  local tries="${CEREMONY_VM_SSH_TRIES:-180}"
  local i
  log "waiting for SSH on live session (up to ${tries}×10s)..."
  for ((i = 1; i <= tries; i++)); do
    if ssh_vm true 2>/dev/null; then
      log "SSH ready after ~$((i * 10))s"
      return 0
    fi
    if (( i % 6 == 0 )); then
      log "still waiting... ($((i * 10))s) — tail ${VM_DIR}/qemu.log for boot progress"
    fi
    sleep 10
  done
  die "SSH not reachable — see ${VM_DIR}/qemu.log"
}

stop_vm() {
  local pid_file="${VM_DIR}/qemu.pid"
  [[ -f "${pid_file}" ]] || return 0
  local pid
  pid="$(cat "${pid_file}")"
  if kill -0 "${pid}" 2>/dev/null; then
    log "stopping QEMU (pid ${pid})"
    kill "${pid}" 2>/dev/null || true
    sleep 3
    kill -9 "${pid}" 2>/dev/null || true
  fi
  rm -f "${pid_file}"
}

run_guest_test() {
  log "copying ceremony tree to live session"
  ssh_vm "sudo mkdir -p /opt/realms-ceremony && sudo chown ubuntu:ubuntu /opt/realms-ceremony"
  tar -C "${CEREMONY_DIR}" -czf - . | ssh_vm "tar -xzf - -C /opt/realms-ceremony"
  ssh_vm "chmod +x /opt/realms-ceremony/realms-key-ceremony.sh /opt/realms-ceremony/vm/guest-run-test.sh"
  log "running guest test"
  ssh_vm "bash /opt/realms-ceremony/vm/guest-run-test.sh /opt/realms-ceremony"
}

cleanup() {
  if [[ "${KEEP_VM}" == "1" ]]; then
    log "keeping VM running (--keep-vm)"
    log "SSH: ssh -i ${SSH_KEY} -p ${SSH_PORT} ubuntu@127.0.0.1"
    return 0
  fi
  stop_vm
}

trap cleanup EXIT

main() {
  download_iso
  build_seed_iso
  start_vm
  wait_for_ssh
  run_guest_test
  log "PASS: Ubuntu 22.04 Desktop live ISO VM test"
}

main
