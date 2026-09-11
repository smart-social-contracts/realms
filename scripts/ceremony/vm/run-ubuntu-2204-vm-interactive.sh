#!/usr/bin/env bash
# Boot the remastered Realms ceremony live ISO in QEMU with a GUI — same flow as the USB stick.
# The ISO carries only bootstrap scripts; the live ceremony tree is shared from this repo via virtio-9p.
#
# Usage:
#   ./vm/run-ubuntu-2204-vm-interactive.sh              # auto USB passthrough if YubiKey plugged
#   ./vm/run-ubuntu-2204-vm-interactive.sh --no-usb   # simulate only (no hardware)
#   ./vm/run-ubuntu-2204-vm-interactive.sh --bg       # background VM (for ./vm/guest-exec.sh)
#   ./vm/run-ubuntu-2204-vm-interactive.sh --ssh-only # headless + SSH on 2222 (copy scripts in)
#
# Tips:
#   - Plug the YubiKey BEFORE starting the VM.
#   - If passthrough fails, on the host run: sudo systemctl stop pcscd
#   - In the VM: Try Ubuntu → double-click "Realms Key Ceremony" (or run launch-ceremony-terminal.sh)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CEREMONY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VM_DIR="${SCRIPT_DIR}/cache"
ISO_PATH="${VM_DIR}/realms-ceremony-live.iso"
BASE_ISO="${VM_DIR}/ubuntu-22.04.5-desktop-amd64.iso"
RAM_MB="${CEREMONY_VM_RAM_MB:-8192}"
CPUS="${CEREMONY_VM_CPUS:-4}"
SSH_PORT="${CEREMONY_VM_SSH_PORT:-2222}"
SERIAL_PORT="${CEREMONY_VM_SERIAL_PORT:-4445}"
DISPLAY_MODE="${CEREMONY_VM_DISPLAY:-gtk}"
VMLINUZ="${VM_DIR}/vmlinuz"
INITRD="${VM_DIR}/initrd"
SSH_KEY="${VM_DIR}/guest_exec_id_ed25519"
QEMU_PID_FILE="${VM_DIR}/interactive-qemu.pid"
USB_PASSTHROUGH=1
SSH_ONLY=0
REFRESH_ISO=0
BG_MODE=0
USE_DIRECT_KERNEL="${CEREMONY_VM_DIRECT_KERNEL:-1}"

log() { printf '[vm-interactive] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

bootstrap_sources_newer_than_iso() {
  [[ -f "${ISO_PATH}" ]] || return 0
  local iso_ts src_ts
  iso_ts="$(stat -c %Y "${ISO_PATH}")"
  src_ts="$(
    find "${CEREMONY_DIR}/usb" -type f -printf '%T@\n' 2>/dev/null \
      | sort -n | tail -1 | cut -d. -f1
  )"
  [[ -n "${src_ts}" && "${src_ts}" -gt "${iso_ts}" ]]
}

ensure_bootstrap_iso() {
  if [[ "${REFRESH_ISO}" == "1" ]] || [[ ! -f "${ISO_PATH}" ]] || bootstrap_sources_newer_than_iso; then
    log "building thin bootstrap ISO at ${ISO_PATH}"
    log "  steps: extract squashfs → patch desktop icon → repack → xorriso (~5–8 min total)"
    log "  progress + 15s heartbeats stream below — not stuck if you see elapsed time increasing"
    "${CEREMONY_DIR}/prepare-ceremony-live-usb.sh" --bootstrap-only --iso-only "${ISO_PATH}" --verify
    return 0
  fi
  log "using existing bootstrap ISO (edit scripts/ceremony on host — no ISO rebuild needed)"
}

extract_casper() {
  if [[ -f "${VMLINUZ}" && -f "${INITRD}" ]]; then
    return 0
  fi
  [[ -f "${BASE_ISO}" ]] || die "missing ${BASE_ISO} (needed for serial console boot)"
  command -v xorriso >/dev/null || die "install xorriso to extract casper kernel/initrd"
  log "extracting casper vmlinuz + initrd from ${BASE_ISO}"
  xorriso -osirrox on -indev "${BASE_ISO}" -extract /casper/vmlinuz "${VMLINUZ}"
  xorriso -osirrox on -indev "${BASE_ISO}" -extract /casper/initrd "${INITRD}"
}

ensure_ssh_key() {
  if [[ ! -f "${SSH_KEY}" ]]; then
    ssh-keygen -t ed25519 -N "" -f "${SSH_KEY}" -q
  fi
}

start_serial_bootstrap_bg() {
  local pid_file="${VM_DIR}/serial_bootstrap.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    log "serial SSH bootstrap already running (pid $(cat "${pid_file}"))"
    return 0
  fi
  ensure_ssh_key
  log "starting serial SSH bootstrap (connects before QEMU boots; SSH -> localhost:${SSH_PORT})"
  : > "${VM_DIR}/serial_bootstrap.log"
  python3 "${SCRIPT_DIR}/serial_bootstrap.py" \
    --port "${SERIAL_PORT}" \
    --pubkey-file "${SSH_KEY}.pub" \
    --boot-wait 0 \
    >"${VM_DIR}/serial_bootstrap.log" 2>&1 &
  echo $! > "${pid_file}"
}

start_push_server() {
  if [[ -f "${SCRIPT_DIR}/cache/ceremony-push-http.pid" ]] \
    && kill -0 "$(cat "${SCRIPT_DIR}/cache/ceremony-push-http.pid")" 2>/dev/null; then
    log "HTTP push server already running (fallback for attach-ceremony-from-host.sh)"
    return 0
  fi
  "${SCRIPT_DIR}/push-ceremony-scripts.sh" --daemon
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-usb) USB_PASSTHROUGH=0 ;;
    --bg) BG_MODE=1 ;;
    --ssh-only) SSH_ONLY=1; DISPLAY_MODE=none ;;
    --refresh-iso) REFRESH_ISO=1 ;;
    --iso) ISO_PATH="${2:-}"; shift 2; continue ;;
    --ram) RAM_MB="${2:-}"; shift 2; continue ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

command -v qemu-system-x86_64 >/dev/null || die "install qemu-system-x86_64"

if [[ ! -f "${BASE_ISO}" && ! -f "${ISO_PATH}" ]]; then
  die "missing base Ubuntu ISO — run: ./prepare-ceremony-live-usb.sh --bootstrap-only --iso-only ${ISO_PATH}"
fi
ensure_bootstrap_iso
if [[ "${USE_DIRECT_KERNEL}" == "1" ]]; then
  extract_casper
fi
start_push_server

usb_args=()
if [[ "${USB_PASSTHROUGH}" == "1" ]]; then
  mapfile -t yubi_lines < <(lsusb 2>/dev/null | grep -i '1050:' || true)
  if [[ ${#yubi_lines[@]} -eq 0 ]]; then
    log "WARNING: no YubiKey on host (vendor 1050) — VM will start without USB passthrough"
    log "         plug the key, stop this VM, and re-run; or use CEREMONY_SIMULATE=1 inside the guest"
  else
    local_line=""
    for line in "${yubi_lines[@]}"; do
      if [[ "${line}" == *"0407"* ]]; then
        local_line="${line}"
        break
      fi
    done
    [[ -n "${local_line}" ]] || local_line="${yubi_lines[0]}"
    vidpid="$(echo "${local_line}" | awk '{print $6}')"
    vid="${vidpid%%:*}"
    pid="${vidpid##*:}"
    log "USB passthrough: ${vidpid} (by vendor/product — survives re-enumeration)"
    log "if QEMU errors on usb-host, run on host: sudo systemctl stop pcscd"
    usb_args=(
      -device qemu-xhci,id=xhci
      -device "usb-host,bus=xhci.0,vendorid=0x${vid},productid=0x${pid},id=yubikey-ccid"
    )
  fi
fi

kvm_args=()
cpu_args=(-cpu max)
if [[ -r /dev/kvm ]] && [[ -w /dev/kvm ]]; then
  kvm_args=(-enable-kvm)
  cpu_args=(-cpu host)
else
  log "KVM not available — using TCG (slower; expect 5–10 min to boot)"
fi

display_args=(-display "${DISPLAY_MODE}")
[[ "${SSH_ONLY}" == "1" ]] && display_args=(-display none)

net_args=(
  -netdev "user,id=net0,dns=10.0.2.3,hostfwd=tcp::${SSH_PORT}-:22"
  -device virtio-net-pci,netdev=net0
)

virtfs_args=(
  -virtfs "local,path=${CEREMONY_DIR},mount_tag=realms_ceremony,security_model=none,id=realms_ceremony"
)

boot_args=()
serial_args=()
if [[ "${USE_DIRECT_KERNEL}" == "1" ]]; then
  local_append="boot=casper ip=dhcp toram=filesystem console=tty0 console=ttyS0,115200n8"
  boot_args=(
    -kernel "${VMLINUZ}"
    -initrd "${INITRD}"
    -append "${local_append}"
    -drive "file=${ISO_PATH},if=virtio,media=cdrom,readonly=on"
  )
  serial_args=(-serial "tcp:127.0.0.1:${SERIAL_PORT},server=on,wait=on")
  start_serial_bootstrap_bg
else
  boot_args=(-cdrom "${ISO_PATH}" -boot d)
  serial_args=()
  log "WARNING: direct-kernel boot disabled — host ./vm/guest-exec.sh will not work"
fi

log "starting QEMU with ${ISO_PATH}"
log "  RAM=${RAM_MB}MB CPUs=${CPUS} display=${DISPLAY_MODE}"
log "  In VM: Try Ubuntu → Realms Key Ceremony desktop icon (auto-attaches host scripts)"
log "  Live tree: ${CEREMONY_DIR} → /opt/realms-ceremony (virtio-9p)"
log "  Host guest shell: ./vm/guest-exec.sh 'command'  (or --attach / --option-a)"
if [[ "${BG_MODE}" == "1" ]]; then
  log "  Stop VM: ./vm/stop-interactive-vm.sh"
else
  log "  Stop VM: close the QEMU window or Ctrl+C here"
fi

qemu_cmd=(
  qemu-system-x86_64
  "${kvm_args[@]}"
  -m "${RAM_MB}"
  -smp "${CPUS}"
  "${cpu_args[@]}"
  "${boot_args[@]}"
  "${display_args[@]}"
  "${net_args[@]}"
  "${virtfs_args[@]}"
  "${usb_args[@]}"
  "${serial_args[@]}"
  -name "realms-ceremony-live"
)

if [[ "${BG_MODE}" == "1" ]]; then
  if [[ -f "${QEMU_PID_FILE}" ]] && kill -0 "$(cat "${QEMU_PID_FILE}")" 2>/dev/null; then
    log "QEMU already running (pid $(cat "${QEMU_PID_FILE}"))"
    exit 0
  fi
  if ! "${qemu_cmd[@]}" -daemonize -pidfile "${QEMU_PID_FILE}"; then
    die "QEMU failed to start (is port ${SSH_PORT} or ${SERIAL_PORT} in use?)"
  fi
  log "QEMU running in background (pid $(cat "${QEMU_PID_FILE}"))"
  log "SSH should be ready in ~3–5 min; then: ./vm/guest-exec.sh --attach"
  exit 0
fi

exec "${qemu_cmd[@]}"
