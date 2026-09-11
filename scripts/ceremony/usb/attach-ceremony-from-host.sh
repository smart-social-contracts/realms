#!/usr/bin/env bash
# Attach the live ceremony tree from the prep laptop (QEMU virtio-9p or HTTP push).
# The remastered ISO only carries this bootstrap — not the full ceremony sources.
#
# Target (writable): /opt/realms-ceremony
# QEMU host share:   mount_tag=realms_ceremony (virtio-9p)
# HTTP fallback:     http://10.0.2.2:8890/ (run vm/push-ceremony-scripts.sh on host)
#
set -euo pipefail

CEREMONY_TARGET="${CEREMONY_TARGET:-/opt/realms-ceremony}"
CEREMONY_9P_TAG="${CEREMONY_9P_TAG:-realms_ceremony}"
CEREMONY_HOST_GATEWAY="${CEREMONY_HOST_GATEWAY:-10.0.2.2}"
CEREMONY_PUSH_PORT="${CEREMONY_PUSH_PORT:-8890}"

log() { printf '[attach-ceremony] %s\n' "$*" >&2; }

die() {
  log "ERROR: $*"
  exit 1
}

ceremony_ready() {
  [[ -f "${CEREMONY_TARGET}/realms-key-ceremony.sh" ]]
}

try_embedded_iso_tree() {
  local d
  for d in \
    /cdrom/realms-ceremony \
    /run/live/mount/medium/realms-ceremony \
    /lib/live/mount/medium/realms-ceremony \
    /isodevice/realms-ceremony; do
    if [[ -f "${d}/realms-key-ceremony.sh" ]]; then
      log "using full ceremony tree embedded on install medium: ${d}"
      printf '%s\n' "${d}"
      return 0
    fi
  done
  return 1
}

load_9p_modules() {
  modprobe 9p 2>/dev/null || true
  modprobe 9pnet 2>/dev/null || true
  modprobe 9pnet_virtio 2>/dev/null || true
}

mount_from_9p() {
  load_9p_modules
  install -d -m 755 "${CEREMONY_TARGET}"
  if mountpoint -q "${CEREMONY_TARGET}" 2>/dev/null; then
    if ceremony_ready; then
      log "already mounted at ${CEREMONY_TARGET} (virtio-9p)"
      return 0
    fi
    umount "${CEREMONY_TARGET}" 2>/dev/null || true
  fi
  log "mounting host ceremony tree via virtio-9p (${CEREMONY_9P_TAG}) → ${CEREMONY_TARGET}"
  log "YubiKey touch: not applicable"
  local err
  err="$(mount -t 9p -o trans=virtio,version=9p2000.L "${CEREMONY_9P_TAG}" "${CEREMONY_TARGET}" 2>&1)" || {
    log "virtio-9p mount failed: ${err:-unknown error}"
    return 1
  }
  if ! ceremony_ready; then
    umount "${CEREMONY_TARGET}" 2>/dev/null || true
    log "9p mount succeeded but realms-key-ceremony.sh is missing on the host share"
    return 1
  fi
  log "attached live scripts from laptop (edit on host — changes are immediate)"
  return 0
}

mount_from_http() {
  local base port tmp
  port="${CEREMONY_PUSH_PORT}"
  base="http://${CEREMONY_HOST_GATEWAY}:${port}"
  command -v curl >/dev/null 2>&1 || return 1
  log "fetching ceremony tree from ${base} (HTTP push on host)"
  local probe_err
  probe_err="$(curl -fsSL --max-time 15 "${base}/realms-ceremony-update.tar.gz" -o /dev/null 2>&1)" || {
    log "HTTP probe failed (${base}): ${probe_err:-no response — is ./vm/push-ceremony-scripts.sh running on the host?)"
    return 1
  }
  tmp="$(mktemp -d)"
  curl -fsSL "${base}/realms-ceremony-update.tar.gz" -o "${tmp}/update.tar.gz"
  install -d -m 755 "${CEREMONY_TARGET}"
  tar -xzf "${tmp}/update.tar.gz" -C "${CEREMONY_TARGET}"
  chmod +x "${CEREMONY_TARGET}/realms-key-ceremony.sh" \
    "${CEREMONY_TARGET}/usb/"*.sh \
    "${CEREMONY_TARGET}/vm/"*.sh 2>/dev/null || true
  rm -rf "${tmp}"
  ceremony_ready || return 1
  log "attached scripts from host HTTP push (${base})"
  return 0
}

main() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "run as root: sudo $0"
  fi

  if ceremony_ready; then
    log "ceremony scripts ready at ${CEREMONY_TARGET}"
    printf '%s\n' "${CEREMONY_TARGET}"
    return 0
  fi

  if mount_from_9p; then
    printf '%s\n' "${CEREMONY_TARGET}"
    return 0
  fi
  log "virtio-9p attach failed — trying HTTP / embedded fallback"

  if mount_from_http; then
    printf '%s\n' "${CEREMONY_TARGET}"
    return 0
  fi

  local embedded
  if embedded="$(try_embedded_iso_tree)"; then
    printf '%s\n' "${embedded}"
    return 0
  fi

  die "could not attach ceremony scripts — on QEMU, start ./vm/run-ubuntu-2204-vm-interactive.sh on the host (virtio-9p + HTTP push); on a physical USB, rebuild with --full-embed"
}

main "$@"
