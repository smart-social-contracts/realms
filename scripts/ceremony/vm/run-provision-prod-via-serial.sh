#!/usr/bin/env bash
# Install dfx + run provision-prod in the live VM via serial (streams all guest output).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '[provision-prod] %s\n' "$*" >&2; }

pgrep -f 'qemu-system-x86_64.*realms-ceremony-live' >/dev/null \
  || { log "ceremony VM not running"; exit 1; }

log "using serial console — guest output streams below"
log "touch the YubiKey in the VM window when step 4 asks"

python3 -u "${SCRIPT_DIR}/serial_guest_cmd.py" --boot-wait 0 \
  --cmd 'curl -fsSL http://10.0.2.2:8890/install-dfx.sh | sudo bash -s 8890' \
  --cmd 'cd /opt/realms-ceremony && sudo ./realms-key-ceremony.sh provision-prod'

log "finished"
