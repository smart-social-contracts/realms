#!/usr/bin/env bash
# Build a bootable Ubuntu 22.04 Desktop live USB with the Realms key ceremony pre-staged.
#
# Embeds scripts/ceremony at /realms-ceremony on the ISO so the ceremony laptop needs
# only this one USB (plus a second stick later for manifest export).
#
# Run on a Linux prep machine (Ubuntu recommended). Requires root to write the USB.
#
# Usage:
#   sudo ./prepare-ceremony-live-usb.sh --device /dev/sdX
#   ./prepare-ceremony-live-usb.sh --iso-only ./realms-ceremony-live.iso
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CEREMONY_DIR="${SCRIPT_DIR}"
CACHE_DIR="${CEREMONY_DIR}/vm/cache"
ISO_URL="https://releases.ubuntu.com/22.04/ubuntu-22.04.5-desktop-amd64.iso"
ISO_SHA256="bfd1cee02bc4f35db939e69b934ba49a39a378797ce9aee20f6e3e3e728fefbf"
ISO_PATH="${CACHE_DIR}/ubuntu-22.04.5-desktop-amd64.iso"
MIN_USB_BYTES=$((8 * 1024 * 1024 * 1024))

DEVICE=""
ISO_ONLY=""
SKIP_CONFIRM=0
DRY_RUN=0
VERIFY_ISO=0
EMBED_MODE="bootstrap"
WITH_PACKAGES=1

log() { printf '[prepare-usb] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

log_step() {
  printf '[prepare-usb] >> step %s: %s\n' "$1" "$2" >&2
}

# Run a long command with a 15s heartbeat so silence never looks like a hang.
run_with_progress() {
  local label="$1"
  shift
  local start hb rc
  start="$(date +%s)"
  log "starting: ${label}"
  (
    while sleep 15; do
      log "  ... still running: ${label} ($(($(date +%s) - start))s elapsed)"
    done
  ) &
  hb=$!
  set +e
  "$@"
  rc=$?
  set -e
  kill "${hb}" 2>/dev/null || true
  wait "${hb}" 2>/dev/null || true
  if [[ "${rc}" -eq 0 ]]; then
    log "finished: ${label} ($(($(date +%s) - start))s)"
  else
    die "${label} failed after $(($(date +%s) - start))s (exit ${rc})"
  fi
}

usage() {
  sed -n '2,22p' "$0"
  cat <<'EOF'

Options:
  --device DEV       Whole-disk block device to overwrite (e.g. /dev/sdb, not /dev/sdb1)
  --iso-only PATH    Build remastered ISO at PATH; do not write a USB stick
  --bootstrap-only   Embed only USB bootstrap scripts (default; VM / dev — live tree from host)
  --full-embed       Embed the full ceremony tree (production airgapped USB)
  --with-packages    Bake ykman/ykcs11/dfx/openssh into the live squashfs (default)
  --skip-packages    Skip apt in squashfs (faster ISO rebuild; guest must run online-setup)
  --cache-dir DIR    ISO download cache (default: scripts/ceremony/vm/cache)
  --iso PATH         Use this base Ubuntu ISO instead of downloading
  --yes              Skip interactive confirmation before writing
  --dry-run          Show actions only (no download/remaster/write)
  --verify           After remaster, list /realms-ceremony on the ISO
  -h, --help         Show this help

Examples:
  sudo ./prepare-ceremony-live-usb.sh --device /dev/sdb --yes
  ./prepare-ceremony-live-usb.sh --iso-only ~/realms-ceremony-live.iso --verify

Safety:
  - Confirms the target device is removable USB and not your system disk.
  - Unmounts all partitions on the device before writing.
  - The USB stick is fully overwritten (~5 GB ISO).
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1 (install on Ubuntu: apt install $2)"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device) DEVICE="${2:-}"; shift 2 ;;
    --iso-only) ISO_ONLY="${2:-}"; shift 2 ;;
    --bootstrap-only) EMBED_MODE="bootstrap"; shift ;;
    --full-embed) EMBED_MODE="full"; shift ;;
    --with-packages) WITH_PACKAGES=1; shift ;;
    --skip-packages) WITH_PACKAGES=0; shift ;;
    --cache-dir) CACHE_DIR="${2:-}"; ISO_PATH="${CACHE_DIR}/ubuntu-22.04.5-desktop-amd64.iso"; shift 2 ;;
    --iso) ISO_PATH="${2:-}"; shift 2 ;;
    --yes) SKIP_CONFIRM=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --verify) VERIFY_ISO=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done

if [[ -z "${DEVICE}" && -z "${ISO_ONLY}" ]]; then
  usage
  die "specify --device /dev/sdX or --iso-only /path/to/output.iso"
fi

require_cmd curl curl
require_cmd xorriso xorriso
require_cmd rsync rsync
require_cmd lsblk util-linux
require_cmd blockdev util-linux
require_cmd findmnt util-linux
require_cmd sha256sum coreutils
require_cmd unsquashfs squashfs-tools
require_cmd mksquashfs squashfs-tools

download_iso() {
  if [[ -f "${ISO_PATH}" ]]; then
    log "base ISO present: ${ISO_PATH}"
    if [[ -n "${ISO_SHA256}" ]]; then
      local actual
      actual="$(sha256sum "${ISO_PATH}" | awk '{print $1}')"
      if [[ "${actual}" != "${ISO_SHA256}" ]]; then
        die "ISO SHA256 mismatch (expected ${ISO_SHA256}, got ${actual}) — delete ${ISO_PATH} and retry"
      fi
      log "ISO SHA256 OK"
    fi
    return 0
  fi
  mkdir -p "${CACHE_DIR}"
  log "downloading Ubuntu 22.04.5 Desktop ISO (~4.5 GB) to ${ISO_PATH}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] would curl -fL ${ISO_URL}"
    return 0
  fi
  curl -fL --progress-bar -o "${ISO_PATH}.partial" "${ISO_URL}"
  mv "${ISO_PATH}.partial" "${ISO_PATH}"
  if [[ -n "${ISO_SHA256}" ]]; then
    local actual
    actual="$(sha256sum "${ISO_PATH}" | awk '{print $1}')"
    [[ "${actual}" == "${ISO_SHA256}" ]] || die "downloaded ISO SHA256 mismatch"
  fi
  log "ISO saved: ${ISO_PATH}"
}

stage_bootstrap_tree() {
  local stage="$1"
  local dest="${stage}/realms-ceremony/usb"
  rm -rf "${stage}/realms-ceremony"
  mkdir -p "${dest}"
  log "staging bootstrap scripts only → ${dest} (live ceremony tree comes from host)"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] would copy usb/*.sh and START-HERE only"
    return 0
  fi
  install -m 755 "${CEREMONY_DIR}/usb/attach-ceremony-from-host.sh" "${dest}/"
  install -m 755 "${CEREMONY_DIR}/usb/auto-attach-from-host.sh" "${dest}/"
  install -m 755 "${CEREMONY_DIR}/usb/find-ceremony-dir.sh" "${dest}/"
  install -m 755 "${CEREMONY_DIR}/usb/launch-ceremony-terminal.sh" "${dest}/"
  install -m 755 "${CEREMONY_DIR}/usb/realms-ceremony-launch.sh" "${dest}/"
  install -m 644 "${CEREMONY_DIR}/usb/CEREMONY-START-HERE.txt" "${dest}/"
  install -m 644 "${CEREMONY_DIR}/usb/Realms-Key-Ceremony.desktop" "${dest}/" 2>/dev/null || true
  install -m 644 "${CEREMONY_DIR}/usb/CEREMONY-START-HERE.txt" "${stage}/CEREMONY-START-HERE.txt"
}

SQUASHFS_PATCHED_OUT=""

_run_unsquashfs() {
  local dest="$1" src="$2"
  # Default unsquashfs prints a progress bar (avoid -quiet / invalid -progress).
  if command -v fakeroot >/dev/null 2>&1; then
    fakeroot unsquashfs -f -d "${dest}" "${src}"
  else
    unsquashfs -f -d "${dest}" -ignore-errors -no-xattrs "${src}"
  fi
}

_run_mksquashfs() {
  local src="$1" dest="$2"
  # mksquashfs -progress exists on squashfs-tools 4.x; fall back to default output.
  local extra=()
  if mksquashfs -help 2>&1 | grep -q -- '-progress'; then
    extra=(-progress)
  fi
  if command -v fakeroot >/dev/null 2>&1; then
    fakeroot mksquashfs "${src}" "${dest}" -comp xz -noappend "${extra[@]}"
  else
    mksquashfs "${src}" "${dest}" -comp xz -noappend "${extra[@]}"
  fi
}

_unmount_squashfs_chroot() {
  local root="$1"
  local wrap=()
  if [[ "${EUID}" -ne 0 ]]; then
    wrap=(sudo)
  fi
  "${wrap[@]}" umount "${root}/run" 2>/dev/null || true
  "${wrap[@]}" umount "${root}/sys" 2>/dev/null || true
  "${wrap[@]}" umount "${root}/proc" 2>/dev/null || true
  "${wrap[@]}" umount "${root}/dev/pts" 2>/dev/null || true
  "${wrap[@]}" umount "${root}/dev" 2>/dev/null || true
}

install_packages_into_squashfs() {
  local root="$1"
  # shellcheck source=lib/packages.sh
  source "${CEREMONY_DIR}/lib/packages.sh"

  if [[ "${WITH_PACKAGES}" != "1" ]]; then
    log "skipping squashfs apt packages (--skip-packages)"
    return 0
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] would apt-get install ceremony packages into squashfs"
    return 0
  fi

  local as_root=()
  if [[ "${EUID}" -ne 0 ]]; then
    if sudo -n true 2>/dev/null; then
      as_root=(sudo)
    else
      die "--with-packages needs root (re-run with sudo, or pass --skip-packages)"
    fi
  fi

  log_step "2c-pkg" "apt-get install ceremony packages into live squashfs (needs network)"
  "${as_root[@]}" mkdir -p "${root}/dev" "${root}/dev/pts" "${root}/proc" "${root}/sys" "${root}/run"
  "${as_root[@]}" mount --bind /dev "${root}/dev"
  "${as_root[@]}" mount --bind /dev/pts "${root}/dev/pts"
  "${as_root[@]}" mount --bind /proc "${root}/proc"
  "${as_root[@]}" mount --bind /sys "${root}/sys"
  "${as_root[@]}" mount --bind /run "${root}/run"
  if [[ -f /etc/resolv.conf ]]; then
    "${as_root[@]}" cp /etc/resolv.conf "${root}/etc/resolv.conf"
  fi

  local pkg_line rc start hb
  pkg_line="${CEREMONY_APT_PACKAGES[*]}"
  start="$(date +%s)"
  log "starting: chroot apt-get update+install"
  (
    while sleep 15; do
      log "  ... still running: chroot apt-get ($(($(date +%s) - start))s elapsed)"
    done
  ) &
  hb=$!
  set +e
  "${as_root[@]}" chroot "${root}" env DEBIAN_FRONTEND=noninteractive bash -lc \
    "apt-get update -qq && apt-get install -y --no-install-recommends ${pkg_line} && (systemctl enable pcscd || true) && (systemctl enable ssh || true)"
  rc=$?
  set -e
  kill "${hb}" 2>/dev/null || true
  wait "${hb}" 2>/dev/null || true
  _unmount_squashfs_chroot "${root}"
  if [[ "${rc}" -ne 0 ]]; then
    die "failed to install ceremony packages into squashfs (exit ${rc})"
  fi
  log "finished: chroot apt-get ($(($(date +%s) - start))s)"

  if [[ -x "${CEREMONY_DIR}/bin/dfx" ]]; then
    log "copying bundled dfx into squashfs /usr/local/bin/dfx"
    "${as_root[@]}" install -m 755 "${CEREMONY_DIR}/bin/dfx" "${root}/usr/local/bin/dfx"
  else
    log "WARNING: ${CEREMONY_DIR}/bin/dfx missing — guest will need online-setup or install-dfx-local.sh"
  fi
}

patch_live_squashfs_desktop() {
  local work="$1"
  local squashfs_in="${work}/filesystem.squashfs.in"
  local squashfs_out="${work}/filesystem.squashfs.out"
  local root="${work}/squashfs-root"

  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] would patch casper/filesystem.squashfs for desktop shortcut"
    SQUASHFS_PATCHED_OUT=""
    return 0
  fi

  log_step "2a" "extract filesystem.squashfs from base ISO (~30s)"
  rm -rf "${root}"
  run_with_progress "xorriso extract filesystem.squashfs" \
    xorriso -osirrox on -indev "${ISO_PATH}" -extract /casper/filesystem.squashfs "${squashfs_in}"

  log_step "2b" "unsquashfs extract live root (~2–3 min; progress below)"
  run_with_progress "unsquashfs extract" _run_unsquashfs "${root}" "${squashfs_in}"

  log_step "2c" "install desktop shortcut + autostart + launchers into live root"
  install -d -m 755 "${root}/usr/local/bin"
  install -d -m 755 "${root}/usr/local/share/realms-ceremony"
  install -m 755 "${CEREMONY_DIR}/usb/realms-ceremony-launch.sh" \
    "${root}/usr/local/bin/realms-ceremony-launch.sh"
  install -m 755 "${CEREMONY_DIR}/usb/launch-ceremony-terminal.sh" \
    "${root}/usr/local/share/realms-ceremony/launch-ceremony-terminal.sh"
  install -m 755 "${CEREMONY_DIR}/usb/attach-ceremony-from-host.sh" \
    "${root}/usr/local/share/realms-ceremony/attach-ceremony-from-host.sh"
  install -m 755 "${CEREMONY_DIR}/usb/realms-ceremony-desktop-setup.sh" \
    "${root}/usr/local/bin/realms-ceremony-desktop-setup.sh"
  # Fallback if 9p/cdrom launch script is missing.
  ln -sfn /usr/local/share/realms-ceremony/launch-ceremony-terminal.sh \
    "${root}/usr/local/bin/launch-ceremony-terminal.sh"

  install -d -m 755 "${root}/etc/skel/Desktop"
  install -m 755 "${CEREMONY_DIR}/usb/skel-desktop/Realms Key Ceremony.desktop" \
    "${root}/etc/skel/Desktop/Realms Key Ceremony.desktop"

  install -d -m 755 "${root}/etc/xdg/autostart"
  install -m 644 "${CEREMONY_DIR}/usb/autostart/realms-ceremony-setup.desktop" \
    "${root}/etc/xdg/autostart/realms-ceremony-setup.desktop"

  [[ -f "${root}/etc/skel/Desktop/Realms Key Ceremony.desktop" ]] \
    || die "desktop shortcut missing before repack"
  [[ -x "${root}/usr/local/bin/realms-ceremony-launch.sh" ]] \
    || die "launch script missing before repack"
  log "desktop shortcut + autostart installed in live root"

  install_packages_into_squashfs "${root}"

  log_step "2d" "mksquashfs repack (~2–3 min; progress below)"
  run_with_progress "mksquashfs repack" _run_mksquashfs "${root}" "${squashfs_out}"
  [[ -f "${squashfs_out}" ]] || die "failed to repack filesystem.squashfs"
  SQUASHFS_PATCHED_OUT="${squashfs_out}"
}

stage_full_ceremony_tree() {
  local stage="$1"
  local dest="${stage}/realms-ceremony"
  rm -rf "${dest}"
  mkdir -p "${dest}"
  log "staging full ceremony tree to ${dest} (airgapped USB)"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] would rsync ceremony sources (excluding vm/cache)"
    return 0
  fi
  rsync -a \
    --exclude 'vm/cache/' \
    --exclude 'vm/work/' \
    --exclude '.git/' \
    "${CEREMONY_DIR}/" "${dest}/"
  chmod +x "${dest}/realms-key-ceremony.sh" \
    "${dest}/prepare-ceremony-live-usb.sh" \
    "${dest}/vm/run-ubuntu-2204-vm-test.sh" \
    "${dest}/vm/guest-run-test.sh" \
    "${dest}/usb/"*.sh \
    "${dest}/docker/test-ceremony.sh" 2>/dev/null || true
  chmod +x "${dest}/usb/"*.desktop 2>/dev/null || true
  install -m 644 "${CEREMONY_DIR}/usb/CEREMONY-START-HERE.txt" "${stage}/CEREMONY-START-HERE.txt"
}

stage_ceremony_tree() {
  if [[ "${EMBED_MODE}" == "full" ]]; then
    stage_full_ceremony_tree "$1"
  else
    stage_bootstrap_tree "$1"
  fi
}

remaster_iso() {
  local stage="$1"
  local out_iso="$2"
  local work xorriso_maps=()
  log_step "2" "patch live desktop + remaster ISO → ${out_iso}"
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] would xorriso -indev ${ISO_PATH} -outdev ${out_iso} -map ${stage}/realms-ceremony /realms-ceremony"
    return 0
  fi

  work="$(mktemp -d)"
  patch_live_squashfs_desktop "${work}"
  [[ -n "${SQUASHFS_PATCHED_OUT}" && -f "${SQUASHFS_PATCHED_OUT}" ]] \
    || die "squashfs desktop patch failed"

  rm -f "${out_iso}"
  xorriso_maps=(
    -boot_image any replay
    -map "${stage}/realms-ceremony" /realms-ceremony
    -map "${stage}/CEREMONY-START-HERE.txt" /CEREMONY-START-HERE.txt
    -map "${SQUASHFS_PATCHED_OUT}" /casper/filesystem.squashfs
  )
  log_step "2e" "xorriso write output ISO (~30–60s)"
  run_with_progress "xorriso remaster commit" \
    xorriso -indev "${ISO_PATH}" -outdev "${out_iso}" \
    "${xorriso_maps[@]}" \
    -commit
  rm -rf "${work}"

  if command -v isohybrid >/dev/null 2>&1; then
    log "running isohybrid on output ISO"
    isohybrid --uefi "${out_iso}" 2>/dev/null || isohybrid "${out_iso}" 2>/dev/null || true
  fi
  log "remastered ISO size: $(du -h "${out_iso}" | awk '{print $1}')"
}

verify_remastered_iso() {
  local out_iso="$1"
  local listing
  [[ "${DRY_RUN}" == "1" ]] && return 0
  log_step "3" "verify remastered ISO (fast path listing only)"
  xorriso -osirrox on -indev "${out_iso}" -ls /CEREMONY-START-HERE.txt >/dev/null 2>&1 \
    || die "remastered ISO missing /CEREMONY-START-HERE.txt"
  if [[ "${EMBED_MODE}" == "full" ]]; then
    listing="$(xorriso -osirrox on -indev "${out_iso}" -ls /realms-ceremony/ 2>/dev/null)" \
      || die "remastered ISO missing /realms-ceremony"
    grep -q 'realms-key-ceremony.sh' <<< "${listing}" \
      || die "remastered ISO missing realms-key-ceremony.sh"
    log "ISO verify OK (full embed: /realms-ceremony + START-HERE)"
  else
    xorriso -osirrox on -indev "${out_iso}" -ls /realms-ceremony/usb/attach-ceremony-from-host.sh >/dev/null 2>&1 \
      || die "remastered ISO missing bootstrap attach-ceremony-from-host.sh"
    xorriso -osirrox on -indev "${out_iso}" -ls /realms-ceremony/usb/find-ceremony-dir.sh >/dev/null 2>&1 \
      || die "remastered ISO missing bootstrap find-ceremony-dir.sh"
    xorriso -osirrox on -indev "${out_iso}" -ls /realms-ceremony/usb/realms-ceremony-launch.sh >/dev/null 2>&1 \
      || die "remastered ISO missing bootstrap realms-ceremony-launch.sh"
    log "ISO verify OK (bootstrap + desktop shortcut; squashfs checked during patch)"
  fi
}

root_disk_for_path() {
  local path="$1"
  findmnt -n -o SOURCE --target "${path}" 2>/dev/null | sed -E 's/p?[0-9]+$//; s/[0-9]+$//'
}

is_removable_disk() {
  local dev="$1"
  local base
  base="$(basename "${dev}")"
  [[ -r "/sys/block/${base}/removable" ]] || return 1
  [[ "$(cat "/sys/block/${base}/removable")" == "1" ]]
}

validate_usb_device() {
  local dev="$1"
  [[ -b "${dev}" ]] || die "not a block device: ${dev}"
  [[ "${dev}" =~ ^/dev/(sd[a-z]+|nvme[0-9]+n[0-9]+|mmcblk[0-9]+)$ ]] \
    || die "refusing device name ${dev} — pass the whole disk (e.g. /dev/sdb), not a partition"
  local root_disk
  root_disk="$(root_disk_for_path /)"
  if [[ "${dev}" == "${root_disk}" ]]; then
    die "refusing to write the system disk ${dev}"
  fi
  if ! is_removable_disk "${dev}"; then
    log "WARNING: ${dev} is not marked removable — double-check this is the ceremony USB"
  fi
  local size
  size="$(blockdev --getsize64 "${dev}")"
  if [[ "${size}" -lt "${MIN_USB_BYTES}" ]]; then
    die "USB too small (${size} bytes) — use at least 8 GB"
  fi
  log "target device: ${dev} ($(lsblk -dn -o SIZE,MODEL "${dev}" | tr -s ' '))"
  lsblk "${dev}" || true
}

unmount_device() {
  local dev="$1"
  local parts
  mapfile -t parts < <(lsblk -ln -o NAME "${dev}" | tail -n +2)
  local p mount
  for p in "${parts[@]}"; do
    mount="$(findmnt -n -o TARGET "/dev/${p}" 2>/dev/null || true)"
    if [[ -n "${mount}" ]]; then
      log "unmounting /dev/${p} (${mount})"
      umount -l "/dev/${p}" 2>/dev/null || umount "/dev/${p}"
    fi
  done
}

confirm_write() {
  local dev="$1"
  [[ "${SKIP_CONFIRM}" == "1" ]] && return 0
  echo
  echo "================================================================"
  echo " ALL DATA ON ${dev} WILL BE DESTROYED."
  echo " Type the device name exactly to continue: ${dev}"
  echo "================================================================"
  local typed
  read -r -p "> " typed
  [[ "${typed}" == "${dev}" ]] || die "confirmation failed — aborted"
}

write_usb() {
  local out_iso="$1"
  local dev="$2"
  validate_usb_device "${dev}"
  confirm_write "${dev}"
  if [[ "${EUID}" -ne 0 ]]; then
    die "writing ${dev} requires root — re-run with sudo"
  fi
  unmount_device "${dev}"
  log "writing ${out_iso} to ${dev} (several minutes)..."
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] would dd if=${out_iso} of=${dev}"
    return 0
  fi
  dd if="${out_iso}" of="${dev}" bs=4M status=progress conv=fsync
  sync
  log "USB write complete — safe to remove after activity stops"
}

main() {
  local stage out_iso
  stage="$(mktemp -d)"
  trap 'rm -rf "${stage}"' EXIT

  if [[ -n "${ISO_ONLY}" ]]; then
    out_iso="$(cd "$(dirname "${ISO_ONLY}")" && pwd)/$(basename "${ISO_ONLY}")"
  else
    out_iso="${CACHE_DIR}/realms-ceremony-live-$(date -u +%Y%m%d).iso"
  fi

  log_step "1" "ensure base Ubuntu 22.04.5 Desktop ISO"
  download_iso
  [[ "${DRY_RUN}" == "1" || -f "${ISO_PATH}" ]] || die "missing base ISO: ${ISO_PATH}"

  log_step "1b" "stage ${EMBED_MODE} ceremony files for ISO"
  stage_ceremony_tree "${stage}"
  remaster_iso "${stage}" "${out_iso}"
  if [[ "${VERIFY_ISO}" == "1" || -n "${ISO_ONLY}" ]]; then
    verify_remastered_iso "${out_iso}"
  fi

  if [[ -n "${ISO_ONLY}" ]]; then
    log "ISO ready: ${out_iso} (embed=${EMBED_MODE})"
    if [[ "${EMBED_MODE}" == "bootstrap" ]]; then
      log "VM: ./vm/run-ubuntu-2204-vm-interactive.sh — scripts attach from host automatically"
    else
      log "Write manually: sudo dd if=${out_iso} of=/dev/sdX bs=4M status=progress conv=fsync"
    fi
    exit 0
  fi

  if [[ "${EMBED_MODE}" == "bootstrap" ]]; then
    die "physical USB requires --full-embed (bootstrap ISO is for QEMU dev only)"
  fi

  write_usb "${out_iso}" "${DEVICE}"
  log "Done. Boot the ceremony laptop from this USB → Try Ubuntu."
  log "Then: cd \"\$(/bin/bash /cdrom/realms-ceremony/usb/find-ceremony-dir.sh)\""
  log "See /cdrom/CEREMONY-START-HERE.txt on the live session."
}

main
