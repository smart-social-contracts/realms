#!/usr/bin/env bash
# Desktop entry target — always open a ceremony terminal (never a zenity error dialog).
set -u

for launch in \
  /opt/realms-ceremony/usb/launch-ceremony-terminal.sh \
  /cdrom/realms-ceremony/usb/launch-ceremony-terminal.sh \
  /run/live/mount/medium/realms-ceremony/usb/launch-ceremony-terminal.sh \
  /usr/local/share/realms-ceremony/launch-ceremony-terminal.sh; do
  if [[ -x "${launch}" ]]; then
    exec bash "${launch}"
  fi
done

# Last resort: open a shell even if bootstrap scripts are missing from this ISO.
if command -v gnome-terminal >/dev/null 2>&1; then
  exec gnome-terminal --working-directory="${HOME:-/home/ubuntu}" -- bash --login
fi
exec bash --login
