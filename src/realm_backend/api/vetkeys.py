"""VetKeys API — on-chain encryption key derivation for user private data.

Provides async helper functions that call the IC management canister's
vetKD (Verifiably Encrypted Threshold Key Derivation) API.

The flow:
  1. Frontend calls ``get_vetkey_public_key`` to obtain the IBE public key.
  2. Frontend generates an ephemeral ``TransportSecretKey`` (BLS12-381 G1).
  3. Frontend calls ``derive_vetkey`` with the transport public key.
  4. Canister proxies the call to the management canister; the derived key
     is encrypted under the transport public key so no single node sees it.
  5. Frontend decrypts → symmetric AES-GCM key → encrypts/decrypts private data.

Context construction:
  ``len(domain_sep) || domain_sep || caller_principal_str``
  This binds every derived key to *this application* and *this user*.
"""

from _cdk import Async, ic
from ic_python_logging import get_logger

logger = get_logger("api.vetkeys")

# Master key hosted on the IC vetKD subnet.
# "test_key_1" — 13-node test subnet (fuqsr).  Switch to "key_1" for
# production (34-node fiduciary subnet pzp6e).
VETKD_KEY_NAME = "test_key_1"

DOMAIN_SEPARATOR = b"realms"


def _build_context_hex(caller_principal_str: str) -> str:
    """Return the vetKD context as a hex string.

    Format: ``<1-byte len><domain_separator><scope>``
    where *scope* is the UTF-8 encoding of the caller's principal string.
    """
    ds = DOMAIN_SEPARATOR
    scope = caller_principal_str.encode()
    ctx = bytes([len(ds)]) + ds + scope
    return "".join(f"{b:02x}" for b in ctx)


def get_vetkey_public_key(caller_principal: str) -> Async[dict]:
    """Retrieve the vetKD public key for *caller_principal*'s context.

    Returns ``{"success": True, "public_key_hex": "..."}`` on success.
    """
    ctx_hex = _build_context_hex(caller_principal)
    logger.info(f"vetkd_public_key for {caller_principal} (ctx len={len(ctx_hex)//2})")

    args = ic.candid_encode(
        f'(record {{ canister_id = null; '
        f'context = blob "{ctx_hex}"; '
        f'key_id = record {{ curve = variant {{ bls12_381_g2 = null }}; '
        f'name = "{VETKD_KEY_NAME}" }} }})'
    )

    result = yield ic.call_raw("aaaaa-aa", "vetkd_public_key", args, 26_000_000_000)

    if hasattr(result, "Ok") and result.Ok is not None:
        decoded = ic.candid_decode(result.Ok)
        # decoded is a Candid record; convert the inner blob to hex
        pk_hex = _extract_blob_hex(decoded, "public_key")
        logger.info(f"vetkd_public_key OK (len={len(pk_hex)//2 if pk_hex else 0})")
        return {"success": True, "public_key_hex": pk_hex}
    else:
        err = str(getattr(result, "Err", result))
        logger.error(f"vetkd_public_key failed: {err}")
        return {"success": False, "error": err}


def derive_vetkey(
    caller_principal: str,
    transport_public_key_hex: str,
    input_hex: str = "",
) -> Async[dict]:
    """Derive an encrypted vetKey for *caller_principal*.

    The management canister encrypts the derived key under the caller's
    *transport_public_key* so the plaintext key never leaves the subnet.

    Returns ``{"success": True, "encrypted_key_hex": "..."}`` on success.
    """
    ctx_hex = _build_context_hex(caller_principal)
    tpk_hex = transport_public_key_hex.strip()
    inp_hex = input_hex.strip() if input_hex else ""

    logger.info(
        f"vetkd_derive_key for {caller_principal} "
        f"(ctx={len(ctx_hex)//2}B, tpk={len(tpk_hex)//2}B, input={len(inp_hex)//2}B)"
    )

    args = ic.candid_encode(
        f'(record {{ '
        f'input = blob "{inp_hex}"; '
        f'context = blob "{ctx_hex}"; '
        f'key_id = record {{ curve = variant {{ bls12_381_g2 = null }}; '
        f'name = "{VETKD_KEY_NAME}" }}; '
        f'transport_public_key = blob "{tpk_hex}" }})'
    )

    result = yield ic.call_raw("aaaaa-aa", "vetkd_derive_key", args, 54_000_000_000)

    if hasattr(result, "Ok") and result.Ok is not None:
        decoded = ic.candid_decode(result.Ok)
        ek_hex = _extract_blob_hex(decoded, "encrypted_key")
        logger.info(f"vetkd_derive_key OK (len={len(ek_hex)//2 if ek_hex else 0})")
        return {"success": True, "encrypted_key_hex": ek_hex}
    else:
        err = str(getattr(result, "Err", result))
        logger.error(f"vetkd_derive_key failed: {err}")
        return {"success": False, "error": err}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_blob_hex(decoded, field_name: str) -> str:
    """Best-effort extraction of a blob field from a Candid-decoded value.

    ``ic.candid_decode`` may return a dict, a record object, or a string
    representation.  We try dict access first, then attribute access, and
    finally fall back to returning the whole thing as a string so the
    caller can still forward it to the frontend.
    """
    # Dict-like (most common inside canister)
    if isinstance(decoded, dict) and field_name in decoded:
        raw = decoded[field_name]
        if isinstance(raw, (bytes, bytearray)):
            return raw.hex()
        return str(raw)

    # Attribute access
    raw = getattr(decoded, field_name, None)
    if raw is not None:
        if isinstance(raw, (bytes, bytearray)):
            return raw.hex()
        return str(raw)

    # Fallback — return string repr
    return str(decoded)
