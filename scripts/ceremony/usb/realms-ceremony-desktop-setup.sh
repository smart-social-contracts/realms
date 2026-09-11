#!/usr/bin/env bash
# Run at live-session login — trusted desktop shortcut + silent host attach.
set -euo pipefail

log() { printf '[ceremony-desktop] %s\n' "$*" >&2; }

desktop_name="Realms Key Ceremony.desktop"
dest="${HOME}/Desktop/${desktop_name}"

mkdir -p "${HOME}/Desktop"

# Always point the icon at the baked launcher (opens a terminal; never a zenity dialog).
cat > "${dest}" <<'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Realms Key Ceremony
Comment=Open a terminal in the ceremony folder
Exec=/usr/local/bin/realms-ceremony-launch.sh
Icon=utilities-terminal
Terminal=false
Categories=System;
StartupNotify=true
EOF
chmod +x "${dest}"
if command -v gio >/dev/null 2>&1; then
  gio set "${dest}" metadata::trusted true 2>/dev/null || true
fi

# Silent attach so the folder is ready when the user clicks the icon.
for attach in \
  /cdrom/realms-ceremony/usb/attach-ceremony-from-host.sh \
  /run/live/mount/medium/realms-ceremony/usb/attach-ceremony-from-host.sh \
  /lib/live/mount/medium/realms-ceremony/usb/attach-ceremony-from-host.sh \
  /usr/local/share/realms-ceremony/attach-ceremony-from-host.sh; do
  if [[ -f "${attach}" ]]; then
    sudo -n bash "${attach}" >/tmp/realms-ceremony-attach.log 2>&1 || true
    break
  fi
done

log "desktop shortcut ready: ${dest}"
