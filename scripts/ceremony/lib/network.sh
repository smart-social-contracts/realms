#!/usr/bin/env bash
# Network gate helpers — ceremony must be offline during key generation.
set -euo pipefail

# Hosts used only to detect outbound connectivity (not contacted for secrets).
CEREMONY_NET_PROBE_HOSTS=(
  "1.1.1.1"
  "8.8.8.8"
  "icp0.io"
)

_network_probe_once() {
  local host="$1"
  if command -v curl >/dev/null 2>&1; then
    curl --max-time 2 -fsS "https://${host}" >/dev/null 2>&1 && return 0
    curl --max-time 2 -fsS "http://${host}" >/dev/null 2>&1 && return 0
  fi
  if command -v ping >/dev/null 2>&1; then
    ping -c1 -W2 "${host}" >/dev/null 2>&1 && return 0
  fi
  return 1
}

is_online() {
  if [[ "${CEREMONY_FORCE_ONLINE}" == "1" ]]; then
    return 0
  fi
  if [[ "${CEREMONY_FORCE_OFFLINE}" == "1" ]]; then
    return 1
  fi
  local host
  for host in "${CEREMONY_NET_PROBE_HOSTS[@]}"; do
    if _network_probe_once "${host}"; then
      return 0
    fi
  done
  return 1
}

require_online() {
  if is_online; then
    log "network check: online (OK for setup)"
    return 0
  fi
  die "network check: offline — connect to the internet before online-setup"
}

require_offline() {
  if [[ "${CEREMONY_FORCE_OFFLINE}" == "1" ]]; then
    log "network check: forced offline (OK for ceremony)"
    return 0
  fi
  if is_online; then
    die "network check: still online — disconnect Wi‑Fi/Ethernet before offline phases"
  fi
  log "network check: offline (OK for ceremony)"
}

prepare_live_session_for_apt() {
  # Ubuntu Desktop live ISO defaults to CD-ROM-only apt sources; QEMU user-net needs explicit DNS.
  if ! grep -q casper /proc/cmdline 2>/dev/null; then
    return 0
  fi

  local write=(tee)
  if [[ "${EUID}" -ne 0 ]]; then
    write=(sudo tee)
  fi

  if ip route 2>/dev/null | grep -q 'default via 10.0.2.2'; then
    log "QEMU user-net detected — setting resolver to 10.0.2.3"
    if [[ "${EUID}" -eq 0 ]]; then
      rm -f /etc/resolv.conf
      echo nameserver 10.0.2.3 > /etc/resolv.conf
    else
      sudo rm -f /etc/resolv.conf
      echo nameserver 10.0.2.3 | sudo tee /etc/resolv.conf >/dev/null
    fi
  elif ! getent hosts archive.ubuntu.com >/dev/null 2>&1; then
    log "warning: archive.ubuntu.com does not resolve; apt may fail until DNS is configured"
  fi

  if ! grep -q '^deb http://archive.ubuntu.com/ubuntu jammy main' /etc/apt/sources.list 2>/dev/null; then
    log "enabling Ubuntu archive apt sources for live session"
    if [[ "${EUID}" -eq 0 ]]; then
      sed -i 's/^deb cdrom:/# deb cdrom:/' /etc/apt/sources.list 2>/dev/null || true
    else
      sudo sed -i 's/^deb cdrom:/# deb cdrom:/' /etc/apt/sources.list 2>/dev/null || true
    fi
    cat <<'EOF' | "${write[@]}" -a /etc/apt/sources.list >/dev/null

deb http://archive.ubuntu.com/ubuntu jammy main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu jammy-updates main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu jammy-security main restricted universe multiverse
EOF
  fi
}
