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
