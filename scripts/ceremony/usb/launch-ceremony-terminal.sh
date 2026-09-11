#!/usr/bin/env bash
# Double-click helper — always open a terminal in the ceremony folder.
# Attach (virtio-9p / HTTP) happens silently first, then again inside the terminal if needed.
set -u

DIR="/opt/realms-ceremony"
_log="/tmp/realms-ceremony-attach.log"

_try_silent_attach() {
  [[ -f "${DIR}/realms-key-ceremony.sh" ]] && return 0
  local attach
  for attach in \
    /cdrom/realms-ceremony/usb/attach-ceremony-from-host.sh \
    /run/live/mount/medium/realms-ceremony/usb/attach-ceremony-from-host.sh \
    /lib/live/mount/medium/realms-ceremony/usb/attach-ceremony-from-host.sh \
    /usr/local/share/realms-ceremony/attach-ceremony-from-host.sh; do
    [[ -f "${attach}" ]] || continue
    if sudo -n bash "${attach}" >"${_log}" 2>&1; then
      return 0
    fi
  done
  return 1
}

_try_silent_attach || true

if [[ -f "${DIR}/realms-key-ceremony.sh" ]]; then
  WORK="${DIR}"
elif [[ -f /cdrom/realms-ceremony/realms-key-ceremony.sh ]]; then
  DIR="/cdrom/realms-ceremony"
  WORK="${DIR}"
else
  WORK="${HOME:-/home/ubuntu}"
fi

CMD='
set +e
DIR=/opt/realms-ceremony
if [[ ! -f "${DIR}/realms-key-ceremony.sh" ]]; then
  echo "Attaching ceremony scripts from the host..."
  for attach in \
    /cdrom/realms-ceremony/usb/attach-ceremony-from-host.sh \
    /run/live/mount/medium/realms-ceremony/usb/attach-ceremony-from-host.sh \
    /lib/live/mount/medium/realms-ceremony/usb/attach-ceremony-from-host.sh \
    /usr/local/share/realms-ceremony/attach-ceremony-from-host.sh; do
    if [[ -f "${attach}" ]]; then
      sudo bash "${attach}" && break
    fi
  done
fi
if [[ -f /opt/realms-ceremony/realms-key-ceremony.sh ]]; then
  cd /opt/realms-ceremony || true
elif [[ -f /cdrom/realms-ceremony/realms-key-ceremony.sh ]]; then
  cd /cdrom/realms-ceremony || true
fi
clear
echo "Realms Key Ceremony — $(pwd)"
echo
if [[ -f ./realms-key-ceremony.sh ]]; then
  echo "Ready. Typical next steps:"
  echo "  sudo ./realms-key-ceremony.sh online-setup     # no-op if packages are in this image"
  echo "  sudo ./realms-key-ceremony.sh check-offline"
  echo "  sudo ./realms-key-ceremony.sh run-offline"
  echo
  command -v ykman >/dev/null && echo "ykman: $(ykman --version 2>/dev/null | head -1)"
  env -u NO_COLOR -u FORCE_COLOR TERM=xterm dfx --version 2>/dev/null | head -1 | sed "s/^/dfx:   /"
  echo
else
  echo "Ceremony scripts not found yet."
  echo "  sudo bash /usr/local/share/realms-ceremony/attach-ceremony-from-host.sh"
  echo "  cd /opt/realms-ceremony"
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
