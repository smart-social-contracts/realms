#!/usr/bin/env bash
# Apt packages baked into the ceremony live image (and installed by online-setup if missing).
# shellcheck disable=SC2034

CEREMONY_APT_PACKAGES=(
  openssl
  jq
  curl
  ca-certificates
  pcscd
  libpcsclite1
  yubikey-manager
  yubikey-manager-qt
  ykcs11
  yubico-piv-tool
  coreutils
  python3
  exfatprogs
  ntfs-3g
  util-linux
  mount
  libdbus-1-3
  openssh-server
)

ceremony_packages_present() {
  command -v ykman >/dev/null 2>&1 \
    && command -v openssl >/dev/null 2>&1 \
    && command -v python3 >/dev/null 2>&1 \
    && command -v jq >/dev/null 2>&1 \
    && [[ -f "${CEREMONY_PKCS11_LIB:-/usr/lib/x86_64-linux-gnu/libykcs11.so}" ]]
}
