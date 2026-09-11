#!/usr/bin/env bash
# dfx install for YubiKey HSM principal verification (icp-cli has no PKCS#11 HSM path yet).
set -euo pipefail

CEREMONY_DFX_VERSION="${CEREMONY_DFX_VERSION:-0.24.3}"

# dfx 0.24.x panics on SSH/non-TTY if NO_COLOR/FORCE_COLOR conflict (ColorOutOfRange).
ceremony_dfx_env() {
  export TERM="${TERM:-xterm}"
  unset NO_COLOR FORCE_COLOR 2>/dev/null || true
  export DFX_WARNING="${DFX_WARNING:--mainnet_plaintext_identity}"
}

ceremony_run_dfx() {
  local dfx_bin
  dfx_bin="$(ceremony_dfx)"
  env -u NO_COLOR -u FORCE_COLOR TERM=xterm DFX_WARNING=-mainnet_plaintext_identity \
    "${dfx_bin}" "$@"
}

ceremony_dfx() {
  if command -v dfx >/dev/null 2>&1; then
    command -v dfx
    return 0
  fi
  local script_dir bundled
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  bundled="${script_dir}/bin/dfx"
  if [[ -x "${bundled}" ]]; then
    printf '%s\n' "${bundled}"
    return 0
  fi
  return 1
}

ceremony_ensure_dfx() {
  if ceremony_dfx >/dev/null 2>&1; then
    return 0
  fi
  die "dfx is required for HSM principal verification — run: sudo ${CEREMONY_ROOT:-/opt/realms-ceremony}/bin/install-dfx-local.sh"
}

install_dfx_local() {
  local script_dir bundled
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  bundled="${script_dir}/bin/dfx"
  if [[ -x "${bundled}" ]]; then
    install -m 755 "${bundled}" /usr/local/bin/dfx
    log_detail "installed bundled dfx to /usr/local/bin/dfx"
    return 0
  fi
  return 1
}

install_dfx_for_ceremony() {
  if command -v dfx >/dev/null 2>&1; then
    log_detail "dfx already installed ($(dfx --version 2>&1 | head -1))"
    return 0
  fi
  if install_dfx_local; then
    return 0
  fi
  local ver="${CEREMONY_DFX_VERSION}"
  local url="https://github.com/dfinity/sdk/releases/download/${ver}/dfx-${ver}-x86_64-linux.tar.gz"
  local tmp
  tmp="$(mktemp -d)"
  log "installing dfx ${ver} from network (HSM principal verification during provision-*)"
  curl -fsSL "${url}" | tar -xzf - -C "${tmp}"
  if [[ ! -f "${tmp}/dfx" ]]; then
    rm -rf "${tmp}"
    die "dfx tarball missing dfx binary (${url})"
  fi
  install -m 755 "${tmp}/dfx" /usr/local/bin/dfx
  rm -rf "${tmp}"
  command -v dfx >/dev/null 2>&1 || die "dfx install failed"
  log_detail "dfx installed at $(command -v dfx)"
}
