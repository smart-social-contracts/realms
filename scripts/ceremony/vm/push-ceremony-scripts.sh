#!/usr/bin/env bash
# Pack current ceremony sources and serve them to a running QEMU live session (host gateway 10.0.2.2).
# Started automatically by run-ubuntu-2204-vm-interactive.sh (--daemon).
# Fallback when virtio-9p is unavailable; attach-ceremony-from-host.sh tries 9p first.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CEREMONY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
STAGING="${SCRIPT_DIR}/cache/ceremony-push"
PORT="${CEREMONY_PUSH_PORT:-8890}"
PID_FILE="${SCRIPT_DIR}/cache/ceremony-push-http.pid"
DAEMON=0

log() { printf '[push-ceremony] %s\n' "$*" >&2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --daemon) DAEMON=1; shift ;;
    -h|--help)
      sed -n '2,6p' "$0"
      exit 0
      ;;
    *) shift ;;
  esac
done

cleanup() {
  if [[ -f "${PID_FILE}" ]]; then
    kill "$(cat "${PID_FILE}")" 2>/dev/null || true
    rm -f "${PID_FILE}"
  fi
}
if [[ "${DAEMON}" != "1" ]]; then
  trap cleanup EXIT
fi

rm -rf "${STAGING}"
mkdir -p "${STAGING}"

log "packing ${CEREMONY_DIR}"
tar -C "${CEREMONY_DIR}" \
  --exclude='./vm/cache' \
  --exclude='./vm/cache/*' \
  -czf "${STAGING}/realms-ceremony-update.tar.gz" .

cat > "${STAGING}/install-ceremony-update.sh" <<'INSTALL'
#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8890}"
BASE="http://10.0.2.2:${PORT}"
TMP="$(mktemp -d)"
curl -fsSL "${BASE}/realms-ceremony-update.tar.gz" -o "${TMP}/update.tar.gz"
install -d -m 755 /opt/realms-ceremony
tar -xzf "${TMP}/update.tar.gz" -C /opt/realms-ceremony
chmod +x /opt/realms-ceremony/realms-key-ceremony.sh \
  /opt/realms-ceremony/usb/*.sh \
  /opt/realms-ceremony/vm/*.sh 2>/dev/null || true
rm -rf "${TMP}"
echo "[install] OK: /opt/realms-ceremony updated"
INSTALL
chmod +x "${STAGING}/install-ceremony-update.sh"

cat > "${STAGING}/install-dfx.sh" <<'INSTALL_DFX'
#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8890}"
BASE="http://10.0.2.2:${PORT}"
TMP="$(mktemp -d)"
curl -fsSL "${BASE}/dfx-x86_64-linux.tar.gz" -o "${TMP}/dfx.tgz"
tar -xzf "${TMP}/dfx.tgz" -C "${TMP}" dfx
install -m 755 "${TMP}/dfx" /usr/local/bin/dfx
rm -rf "${TMP}"
dfx --version
echo "[install-dfx] OK: $(command -v dfx)"
INSTALL_DFX
chmod +x "${STAGING}/install-dfx.sh"

DFX_CACHE="${SCRIPT_DIR}/cache/dfx-x86_64-linux.tar.gz"
if [[ ! -f "${DFX_CACHE}" ]]; then
  log "fetching dfx tarball for offline VM install (one-time)"
  curl -fsSL -o "${DFX_CACHE}.partial" \
    "https://github.com/dfinity/sdk/releases/download/0.24.3/dfx-0.24.3-x86_64-linux.tar.gz"
  mv "${DFX_CACHE}.partial" "${DFX_CACHE}"
fi
cp "${DFX_CACHE}" "${STAGING}/dfx-x86_64-linux.tar.gz"

if [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
  kill "$(cat "${PID_FILE}")" 2>/dev/null || true
fi
python3 -m http.server "${PORT}" --directory "${STAGING}" \
  >/dev/null 2>"${SCRIPT_DIR}/cache/ceremony-push-http.log" &
echo $! > "${PID_FILE}"

log "serving on http://10.0.2.2:${PORT}/ (HTTP fallback for attach-ceremony-from-host.sh)"

if [[ "${DAEMON}" == "1" ]]; then
  log "daemon mode — VM auto-attaches via virtio-9p; HTTP used if 9p fails"
  exit 0
fi

log "press Ctrl+C to stop"
wait "$(cat "${PID_FILE}")"
