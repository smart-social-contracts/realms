#!/usr/bin/env bash
# Flash the Realms ceremony live ISO to a USB stick and restore a preserved data partition.
#
# Usage (run as root):
#   sudo ./flash-ceremony-usb-preserve-data.sh --device /dev/sda \
#     --preserve-from /tmp/realms-usb-bkp-preserve
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="${SCRIPT_DIR}/vm/cache/realms-ceremony-live.iso"
DEVICE=""
PRESERVE_FROM=""
DATA_LABEL="REALMS_DATA"

log() { printf '[flash-usb] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Usage: sudo $0 --device /dev/sdX [--preserve-from DIR] [--iso PATH]

  --device DEV         Whole USB disk (e.g. /dev/sda)
  --preserve-from DIR  Copy top-level folders from DIR onto a new NTFS data partition
  --iso PATH           Ceremony ISO (default: vm/cache/realms-ceremony-live.iso)
  --data-label NAME    NTFS volume label (default: REALMS_DATA)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE="${2:-}"; shift 2 ;;
    --preserve-from) PRESERVE_FROM="${2:-}"; shift 2 ;;
    --iso) ISO="${2:-}"; shift 2 ;;
    --data-label) DATA_LABEL="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

[[ -n "${DEVICE}" ]] || { usage; die "missing --device"; }
[[ "${EUID}" -eq 0 ]] || die "run as root (sudo)"
[[ -b "${DEVICE}" ]] || die "not a block device: ${DEVICE}"
[[ "${DEVICE}" =~ ^/dev/(sd[a-z]+|nvme[0-9]+n[0-9]+)$ ]] || die "pass whole disk, not a partition"
[[ -f "${ISO}" ]] || die "missing ISO: ${ISO} (run: ./prepare-ceremony-live-usb.sh --full-embed --iso-only ${ISO})"

root_disk="$(findmnt -n -o SOURCE / | sed -E 's/p?[0-9]+$//; s/[0-9]+$//')"
[[ "${DEVICE}" != "${root_disk}" ]] || die "refusing system disk ${DEVICE}"

for p in "${DEVICE}"*; do
  [[ -b "${p}" ]] || continue
  mountpoint="$(findmnt -n -o TARGET "${p}" 2>/dev/null || true)"
  if [[ -n "${mountpoint}" ]]; then
    log "unmounting ${p} (${mountpoint})"
    umount -l "${p}" 2>/dev/null || umount "${p}"
  fi
done

log "writing ceremony ISO to ${DEVICE} (~5 min)..."
dd if="${ISO}" of="${DEVICE}" bs=4M status=progress conv=fsync
sync
partprobe "${DEVICE}" 2>/dev/null || true
sleep 2

log "partition layout after flash:"
lsblk -o NAME,SIZE,FSTYPE,LABEL "${DEVICE}" || true

if [[ -n "${PRESERVE_FROM}" ]]; then
  "${SCRIPT_DIR}/restore-usb-data-partition.sh" \
    --device "${DEVICE}" \
    --preserve-from "${PRESERVE_FROM}" \
    --data-label "${DATA_LABEL}"
fi

log "done — boot this USB → Try Ubuntu"
log "  cd \"\$(/bin/bash /cdrom/realms-ceremony/usb/find-ceremony-dir.sh)\""
log "  or read /cdrom/CEREMONY-START-HERE.txt"
lsblk -o NAME,SIZE,FSTYPE,LABEL "${DEVICE}"
