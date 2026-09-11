#!/usr/bin/env bash
# Create (or reuse) the CEREMONY DATA volume and optionally restore folders onto it.
# Usage:
#   sudo ./restore-usb-data-partition.sh --device /dev/sdX
#   sudo ./restore-usb-data-partition.sh --device /dev/sdX --preserve-from DIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/usb_labels.sh
source "${SCRIPT_DIR}/lib/usb_labels.sh"
# shellcheck source=lib/usb_disk.sh
source "${SCRIPT_DIR}/lib/usb_disk.sh"

DEVICE=""
PRESERVE_FROM=""
DATA_LABEL="${CEREMONY_DATA_LABEL}"

log() { printf '[restore-usb] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE="${2:-}"; shift 2 ;;
    --preserve-from) PRESERVE_FROM="${2:-}"; shift 2 ;;
    --data-label) DATA_LABEL="${2:-}"; shift 2 ;;
    -h|--help)
      echo "Usage: sudo $0 --device /dev/sdX [--preserve-from DIR]"
      exit 0
      ;;
    *) die "unknown option: $1" ;;
  esac
done

[[ -n "${DEVICE}" ]] || die "need --device"
[[ "${EUID}" -eq 0 ]] || die "run as root (sudo)"
[[ -z "${PRESERVE_FROM}" || -d "${PRESERVE_FROM}" ]] || die "missing ${PRESERVE_FROM}"

usb_require_write_tools
usb_unmount_device "${DEVICE}"
usb_create_data_partition "${DEVICE}" "${DATA_LABEL}"

if [[ -n "${PRESERVE_FROM}" ]]; then
  data_dev="$(usb_data_partition_dev "${DEVICE}")"
  [[ -b "${data_dev}" ]] || die "no data partition on ${DEVICE}"
  mount_dir="$(mktemp -d)"
  mount "${data_dev}" "${mount_dir}" \
    || mount -t exfat "${data_dev}" "${mount_dir}" \
    || mount -t ntfs-3g "${data_dev}" "${mount_dir}" \
    || die "could not mount ${data_dev}"
  log "restoring from ${PRESERVE_FROM}"
  rsync -a "${PRESERVE_FROM}/" "${mount_dir}/"
  sync
  umount "${mount_dir}"
  rmdir "${mount_dir}"
fi

log "done"
lsblk -o NAME,SIZE,FSTYPE,LABEL "${DEVICE}"
