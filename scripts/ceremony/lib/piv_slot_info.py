#!/usr/bin/env python3
"""Report PIV slot metadata (and the slot's public key) as JSON.

The ykman 4.x CLI cannot show slot policies -- `ykman piv info` omits slots and
`ykman piv keys info` does not exist -- so read them through the library, which
also hands back the public key without needing the PIN or a touch.

Usage: piv_slot_info.py [SLOT] [KEY_TYPE]   (default slot 9c, ECCP256)
"""
import json
import logging
import sys

# ykman logs a full PC/SC traceback when no reader is present; the caller gets a
# clean JSON error instead.
logging.disable(logging.CRITICAL)

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from ykman.device import list_all_devices
    from yubikit.core.smartcard import ApduError, SmartCardConnection
    from yubikit.piv import KEY_TYPE, PivSession, SLOT
except ImportError as exc:  # pragma: no cover - depends on host packages
    print(json.dumps({"error": f"missing python yubikey/cryptography libs: {exc}"}))
    sys.exit(2)


def probe_key_present(piv, slot, key_type) -> dict:
    """Ask for a signature with no PIN verified, and read the status word.

    Pre-5.3 firmware reports no slot metadata, so this is the only way to tell
    an empty slot from a populated one without knowing the PIN. The card checks
    authentication before touch, so this returns immediately and consumes no
    PIN retry.
    """
    try:
        piv.sign(slot, key_type, b"realms-probe", hashes.SHA256())
        return {"key_present": True, "probe": "signed without PIN"}
    except ApduError as exc:
        sw = exc.sw
        if sw == 0x6982:  # security status not satisfied -> key is there
            return {"key_present": True, "probe": "SW=0x6982 (PIN required)"}
        if sw in (0x6A88, 0x6A82):  # referenced data / file not found
            return {"key_present": False, "probe": f"SW=0x{sw:04x} (no key in slot)"}
        return {"probe": f"SW=0x{sw:04x}"}
    except Exception as exc:  # noqa: BLE001
        return {"probe": f"{type(exc).__name__}: {exc}"}


def enum_name(value) -> str:
    return getattr(value, "name", str(value))


def main() -> int:
    slot_arg = (sys.argv[1] if len(sys.argv) > 1 else "9c").lower().lstrip("0x")
    slot = {"9a": SLOT.AUTHENTICATION, "9c": SLOT.SIGNATURE,
            "9d": SLOT.KEY_MANAGEMENT, "9e": SLOT.CARD_AUTH}.get(slot_arg)
    if slot is None:
        print(json.dumps({"error": f"unsupported slot {slot_arg}"}))
        return 2
    key_type_arg = (sys.argv[2] if len(sys.argv) > 2 else "ECCP256").upper()
    try:
        key_type = KEY_TYPE[key_type_arg]
    except KeyError:
        print(json.dumps({"error": f"unsupported key type {key_type_arg}"}))
        return 2

    try:
        found = list_all_devices()
    except Exception as exc:  # noqa: BLE001 - no PC/SC service, no reader, etc.
        print(json.dumps({"error": f"cannot enumerate YubiKeys: {exc}"}))
        return 1

    devices = []
    for dev, info in found:
        entry = {
            "serial": info.serial,
            "firmware": ".".join(str(p) for p in tuple(info.version)),
        }
        try:
            with dev.open_connection(SmartCardConnection) as conn:
                piv = PivSession(conn)
                # ykcs11 (dfx --hsm / icp) only sees a slot that holds a
                # certificate, so report it even when metadata is unavailable.
                try:
                    cert = piv.get_certificate(slot)
                    entry["has_certificate"] = True
                    entry["cert_subject"] = cert.subject.rfc4514_string()
                except Exception:  # noqa: BLE001 - absent cert is not an error
                    entry["has_certificate"] = False
                try:
                    md = piv.get_slot_metadata(slot)
                except Exception:
                    # No metadata (firmware < 5.3): fall back to a probe so the
                    # caller can still tell whether the slot holds a key.
                    entry.update(probe_key_present(piv, slot, key_type))
                    raise
                # Attribute set varies across ykman releases; report what exists.
                for field in ("key_type", "pin_policy", "touch_policy", "origin"):
                    if hasattr(md, field):
                        entry[field] = enum_name(getattr(md, field))
                if getattr(md, "public_key", None) is not None:
                    entry["public_key_pem"] = md.public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    ).decode()
        except Exception as exc:  # noqa: BLE001 - surface any card error verbatim
            entry["error"] = f"{type(exc).__name__}: {exc}"
        devices.append(entry)

    if not devices:
        print(json.dumps({"error": "no YubiKey detected"}))
        return 1
    print(json.dumps({"slot": slot_arg, "devices": devices}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
