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

_net_sudo() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo -n "$@" 2>/dev/null || sudo "$@"
  else
    return 1
  fi
}

# Cut every interface the ceremony machine has. Belt and braces on purpose: a
# single mechanism is not enough (rfkill misses wired, nmcli is absent on some
# live images), and being wrong here means generating keys on a networked host.
network_disable_all() {
  local did_something=0

  if command -v nmcli >/dev/null 2>&1; then
    if _net_sudo nmcli networking off >/dev/null 2>&1; then
      log_detail "NetworkManager: networking off"
      did_something=1
    fi
    _net_sudo nmcli radio all off >/dev/null 2>&1 \
      && log_detail "NetworkManager: all radios off (Wi‑Fi, WWAN, Bluetooth)"
  fi

  if command -v rfkill >/dev/null 2>&1; then
    _net_sudo rfkill block all >/dev/null 2>&1 \
      && { log_detail "rfkill: all wireless blocked"; did_something=1; }
  fi

  # Wired links stay up even with radios blocked, so take them down by name.
  local iface
  for iface in $(ls /sys/class/net 2>/dev/null); do
    [[ "${iface}" == "lo" ]] && continue
    if _net_sudo ip link set "${iface}" down >/dev/null 2>&1; then
      log_detail "interface ${iface}: down"
      did_something=1
    fi
  done

  [[ "${did_something}" == "1" ]] || return 1
  # Links drop asynchronously; probing too early reports a stale "online".
  sleep 3
  return 0
}

require_offline() {
  if [[ "${CEREMONY_FORCE_OFFLINE}" == "1" ]]; then
    log "network check: forced offline (OK for ceremony)"
    return 0
  fi
  if is_online && [[ "${CEREMONY_NO_AUTO_OFFLINE:-0}" != "1" ]]; then
    log "network check: still online — disconnecting all interfaces now"
    network_disable_all \
      || log "warning: could not disconnect automatically (no sudo/nmcli/ip?)"
  fi
  if is_online; then
    die "network check: still online — disconnect Wi‑Fi/Ethernet manually, then re-run (set CEREMONY_NO_AUTO_OFFLINE=1 to skip auto-disconnect)"
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
