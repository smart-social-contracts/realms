#!/usr/bin/env bash
# Restart the interactive ceremony VM with serial SSH bootstrap, then wait for SSH.
#
# Usage:
#   ./vm/restart-interactive-vm.sh
#   ./vm/restart-interactive-vm.sh --option-a
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPTION_A=0

log() { printf '[restart-vm] %s\n' "$*" >&2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --option-a) OPTION_A=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
    *) log "unknown option: $1"; exit 1 ;;
  esac
  shift
done

"${SCRIPT_DIR}/stop-interactive-vm.sh"
log "starting VM in background (serial bootstrap + GTK)"
log "all output streams below — nothing is hidden"
"${SCRIPT_DIR}/run-ubuntu-2204-vm-interactive.sh" --bg

if [[ "${OPTION_A}" == "1" ]]; then
  "${SCRIPT_DIR}/guest-exec.sh" --option-a
else
  "${SCRIPT_DIR}/guest-exec.sh" --wait-ssh
fi
