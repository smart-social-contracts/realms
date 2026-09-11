#!/usr/bin/env bash
# Rename the two ceremony USB volumes in place (no ISO remaster).
#
#   sudo ./usb/relabel-ceremony-usb.sh --device /dev/sda
#
# Sets ISO9660 + Joliet volume ID to "CEREMONY OS" and the data
# partition (exFAT or NTFS) to "CEREMONY DATA". Unmounts those volumes first.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/usb_labels.sh
source "${SCRIPT_DIR}/../lib/usb_labels.sh"

DEVICE=""
OS_LABEL="${CEREMONY_OS_LABEL}"
DATA_LABEL="${CEREMONY_DATA_LABEL}"

log() { printf '[relabel-usb] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat <<EOF
Usage: sudo $0 --device /dev/sdX

  --device DEV     Whole USB disk (e.g. /dev/sda)
  --os-label NAME  ISO9660 / Joliet volume ID (default: ${OS_LABEL})
  --data-label NAME  Data volume label (default: ${DATA_LABEL})
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE="${2:-}"; shift 2 ;;
    --os-label) OS_LABEL="${2:-}"; shift 2 ;;
    --data-label) DATA_LABEL="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

[[ -n "${DEVICE}" ]] || die "need --device /dev/sdX"
[[ "${EUID}" -eq 0 ]] || die "run as root (sudo)"
[[ -b "${DEVICE}" ]] || die "not a block device: ${DEVICE}"
[[ "${#OS_LABEL}" -le 32 ]] || die "ISO volume id must be ≤ 32 characters"
[[ "${#DATA_LABEL}" -le 32 ]] || die "data volume label must be ≤ 32 characters"

unmount_device_mounts() {
  local dev="$1" mp
  while mp="$(findmnt -n -o TARGET --source "${dev}" 2>/dev/null | head -1)"; do
    [[ -n "${mp}" ]] || break
    log "unmounting ${dev} from ${mp}"
    umount "${mp}" || die "could not unmount ${mp} — close Files windows on that volume"
  done
}

for part in "${DEVICE}" "${DEVICE}"[0-9]* "${DEVICE}"p[0-9]*; do
  [[ -b "${part}" ]] || continue
  unmount_device_mounts "${part}"
done

python3 - "${DEVICE}" "${OS_LABEL}" <<'PY'
import sys

dev, label = sys.argv[1], sys.argv[2]
sector = 2048
found = 0
with open(dev, "r+b") as f:
    for i in range(16, 32):
        f.seek(i * sector)
        desc = f.read(6)
        if desc[1:6] != b"CD001":
            continue
        dtype = desc[0]
        if dtype == 1:
            raw = label.encode("ascii", "replace")[:32].ljust(32, b" ")
            f.seek(i * sector + 40)
            f.write(raw)
            found += 1
        elif dtype == 2:
            raw = label.encode("utf-16-be")[:64].ljust(64, b"\x00")
            f.seek(i * sector + 40)
            f.write(raw)
            found += 1
if found < 1:
    sys.exit("no ISO9660 volume descriptor on " + dev)
print(f"patched {found} ISO volume descriptor(s) → {label!r}")
PY

data_dev=""
fstype=""
for part in "${DEVICE}"[0-9]* "${DEVICE}"p[0-9]*; do
  [[ -b "${part}" ]] || continue
  fstype="$(lsblk -ln -o FSTYPE "${part}" 2>/dev/null || true)"
  if [[ "${fstype}" == "exfat" || "${fstype}" == "ntfs" ]]; then
    data_dev="${part}"
    break
  fi
done
[[ -n "${data_dev}" ]] || die "no exFAT/NTFS data partition on ${DEVICE}"

log "setting ${fstype} label on ${data_dev} → ${DATA_LABEL}"
if [[ "${fstype}" == "exfat" ]]; then
  command -v exfatlabel >/dev/null || die "install exfatprogs (exfatlabel)"
  exfatlabel "${data_dev}" "${DATA_LABEL}"
else
  command -v ntfslabel >/dev/null || die "install ntfs-3g (ntfslabel)"
  ntfslabel "${data_dev}" "${DATA_LABEL}"
fi

udevadm settle 2>/dev/null || true
partprobe "${DEVICE}" 2>/dev/null || true
sleep 1
lsblk -o NAME,SIZE,FSTYPE,LABEL "${DEVICE}"
log "done — replug or: udisksctl mount -b ${data_dev}"
