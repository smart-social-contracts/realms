#!/usr/bin/env python3
"""Sign a message with the PIV slot private key (PIN on stdin).

Used to prove a pre-5.3 YubiKey holds the ceremony key: those cards cannot
report slot metadata or export a public key unless a certificate is present.

Usage: piv_sign.py SLOT MSG_PATH SIG_PATH [KEY_TYPE]   (default ECCP256)
"""
import logging
import sys

logging.disable(logging.CRITICAL)

try:
    from cryptography.hazmat.primitives import hashes
    from ykman.device import list_all_devices
    from yubikit.core.smartcard import SmartCardConnection
    from yubikit.piv import KEY_TYPE, SLOT, PivSession
except ImportError as exc:  # pragma: no cover
    sys.stderr.write(f"missing python yubikey/cryptography libs: {exc}\n")
    sys.exit(2)

SLOTS = {
    "9a": SLOT.AUTHENTICATION,
    "9c": SLOT.SIGNATURE,
    "9d": SLOT.KEY_MANAGEMENT,
    "9e": SLOT.CARD_AUTH,
}


def main() -> int:
    if len(sys.argv) not in (4, 5):
        sys.stderr.write(
            "usage: piv_sign.py SLOT MSG_PATH SIG_PATH [KEY_TYPE]  (PIN on stdin)\n"
        )
        return 2
    slot_arg = sys.argv[1].lower().lstrip("0x")
    slot = SLOTS.get(slot_arg)
    if slot is None:
        sys.stderr.write(f"unsupported slot {slot_arg}\n")
        return 2
    key_type_arg = (sys.argv[4] if len(sys.argv) == 5 else "ECCP256").upper()
    try:
        key_type = KEY_TYPE[key_type_arg]
    except KeyError:
        sys.stderr.write(f"unsupported key type {key_type_arg}\n")
        return 2
    pin = sys.stdin.read().strip()
    if not pin:
        sys.stderr.write("empty PIN\n")
        return 2
    message = open(sys.argv[2], "rb").read()

    try:
        found = list_all_devices()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"cannot enumerate YubiKeys: {exc}\n")
        return 1
    if len(found) != 1:
        sys.stderr.write(f"{len(found)} YubiKeys detected — insert exactly one\n")
        return 1

    dev, _info = found[0]
    try:
        with dev.open_connection(SmartCardConnection) as conn:
            piv = PivSession(conn)
            piv.verify_pin(pin)
            signature = piv.sign(slot, key_type, message, hashes.SHA256())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        return 1

    open(sys.argv[3], "wb").write(signature)
    return 0


if __name__ == "__main__":
    sys.exit(main())
