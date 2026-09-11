#!/usr/bin/env bash
# Wipe a USB stick, flash the ceremony live ISO, then create the data volume.
#
# Layout after a successful write:
#   CEREMONY OS   ISO9660  (isohybrid live image — read-only by design)
#   ESP           FAT32    (UEFI boot, created by the ISO)
#   CEREMONY DATA exFAT    (writable verification bundle; Linux / Windows / macOS)
set -euo pipefail

# shellcheck source=usb_labels.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/usb_labels.sh"

CEREMONY_DATA_FSTYPE="${CEREMONY_DATA_FSTYPE:-exfat}"

_usb_log() {
  if declare -F log >/dev/null; then
    log "$@"
  else
    printf '[usb-disk] %s\n' "$*" >&2
  fi
}

_usb_die() {
  if declare -F die >/dev/null; then
    die "$@"
  else
    printf '[usb-disk] ERROR: %s\n' "$*" >&2
    exit 1
  fi
}

usb_require_write_tools() {
  command -v wipefs >/dev/null || _usb_die "install util-linux (wipefs)"
  command -v sgdisk >/dev/null || _usb_die "install gdisk (sgdisk)"
  command -v parted >/dev/null || _usb_die "install parted"
  command -v partprobe >/dev/null || _usb_die "install parted (partprobe)"
  command -v mkfs.exfat >/dev/null || _usb_die "install exfatprogs (mkfs.exfat)"
}

usb_unmount_device() {
  local dev="$1" p mount
  local parts=()
  mapfile -t parts < <(lsblk -ln -o NAME "${dev}" | tail -n +2)
  for p in "${parts[@]}"; do
    mount="$(findmnt -n -o TARGET "/dev/${p}" 2>/dev/null || true)"
    if [[ -n "${mount}" ]]; then
      _usb_log "unmounting /dev/${p} (${mount})"
      umount -l "/dev/${p}" 2>/dev/null || umount "/dev/${p}" \
        || _usb_die "could not unmount /dev/${p} — close Files windows on that volume"
    fi
  done
}

# Destroy every partition table and filesystem signature on the stick,
# including a leftover GPT backup at the end of a previously partitioned disk.
usb_wipe_device() {
  local dev="$1" p
  usb_unmount_device "${dev}"
  _usb_log "wiping partition tables and filesystem signatures on ${dev}"
  local parts=()
  mapfile -t parts < <(lsblk -ln -o NAME "${dev}" | tail -n +2)
  for p in "${parts[@]}"; do
    wipefs -a "/dev/${p}" >/dev/null 2>&1 || true
  done
  wipefs -a "${dev}" >/dev/null 2>&1 || true
  sgdisk --zap-all "${dev}" >/dev/null 2>&1 || true
  # Clear the first and last megabytes so no stale MBR/GPT survives the ISO dd.
  local bytes seek_mib
  bytes="$(blockdev --getsize64 "${dev}")"
  seek_mib="$((bytes / 1048576 - 4))"
  dd if=/dev/zero of="${dev}" bs=1M count=4 status=none conv=fsync 2>/dev/null || true
  if [[ "${seek_mib}" -gt 4 ]]; then
    dd if=/dev/zero of="${dev}" bs=1M count=4 seek="${seek_mib}" status=none conv=fsync 2>/dev/null || true
  fi
  partprobe "${dev}" 2>/dev/null || true
}

usb_data_partition_dev() {
  local dev="$1"
  lsblk -lnp -o NAME,FSTYPE,TYPE "${dev}" \
    | awk '$3=="part" && ($2=="exfat" || $2=="ntfs") {print $1; exit}'
}

# After the isohybrid ISO is on the disk, claim the leftover space as CEREMONY DATA.
usb_create_data_partition() {
  local dev="$1"
  local label="${2:-${CEREMONY_DATA_LABEL}}"
  local existing start_mb data_dev

  existing="$(usb_data_partition_dev "${dev}" || true)"
  if [[ -n "${existing}" ]]; then
    _usb_log "data partition already present: ${existing}"
    return 0
  fi

  _usb_log "expanding GPT to the full disk"
  sgdisk -e "${dev}" >/dev/null
  partprobe "${dev}" 2>/dev/null || true
  sleep 1

  start_mb="$(parted -ms "${dev}" unit MiB print free \
    | awk -F: '$4=="free" && $3+0 > 1024 {gsub(/MiB/,"",$2); print int($2); exit}')"
  [[ -n "${start_mb}" ]] || _usb_die "no free space ≥ 1 GiB on ${dev} after the live ISO"

  _usb_log "creating ${CEREMONY_DATA_FSTYPE} '${label}' from ${start_mb}MiB to end of disk"
  # Do not pass an fs-type to parted — "exfat" is not a parted fs name; mkfs.exfat formats it.
  parted -s "${dev}" mkpart primary "${start_mb}MiB" 100%
  partprobe "${dev}" 2>/dev/null || true
  udevadm settle 2>/dev/null || true
  sleep 2

  data_dev="$(lsblk -lnp -o NAME,FSTYPE,TYPE "${dev}" \
    | awk '$3=="part" && $2=="" {print $1}' | tail -1)"
  [[ -b "${data_dev}" ]] || data_dev="$(usb_data_partition_dev "${dev}" || true)"
  [[ -b "${data_dev}" ]] || _usb_die "could not find the new data partition on ${dev}"

  mkfs.exfat -n "${label}" "${data_dev}"
  _usb_log "formatted ${data_dev} as exFAT '${label}'"
}

usb_flash_iso_and_partition() {
  local iso="$1"
  local dev="$2"
  [[ -f "${iso}" ]] || _usb_die "missing ISO: ${iso}"
  [[ -b "${dev}" ]] || _usb_die "not a block device: ${dev}"
  usb_require_write_tools
  usb_wipe_device "${dev}"
  _usb_log "writing ${iso} → ${dev}"
  dd if="${iso}" of="${dev}" bs=4M status=progress conv=fsync
  sync
  partprobe "${dev}" 2>/dev/null || true
  sleep 2
  usb_create_data_partition "${dev}" "${CEREMONY_DATA_LABEL}"
  _usb_log "USB layout:"
  lsblk -o NAME,SIZE,FSTYPE,LABEL "${dev}" || true
}
