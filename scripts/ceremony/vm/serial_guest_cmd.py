#!/usr/bin/env python3
"""Run shell commands on Ubuntu 22.04 Desktop live via serial console (ttyS0)."""
from __future__ import annotations

import argparse
import socket
import sys
import time

PROMPT = "ubuntu@ubuntu:"
PROMPT_MARKERS = (PROMPT, f"{PROMPT}~", f"{PROMPT}$")


def log(msg: str) -> None:
    print(f"[serial-guest] {msg}", file=sys.stderr, flush=True)


def stream_write(text: str) -> None:
    if text:
        sys.stdout.write(text)
        sys.stdout.flush()


def connect_serial(host: str, port: int, retries: int = 180) -> socket.socket:
    for attempt in range(1, retries + 1):
        try:
            sock = socket.create_connection((host, port), timeout=2)
            sock.settimeout(2.0)
            log(f"connected to serial {host}:{port}")
            return sock
        except OSError:
            if attempt % 15 == 0:
                log(f"still waiting for serial ({attempt}s)...")
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


def at_prompt(buf: str) -> bool:
    tail = buf[-320:]
    return any(marker in tail for marker in PROMPT_MARKERS) and (
        tail.rstrip().endswith(PROMPT)
        or f"{PROMPT}~" in tail[-40:]
        or f"{PROMPT}$" in tail[-40:]
    )


def wake_serial(sock: socket.socket, timeout: float = 20.0) -> str:
    log("waking serial console (press Enter until shell prompt)")
    buf = ""
    deadline = time.time() + timeout
    while time.time() < deadline:
        send_line(sock, "")
        chunk = read_for(sock, 1.0)
        if chunk:
            stream_write(chunk)
            buf += chunk
            if at_prompt(buf) or PROMPT in buf:
                log("shell prompt ready")
                return buf
        elif buf and at_prompt(buf):
            return buf
    raise SystemExit("serial shell prompt not available — is the VM running?")


def run_cmd(sock: socket.socket, cmd: str, timeout: float = 180.0) -> str:
    log(f"executing: {cmd}")
    send_line(sock, cmd)
    time.sleep(0.25)
    out = ""
    deadline = time.time() + timeout
    last_heartbeat = time.time()
    while time.time() < deadline:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            chunk = b""
        if chunk:
            text = chunk.decode(errors="replace")
            stream_write(text)
            out += text
            last_heartbeat = time.time()
            if at_prompt(out):
                break
        else:
            if time.time() - last_heartbeat >= 15:
                elapsed = int(time.time() - (deadline - timeout))
                log(f"... still running ({elapsed}s elapsed)")
                last_heartbeat = time.time()
            time.sleep(0.2)
            if out and at_prompt(out):
                break
    if not at_prompt(out):
        log(f"warning: command may still be running after {int(timeout)}s")
    return out


def login(sock: socket.socket) -> None:
    buf = wake_serial(sock)
    if at_prompt(buf) or PROMPT in buf:
        return
    if "login:" in buf.lower():
        log("logging in as ubuntu")
        send_line(sock, "ubuntu")
        tail = read_until(sock, ("Password:", PROMPT), 30)
        stream_write(tail)
        if "Password:" in tail:
            log("using empty password")
            send_line(sock, "")
            tail = read_until(sock, (PROMPT,), 30)
            stream_write(tail)
    if not at_prompt(buf):
        wake_serial(sock)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4445)
    parser.add_argument("--boot-wait", type=float, default=0.0)
    parser.add_argument(
        "--cmd",
        action="append",
        dest="commands",
        help="shell command to run (repeatable); default runs Option A (9p mount + ceremony terminal)",
    )
    args = parser.parse_args()

    commands = args.commands or [
        "sudo modprobe 9p 2>/dev/null; sudo modprobe 9pnet 2>/dev/null; sudo modprobe 9pnet_virtio 2>/dev/null; "
        "sudo mkdir -p /opt/realms-ceremony; "
        "sudo mount -t 9p -o trans=virtio,version=9p2000.L realms_ceremony /opt/realms-ceremony "
        "|| curl -fsSL http://10.0.2.2:8890/install-ceremony-update.sh | sudo bash -s 8890",
        "DISPLAY=:0 bash /opt/realms-ceremony/usb/launch-ceremony-terminal.sh",
    ]

    if args.boot_wait > 0:
        log(f"waiting {args.boot_wait:.0f}s before serial connect")
        time.sleep(args.boot_wait)

    sock = connect_serial(args.host, args.port)
    login(sock)

    for i, cmd in enumerate(commands, 1):
        log(f"step {i}/{len(commands)}")
        if "provision-prod" in cmd:
            timeout = 1800.0
        elif "install-dfx" in cmd or "mount" in cmd or "attach" in cmd:
            timeout = 300.0
        else:
            timeout = 120.0
        out = run_cmd(sock, cmd, timeout=timeout)
        if "mount:" in out and "failed" in out.lower():
            log("command may have failed; tail:")
            print(out[-2500:], file=sys.stderr)
            raise SystemExit(f"command failed: {cmd}")
        if "ERROR" in out and "attach-ceremony" in out:
            log("attach error; tail:")
            print(out[-2500:], file=sys.stderr)
            raise SystemExit(f"command failed: {cmd}")

    log("done")


if __name__ == "__main__":
    main()
