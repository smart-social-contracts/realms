#!/usr/bin/env bash
# Fresh Ubuntu desktop VM: install only what is needed to test
#   icp identity link web oisy_probe --app https://oisy.com --storage plaintext
#
# Requires a GUI session (Firefox/Chromium). Do not use a headless SSH box.
# Usage:  curl -fsSL … | bash   OR   bash bootstrap_icp_link_web_test.sh

set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as a normal user (the script will sudo). Do not run as root." >&2
  exit 1
fi

if [[ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  echo "No graphical display. Log into the Ubuntu desktop session first." >&2
  exit 1
fi

echo "==> apt packages (icp runtime + browser + opener)"
sudo apt-get update -y
sudo apt-get install -y \
  ca-certificates \
  curl \
  libdbus-1-3 \
  libssl3 \
  xdg-utils \
  xdg-user-dirs

# Firefox: deb package on some images, snap on Ubuntu 24.04 desktop.
if ! command -v firefox >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1 && ! command -v chromium >/dev/null 2>&1; then
  if apt-cache show firefox >/dev/null 2>&1; then
    sudo apt-get install -y firefox || true
  fi
  if ! command -v firefox >/dev/null 2>&1; then
    if command -v snap >/dev/null 2>&1; then
      sudo snap install firefox
    else
      sudo apt-get install -y chromium-browser || sudo apt-get install -y chromium
    fi
  fi
fi

echo "==> icp-cli (official installer, no Motoko/Rust/npm stack)"
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/dfinity/icp-cli/releases/latest/download/icp-cli-installer.sh | sh

# installer drops the binary in ~/.cargo/bin
ICP_BIN="${HOME}/.cargo/bin"
case ":${PATH}:" in
  *":${ICP_BIN}:"*) ;;
  *)
    export PATH="${ICP_BIN}:${PATH}"
    if ! grep -q '\.cargo/bin' "${HOME}/.bashrc" 2>/dev/null; then
      echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "${HOME}/.bashrc"
    fi
    ;;
esac

command -v icp >/dev/null
icp --version

echo
echo "Install OK. In this graphical terminal, run:"
echo
echo "  export PATH=\"\$HOME/.cargo/bin:\$PATH\""
echo "  icp identity link web oisy_probe --app https://oisy.com --storage plaintext"
echo
echo "Press Enter when prompted. Success = II shows an Allow / sign-in page"
echo "(not a blank /cli or 'Invalid request'). Passkeys in VirtualBox may still fail;"
echo "seeing the UI is enough for this test."
echo
echo "Then Ctrl+C / delete the probe identity if you want:"
echo "  icp identity delete oisy_probe"
echo
