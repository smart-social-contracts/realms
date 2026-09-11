#!/usr/bin/env bash
# Double-click helper — open a terminal in /opt/realms-ceremony.
# Boot already attaches the host share (systemd). This waits briefly, then opens bash.
set -u

DIR="/opt/realms-ceremony"
_log="/tmp/realms-ceremony-attach.log"

_try_attach() {
  [[ -f "${DIR}/realms-key-ceremony.sh" ]] && return 0
  local attach
  for attach in \
    /usr/local/share/realms-ceremony/attach-ceremony-from-host.sh \
    /cdrom/realms-ceremony/usb/attach-ceremony-from-host.sh \
    /run/live/mount/medium/realms-ceremony/usb/attach-ceremony-from-host.sh; do
    [[ -f "${attach}" ]] || continue
    if [[ "${EUID}" -eq 0 ]]; then
      bash "${attach}" >"${_log}" 2>&1 && return 0
    elif sudo -n true 2>/dev/null; then
      sudo -n bash "${attach}" >"${_log}" 2>&1 && return 0
    fi
  done
  return 1
}

# Boot service may still be mounting 9p.
for _ in $(seq 1 20); do
  [[ -f "${DIR}/realms-key-ceremony.sh" ]] && break
  _try_attach && break
  sleep 1
done

if [[ -f "${DIR}/realms-key-ceremony.sh" ]]; then
  WORK="${DIR}"
elif [[ -f /cdrom/realms-ceremony/realms-key-ceremony.sh ]]; then
  WORK="/cdrom/realms-ceremony"
else
  WORK="${HOME:-/home/ubuntu}"
fi

CMD='
cd /opt/realms-ceremony 2>/dev/null || cd /cdrom/realms-ceremony 2>/dev/null || true
echo "Realms Key Ceremony — $(pwd)"
echo
if [[ -f ./realms-key-ceremony.sh ]]; then
  echo "Typical flow:"
  echo "  1. sudo ./realms-key-ceremony.sh online-setup          # while online"
  echo "  2. (optional) cp operator-credentials.example my-piv.txt"
  echo "       edit PIV_PIN/PIV_PUK → offline-generate --credentials-file my-piv.txt"
  echo "  3. disconnect network → check-offline → offline-generate"
  echo "  4. provision-dev / provision-prod (plug YubiKey before VM boot in QEMU)"
  echo "     Used key?  CEREMONY_PIV_RESET=1 sudo -E ./realms-key-ceremony.sh provision-prod"
  echo "  5. finalize (writes the verification bundle) → destroy"
  echo
  echo "Details: cat usb/CEREMONY-START-HERE.txt  (or README.md)"
  echo
  command -v ykman >/dev/null && echo "ykman: $(ykman --version 2>/dev/null | head -1)"
  env -u NO_COLOR -u FORCE_COLOR TERM=xterm dfx --version 2>/dev/null | head -1 | sed "s/^/dfx:   /"
  echo
fi
exec bash --login
'

if command -v gnome-terminal >/dev/null 2>&1; then
  exec gnome-terminal --working-directory="${WORK}" -- bash -lc "${CMD}"
fi
if command -v x-terminal-emulator >/dev/null 2>&1; then
  exec x-terminal-emulator -e bash -lc "cd '${WORK}'; ${CMD}"
fi
if command -v xterm >/dev/null 2>&1; then
  exec xterm -e bash -lc "cd '${WORK}'; ${CMD}"
fi

eval "${CMD}"
