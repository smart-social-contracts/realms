#!/usr/bin/env python3
"""Bootstrap SSH on Ubuntu 22.04 Desktop live via serial console (cloud-init unavailable)."""
from __future__ import annotations

import argparse
import socket
import sys
import time

PROMPT = "ubuntu@ubuntu:"


def log(msg: str) -> None:
    print(f"[serial-bootstrap] {msg}", file=sys.stderr, flush=True)


def connect_serial(host: str, port: int, retries: int = 120) -> socket.socket:
    for _ in range(retries):
        try:
            sock = socket.create_connection((host, port), timeout=2)
            sock.settimeout(2.0)
            log(f"connected to serial {host}:{port}")
            return sock
        except OSError:
            time.sleep(1)
    raise SystemExit(f"could not connect to serial {host}:{port} after {retries}s")


def read_for(sock: socket.socket, timeout: float) -> str:
    buf = ""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            continue
        if not chunk:
            break
        buf += chunk.decode(errors="replace")
    return buf


def read_until(sock: socket.socket, markers: tuple[str, ...], timeout: float) -> str:
    buf = ""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            continue
        if not chunk:
            break
        buf += chunk.decode(errors="replace")
        for marker in markers:
            if marker in buf:
                return buf
    return buf


def send_line(sock: socket.socket, line: str) -> None:
    sock.sendall((line + "\r").encode())


def run_cmd(sock: socket.socket, cmd: str, timeout: float = 120.0) -> str:
    send_line(sock, cmd)
    # Wait for shell prompt after command completes (not local echo of the command).
    time.sleep(0.2)
    out = ""
    deadline = time.time() + timeout
    while time.time() < deadline:
        chunk = read_for(sock, 2.0)
        if not chunk:
            continue
        out += chunk
        if PROMPT in out:
            # Require prompt near end of buffer to avoid matching mid-stream noise.
            tail = out[-200:]
            if tail.rstrip().endswith(PROMPT) or f"{PROMPT}~" in tail or f"{PROMPT}$" in tail:
                break
    return out


def login(sock: socket.socket) -> None:
    banner = read_until(sock, ("login:", "Login:"), 240)
    if "login:" not in banner.lower():
        log("login prompt not seen; tail:")
        print(banner[-2000:], file=sys.stderr)
        raise SystemExit("serial login prompt missing")

    log("logging in as ubuntu")
    send_line(sock, "ubuntu")
    tail = read_until(sock, ("Password:", PROMPT), 30)
    if "Password:" in tail:
        log("using empty password")
        send_line(sock, "")
        tail = read_until(sock, (PROMPT,), 30)

    if PROMPT not in tail:
        tail += read_for(sock, 5)
    if PROMPT not in tail:
        log("shell prompt missing after login; tail:")
        print(tail[-2000:], file=sys.stderr)
        raise SystemExit("serial login failed")


def upload_script(sock: socket.socket, path: str, script: str) -> None:
    log(f"uploading bootstrap script to {path}")
    run_cmd(sock, f"rm -f {path}", timeout=15)
    send_line(sock, f"cat > {path} <<'REALMS_BOOTSTRAP_EOF'")
    time.sleep(0.5)
    for line in script.splitlines():
        send_line(sock, line)
        time.sleep(0.05)
    send_line(sock, "REALMS_BOOTSTRAP_EOF")
    read_until(sock, (PROMPT,), 30)


def bootstrap(host: str, port: int, pubkey: str, boot_wait: float) -> None:
    if boot_wait > 0:
        log(f"waiting {boot_wait:.0f}s before serial connect")
        time.sleep(boot_wait)

    sock = connect_serial(host, port)
    login(sock)

    log("configuring DNS for QEMU user networking")
    run_cmd(sock, "sudo rm -f /etc/resolv.conf", timeout=15)
    run_cmd(sock, "echo nameserver 10.0.2.3 | sudo tee /etc/resolv.conf", timeout=15)
    resolve_check = run_cmd(sock, "getent hosts archive.ubuntu.com", timeout=30)
    if "archive.ubuntu.com" not in resolve_check:
        log("DNS check failed:")
        print(resolve_check[-800:], file=sys.stderr)
        raise SystemExit("guest DNS not working")

    script = f"""#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
rm -f /etc/resolv.conf
echo nameserver 10.0.2.3 > /etc/resolv.conf
apt-get update -y
apt-get install -y openssh-server
install -d -m 700 -o ubuntu -g ubuntu /home/ubuntu/.ssh
auth=/home/ubuntu/.ssh/authorized_keys
grep -qF '{pubkey}' "$auth" 2>/dev/null || echo '{pubkey}' >> "$auth"
chmod 600 "$auth"
chown ubuntu:ubuntu "$auth"
systemctl enable --now ssh
systemctl is-active --quiet ssh
touch /tmp/realms-bootstrap.done
"""
    upload_script(sock, "/tmp/realms-bootstrap.sh", script)
    log("running bootstrap script (apt + openssh; may take several minutes)")
    run_cmd(sock, "sudo bash /tmp/realms-bootstrap.sh", timeout=900)

    out = run_cmd(
        sock,
        "test -f /tmp/realms-bootstrap.done && echo READY; systemctl is-active ssh",
        timeout=30,
    )
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    if "READY" not in lines or "active" not in lines:
        log("bootstrap verification failed; tail:")
        print(out[-3000:], file=sys.stderr)
        raise SystemExit("serial bootstrap incomplete")
    log("serial bootstrap finished")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4445)
    parser.add_argument("--pubkey-file", required=True)
    parser.add_argument("--boot-wait", type=float, default=0.0)
    args = parser.parse_args()
    pubkey = open(args.pubkey_file, encoding="utf-8").read().strip()
    bootstrap(args.host, args.port, pubkey, args.boot_wait)


if __name__ == "__main__":
    main()
