#!/usr/bin/env python3
"""Derive an IC self-authenticating principal from a DER SPKI public key on stdin.

Offline by design: the ceremony runs airgapped, so principal derivation must not
depend on dfx, icp-cli, npm or any network install.
"""
import base64
import hashlib
import sys
import zlib


def principal_from_spki_der(der: bytes) -> str:
    blob = hashlib.sha224(der).digest() + b"\x02"
    checksum = zlib.crc32(blob).to_bytes(4, "big")
    text = base64.b32encode(checksum + blob).decode("ascii").lower().rstrip("=")
    return "-".join(text[i:i + 5] for i in range(0, len(text), 5))


def main() -> int:
    der = sys.stdin.buffer.read()
    if not der:
        print("empty DER public key on stdin", file=sys.stderr)
        return 1
    print(principal_from_spki_der(der))
    return 0


if __name__ == "__main__":
    sys.exit(main())
