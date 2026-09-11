#!/usr/bin/env bash
# After flashing the ceremony ISO, create the data partition and restore preserved folders.
# Usage: sudo ./restore-usb-data-partition.sh --device /dev/sdX --preserve-from /tmp/realms-usb-bkp-preserve
set -euo pipefail

DEVICE=""
PRESERVE_FROM=""
DATA_LABEL="REALMS_DATA"

log() { printf '[restore-usb] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE="${2:-}"; shift 2 ;;
    --preserve-from) PRESERVE_FROM="${2:-}"; shift 2 ;;
    --data-label) DATA_LABEL="${2:-}"; shift 2 ;;
    -h|--help)
      echo "Usage: sudo $0 --device /dev/sdX --preserve-from DIR"
      exit 0
      ;;
    *) die "unknown option: $1" ;;
  esac
done

[[ -n "${DEVICE}" && -n "${PRESERVE_FROM}" ]] || die "need --device and --preserve-from"
[[ "${EUID}" -eq 0 ]] || die "run as root (sudo)"
[[ -d "${PRESERVE_FROM}" ]] || die "missing ${PRESERVE_FROM}"
command -v sgdisk >/dev/null || die "install gdisk (sgdisk)"
command -v parted >/dev/null || die "install parted"
command -v mkfs.ntfs >/dev/null || die "install ntfs-3g"

log "expanding GPT to use full disk"
sgdisk -e "${DEVICE}" >/dev/null

start_mb="$(parted -ms "${DEVICE}" unit MiB print free | awk -F: '$4=="free" && $3+0 > 1024 {gsub(/MiB/,"",$2); print int($2); exit}')"
[[ -n "${start_mb}" ]] || die "no free space >= 1 GiB on ${DEVICE}"

if lsblk -ln -o FSTYPE "${DEVICE}" | grep -q '^ntfs$'; then
  log "NTFS data partition already present — mounting and syncing"
else
  log "creating NTFS data partition from ${start_mb}MiB"
  parted -s "${DEVICE}" mkpart primary ntfs "${start_mb}MiB" 100%
  partprobe "${DEVICE}" 2>/dev/null || true
  sleep 2
  data_dev="/dev/$(lsblk -ln -o NAME,FSTYPE "${DEVICE}" | awk '$2=="" {last=$1} END {print last}')"
  [[ -b "${data_dev}" ]] || data_dev="/dev/$(lsblk -ln -o NAME,FSTYPE "${DEVICE}" | awk '$2=="ntfs" {print $1; exit}')"
  [[ -b "${data_dev}" ]] || die "could not find new data partition"
  log "formatting ${data_dev} as ${DATA_LABEL}"
  mkfs.ntfs -f -L "${DATA_LABEL}" "${data_dev}"
fi

data_dev="/dev/$(lsblk -ln -o NAME,FSTYPE "${DEVICE}" | awk '$2=="ntfs" {print $1; exit}')"
[[ -b "${data_dev}" ]] || die "no NTFS partition on ${DEVICE}"

mount_dir="$(mktemp -d)"
mount "${data_dev}" "${mount_dir}"
log "restoring from ${PRESERVE_FROM}"
rsync -a "${PRESERVE_FROM}/" "${mount_dir}/"
sync
umount "${mount_dir}"
rmdir "${mount_dir}"
log "done"
lsblk -o NAME,SIZE,FSTYPE,LABEL "${DEVICE}"
