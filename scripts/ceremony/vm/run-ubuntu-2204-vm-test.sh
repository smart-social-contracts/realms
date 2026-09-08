#!/usr/bin/env bash
# Boot Ubuntu 22.04 **Desktop** live ISO in QEMU and run the ceremony self-test.
#
# Boots the same casper live environment as "Try Ubuntu" on the Desktop USB stick,
# using direct kernel boot + nocloud (headless-friendly). Official ISO:
#   ubuntu-22.04.5-desktop-amd64.iso
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
SEED_DIR="${VM_DIR}/nocloud-seed"
HTTP_PORT="${CEREMONY_VM_HTTP_PORT:-8888}"
SERIAL_PORT="${CEREMONY_VM_SERIAL_PORT:-4445}"
VMLINUZ="${VM_DIR}/vmlinuz"
INITRD="${VM_DIR}/initrd"
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
      log "note: --reuse-disk is ignored (always boots fresh live session)"
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
require_cmd xorriso
require_cmd ssh
require_cmd curl
require_cmd python3

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

extract_casper() {
  if [[ -f "${VMLINUZ}" && -f "${INITRD}" ]]; then
    log "casper kernel/initrd already extracted"
    return 0
  fi
  log "extracting casper vmlinuz + initrd from Desktop ISO"
  xorriso -osirrox on -indev "${ISO_PATH}" -extract /casper/vmlinuz "${VMLINUZ}"
  xorriso -osirrox on -indev "${ISO_PATH}" -extract /casper/initrd "${INITRD}"
}

build_nocloud_seed() {
  log "building nocloud seed (user-data + meta-data) for live session"
  if [[ ! -f "${SSH_KEY}" ]]; then
    ssh-keygen -t ed25519 -N "" -f "${SSH_KEY}" -q
  fi
  local pub
  pub="$(cat "${SSH_KEY}.pub")"
  local ud="${VM_DIR}/user-data.generated"
  # Keys must live under the ubuntu user block (not at file root).
  awk -v pub="${pub}" '
    /# ssh_authorized_keys injected/ {
      print "    ssh_authorized_keys:"
      printf "      - \"%s\"\n", pub
      next
    }
    { print }
  ' "${SCRIPT_DIR}/cloud-init/user-data" > "${ud}"
  mkdir -p "${SEED_DIR}"
  cp "${ud}" "${SEED_DIR}/user-data"
  cp "${SCRIPT_DIR}/cloud-init/meta-data" "${SEED_DIR}/meta-data"
}

start_seed_http() {
  local pid_file="${VM_DIR}/http.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    return 0
  fi
  log "serving nocloud seed at http://10.0.2.2:${HTTP_PORT}/ (QEMU user-net gateway)"
  python3 -m http.server "${HTTP_PORT}" --directory "${SEED_DIR}" \
    >/dev/null 2>"${VM_DIR}/http.log" &
  echo $! > "${pid_file}"
  sleep 1
  curl -fsS "http://127.0.0.1:${HTTP_PORT}/user-data" >/dev/null \
    || die "nocloud HTTP seed not reachable on port ${HTTP_PORT}"
}

stop_seed_http() {
  local pid_file="${VM_DIR}/http.pid"
  [[ -f "${pid_file}" ]] || return 0
  local pid
  pid="$(cat "${pid_file}")"
  if kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true
  fi
  rm -f "${pid_file}"
}

qemu_kvm_args() {
  if [[ -r /dev/kvm ]]; then
    printf '%s\n' -enable-kvm
  fi
}

start_serial_bootstrap_bg() {
  local pid_file="${VM_DIR}/serial_bootstrap.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    return 0
  fi
  log "starting background serial bootstrap (must connect before live boot proceeds)"
  : > "${VM_DIR}/serial_bootstrap.log"
  python3 "${SCRIPT_DIR}/serial_bootstrap.py" \
    --port "${SERIAL_PORT}" \
    --pubkey-file "${SSH_KEY}.pub" \
    --boot-wait 0 \
    >"${VM_DIR}/serial_bootstrap.log" 2>&1 &
  echo $! > "${pid_file}"
}

start_vm() {
  local pid_file="${VM_DIR}/qemu.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    log "QEMU already running (pid $(cat "${pid_file}"))"
    return 0
  fi
  # Desktop live does not apply cloud-init; nocloud-net is attempted first, then serial bootstrap.
  local append="boot=casper ip=dhcp toram=filesystem console=ttyS0,115200n8 ds=nocloud-net;s=http://10.0.2.2:${HTTP_PORT}/"
  log "starting QEMU Desktop casper live (SSH -> localhost:${SSH_PORT})"
  log "serial console: tcp localhost:${SERIAL_PORT} (wait=on — bootstrap connects first)"
  start_serial_bootstrap_bg
  # shellcheck disable=SC2046
  if ! qemu-system-x86_64 \
    $(qemu_kvm_args) \
    -m "${RAM_MB}" \
    -smp 2 \
    -cpu host \
    -kernel "${VMLINUZ}" \
    -initrd "${INITRD}" \
    -append "${append}" \
    -drive "file=${ISO_PATH},if=virtio,media=cdrom,readonly=on" \
    -netdev "user,id=net0,dns=10.0.2.3,hostfwd=tcp::${SSH_PORT}-:22" \
    -device virtio-net-pci,netdev=net0 \
    -display none \
    -serial "tcp:127.0.0.1:${SERIAL_PORT},server=on,wait=on" \
    -daemonize \
    -pidfile "${pid_file}"; then
    die "QEMU failed to start (is port ${SSH_PORT} or ${SERIAL_PORT} in use?)"
  fi
}

bootstrap_ssh_via_serial() {
  log "waiting for background serial bootstrap"
  local pid_file="${VM_DIR}/serial_bootstrap.pid"
  local i
  for ((i = 1; i <= 120; i++)); do
    if [[ -f "${pid_file}" ]]; then
      local pid
      pid="$(cat "${pid_file}")"
      if ! kill -0 "${pid}" 2>/dev/null; then
        wait "${pid}" 2>/dev/null || true
        if grep -q "serial bootstrap finished" "${VM_DIR}/serial_bootstrap.log" 2>/dev/null; then
          return 0
        fi
        log "serial bootstrap failed:"
        tail -30 "${VM_DIR}/serial_bootstrap.log" >&2 || true
        return 1
      fi
    fi
    sleep 5
  done
  log "serial bootstrap still running after 10 min"
  return 1
}

ssh_vm() {
  ssh -i "${SSH_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=5 -o BatchMode=yes \
    -p "${SSH_PORT}" "ubuntu@127.0.0.1" "$@"
}

wait_for_ssh() {
  local tries="${CEREMONY_VM_SSH_TRIES:-120}"
  local i
  local bootstrap_pid_file="${VM_DIR}/serial_bootstrap.pid"
  log "waiting for SSH on live session (up to ${tries}×10s)..."
  for ((i = 1; i <= tries; i++)); do
    if ssh_vm true 2>/dev/null; then
      log "SSH ready after ~$((i * 10))s"
      stop_seed_http
      return 0
    fi
    if [[ -f "${bootstrap_pid_file}" ]]; then
      local bpid
      bpid="$(cat "${bootstrap_pid_file}")"
      if ! kill -0 "${bpid}" 2>/dev/null; then
        if grep -q "serial bootstrap finished" "${VM_DIR}/serial_bootstrap.log" 2>/dev/null; then
          log "serial bootstrap finished; continuing SSH wait"
          rm -f "${bootstrap_pid_file}"
        fi
      fi
    fi
    if (( i % 6 == 0 )); then
      log "still waiting... ($((i * 10))s)"
      if [[ -f "${VM_DIR}/serial_bootstrap.log" ]]; then
        tail -2 "${VM_DIR}/serial_bootstrap.log" | sed 's/^/[serial] /' >&2 || true
      fi
    fi
    sleep 10
  done
  die "SSH not reachable — see ${VM_DIR}/serial_bootstrap.log"
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
  log "copying ceremony tree to live session (excluding vm/cache ISO)"
  ssh_vm "sudo mkdir -p /opt/realms-ceremony && sudo chown ubuntu:ubuntu /opt/realms-ceremony"
  tar -C "${CEREMONY_DIR}" \
    --exclude='./vm/cache' \
    --exclude='./vm/cache/*' \
    -czf - . | ssh_vm "tar -xzf - -C /opt/realms-ceremony"
  ssh_vm "chmod +x /opt/realms-ceremony/realms-key-ceremony.sh /opt/realms-ceremony/vm/guest-run-test.sh"
  log "running guest test"
  ssh_vm "bash /opt/realms-ceremony/vm/guest-run-test.sh /opt/realms-ceremony" || die "guest ceremony test failed"
}

cleanup() {
  if [[ "${KEEP_VM}" == "1" ]]; then
    log "keeping VM running (--keep-vm)"
    log "SSH: ssh -i ${SSH_KEY} -p ${SSH_PORT} ubuntu@127.0.0.1"
    return 0
  fi
  local sb_pid="${VM_DIR}/serial_bootstrap.pid"
  if [[ -f "${sb_pid}" ]]; then
    kill "$(cat "${sb_pid}")" 2>/dev/null || true
    rm -f "${sb_pid}"
  fi
  stop_seed_http
  stop_vm
}

trap cleanup EXIT

main() {
  download_iso
  extract_casper
  build_nocloud_seed
  start_seed_http
  start_vm
  wait_for_ssh
  run_guest_test
  log "PASS: Ubuntu 22.04 Desktop live ISO VM test"
}

main
