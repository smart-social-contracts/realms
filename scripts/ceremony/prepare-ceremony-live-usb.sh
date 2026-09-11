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
# shellcheck source=lib/usb_labels.sh
source "${SCRIPT_DIR}/lib/usb_labels.sh"
# shellcheck source=lib/usb_disk.sh
source "${SCRIPT_DIR}/lib/usb_disk.sh"
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
  - Wipes every partition table (including a leftover GPT at the end of the stick).
  - Writes the live ISO, then creates an empty exFAT "CEREMONY DATA" volume
    in the remaining space. ALL data on the device is destroyed.
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
if [[ -n "${DEVICE}" ]]; then
  require_cmd wipefs util-linux
  require_cmd sgdisk gdisk
  require_cmd parted parted
  require_cmd mkfs.exfat exfatprogs
fi
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
  install -m 644 "${CEREMONY_DIR}/usb/realms-ceremony-attach.service" "${dest}/" 2>/dev/null || true
  install -m 644 "${CEREMONY_DIR}/usb/CEREMONY-START-HERE.txt" "${dest}/"
  install -m 644 "${CEREMONY_DIR}/operator-credentials.example" "${dest}/" 2>/dev/null || true
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
  local wrap=() tgt
  if [[ "${EUID}" -ne 0 ]]; then
    wrap=(sudo)
  fi
  # Deepest mounts first. Never `rm -rf` this tree while anything is mounted —
  # a leftover /run bind is the host's udev/docker runtime.
  while IFS= read -r tgt; do
    [[ -n "${tgt}" ]] || continue
    "${wrap[@]}" umount "${tgt}" 2>/dev/null || "${wrap[@]}" umount -l "${tgt}" 2>/dev/null || true
  done < <(findmnt -Rn -o TARGET 2>/dev/null | grep "^${root}/" | sort -r)
  "${wrap[@]}" umount "${root}/run" 2>/dev/null || true
  "${wrap[@]}" umount "${root}/sys" 2>/dev/null || true
  "${wrap[@]}" umount "${root}/proc" 2>/dev/null || true
  "${wrap[@]}" umount "${root}/dev/pts" 2>/dev/null || true
  "${wrap[@]}" umount "${root}/dev" 2>/dev/null || true
}

_squashfs_still_mounted() {
  local root="$1"
  findmnt -Rn -o TARGET 2>/dev/null | grep -q "^${root}/"
}

_safe_rm_work_dir() {
  local work="$1"
  local root="${work}/squashfs-root"
  [[ -d "${work}" ]] || return 0
  _unmount_squashfs_chroot "${root}"
  if _squashfs_still_mounted "${root}"; then
    log "ERROR: refusing to delete ${work} — chroot mounts still active:"
    findmnt -Rn -o TARGET 2>/dev/null | grep "^${root}/" >&2 || true
    return 1
  fi
  rm -rf "${work}"
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
      log "WARNING: not root — skipping squashfs apt (need sudo to bake ykman/ykcs11). Desktop launcher + bundled dfx still apply."
      if [[ -x "${CEREMONY_DIR}/bin/dfx" ]]; then
        install -m 755 "${CEREMONY_DIR}/bin/dfx" "${root}/usr/local/bin/dfx"
        log "copied bundled dfx to squashfs /usr/local/bin/dfx"
      fi
      return 0
    fi
  fi

  log_step "2c-pkg" "apt-get install ceremony packages into live squashfs (needs network)"
  "${as_root[@]}" mkdir -p "${root}/dev" "${root}/dev/pts" "${root}/proc" "${root}/sys" "${root}/run"
  # Always tear down chroot mounts, including if apt or resolv setup fails.
  trap '_unmount_squashfs_chroot "'"${root}"'"' RETURN
  "${as_root[@]}" mount --bind /dev "${root}/dev"
  "${as_root[@]}" mount --bind /dev/pts "${root}/dev/pts"
  "${as_root[@]}" mount --bind /proc "${root}/proc"
  "${as_root[@]}" mount --bind /sys "${root}/sys"
  # Empty tmpfs — never bind-mount host /run (udev/docker). That made cleanup
  # try to `rm` this laptop's runtime files.
  "${as_root[@]}" mount -t tmpfs -o mode=755 tmpfs "${root}/run"
  # Live image resolv.conf is a symlink into /run; replace with a real file
  # for chroot DNS, then restore the symlink so the live session is unchanged.
  "${as_root[@]}" rm -f "${root}/etc/resolv.conf"
  printf 'nameserver 1.1.1.1\nnameserver 8.8.8.8\n' \
    | "${as_root[@]}" tee "${root}/etc/resolv.conf" >/dev/null

  # The Desktop live squashfs only has a cdrom: sources.list (main/restricted).
  # pcscd, ykman, exfatprogs, etc. live in universe — point chroot at the archive.
  "${as_root[@]}" mkdir -p "${root}/etc/apt/sources.list.d"
  if [[ -f "${root}/etc/apt/sources.list" ]]; then
    "${as_root[@]}" cp "${root}/etc/apt/sources.list" "${root}/etc/apt/sources.list.pre-ceremony"
  fi
  printf '%s\n' \
    'deb http://archive.ubuntu.com/ubuntu jammy main restricted universe multiverse' \
    'deb http://archive.ubuntu.com/ubuntu jammy-updates main restricted universe multiverse' \
    'deb http://security.ubuntu.com/ubuntu jammy-security main restricted universe multiverse' \
    | "${as_root[@]}" tee "${root}/etc/apt/sources.list" >/dev/null
  # Disable leftover cdrom / oem lists so apt does not wait on a missing disc.
  local list
  for list in "${root}/etc/apt/sources.list.d"/*.list; do
    [[ -f "${list}" ]] || continue
    "${as_root[@]}" mv "${list}" "${list}.disabled"
  done

  local pkg_line rc start hb
  pkg_line="${CEREMONY_APT_PACKAGES[*]}"
  start="$(date +%s)"
  log "starting: chroot apt-get update+install (jammy universe enabled)"
  (
    while sleep 15; do
      log "  ... still running: chroot apt-get ($(($(date +%s) - start))s elapsed)"
    done
  ) &
  hb=$!
  set +e
  "${as_root[@]}" chroot "${root}" env DEBIAN_FRONTEND=noninteractive bash -lc \
    "apt-get update && apt-get install -y --no-install-recommends ${pkg_line} && (systemctl enable pcscd || true) && (systemctl enable ssh || true)"
  rc=$?
  set -e
  kill "${hb}" 2>/dev/null || true
  wait "${hb}" 2>/dev/null || true
  trap - RETURN
  _unmount_squashfs_chroot "${root}"
  # Restore systemd-resolved layout used by the live session.
  "${as_root[@]}" rm -f "${root}/etc/resolv.conf"
  "${as_root[@]}" ln -s ../run/systemd/resolve/stub-resolv.conf "${root}/etc/resolv.conf"
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

  install -d -m 755 "${root}/opt/realms-ceremony"
  install -d -m 755 "${root}/etc/modules-load.d"
  install -m 644 "${CEREMONY_DIR}/usb/modules-load.d-realms-9p.conf" \
    "${root}/etc/modules-load.d/realms-9p.conf"
  install -d -m 755 "${root}/etc/systemd/system"
  install -m 644 "${CEREMONY_DIR}/usb/realms-ceremony-attach.service" \
    "${root}/etc/systemd/system/realms-ceremony-attach.service"
  install -d -m 755 "${root}/etc/systemd/system/multi-user.target.wants"
  install -d -m 755 "${root}/etc/systemd/system/graphical.target.wants"
  ln -sfn /etc/systemd/system/realms-ceremony-attach.service \
    "${root}/etc/systemd/system/multi-user.target.wants/realms-ceremony-attach.service"
  ln -sfn /etc/systemd/system/realms-ceremony-attach.service \
    "${root}/etc/systemd/system/graphical.target.wants/realms-ceremony-attach.service"

  if ! grep -q 'realms_ceremony' "${root}/etc/fstab" 2>/dev/null; then
    printf '%s\n' \
      'realms_ceremony /opt/realms-ceremony 9p trans=virtio,version=9p2000.L,_netdev,nofail,x-systemd.automount 0 0' \
      >> "${root}/etc/fstab"
  fi
  install -d -m 755 "${root}/etc/sudoers.d"
  printf '%s\n' 'ubuntu ALL=(ALL) NOPASSWD:ALL' \
    > "${root}/etc/sudoers.d/realms-ceremony"
  chmod 440 "${root}/etc/sudoers.d/realms-ceremony"

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
  # EXIT (not RETURN): the inner apt function also uses a RETURN trap.
  trap '_safe_rm_work_dir "'"${work}"'" || true' EXIT
  patch_live_squashfs_desktop "${work}"
  [[ -n "${SQUASHFS_PATCHED_OUT}" && -f "${SQUASHFS_PATCHED_OUT}" ]] \
    || die "squashfs desktop patch failed"

  rm -f "${out_iso}"
  xorriso_maps=(
    -boot_image any replay
    -volid "${CEREMONY_OS_LABEL:-CEREMONY OS}"
    -map "${stage}/realms-ceremony" /realms-ceremony
    -map "${stage}/CEREMONY-START-HERE.txt" /CEREMONY-START-HERE.txt
    -map "${SQUASHFS_PATCHED_OUT}" /casper/filesystem.squashfs
  )
  log_step "2e" "xorriso write output ISO (~30–60s)"
  run_with_progress "xorriso remaster commit" \
    xorriso -indev "${ISO_PATH}" -outdev "${out_iso}" \
    "${xorriso_maps[@]}" \
    -commit
  _safe_rm_work_dir "${work}" || die "could not unmount squashfs work dir before delete"
  trap - EXIT

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
  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[dry-run] would wipe ${dev}, dd ${out_iso}, create exFAT '${CEREMONY_DATA_LABEL}'"
    return 0
  fi
  usb_flash_iso_and_partition "${out_iso}" "${dev}"
  log "USB write complete — CEREMONY OS (live) + CEREMONY DATA (empty, for finalize)"
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
      log "Write + partition: sudo $0 --full-embed --device /dev/sdX --yes"
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
