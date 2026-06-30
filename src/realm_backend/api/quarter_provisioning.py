"""Inter-canister transport for quarter auto-scaling (issue #156).

Two provisioning transports live here, both thin yield/generator wrappers
(mirroring ``api/cross_quarter.py``); the *decision* of whether to scale lives
in ``core.autoscale``:

1. **Direct (preferred).** The capital commands its own Casals stand, so it
   asks Casals to ``create_canister`` a backend-only quarter directly. Because
   Casals co-adds the stand commander (the capital) as a controller of canisters
   minted in its stand, the capital can then drive ``bootstrap_as_quarter`` on
   the fresh canister to bring it to parity (config + codex + extensions).
2. **Broker (legacy).** Ask a ``realm_installer`` to provision via Casals on the
   capital's behalf. Kept for realms wired with an installer broker.
"""

import json
from typing import Dict

from _cdk import Async, CallResult, Principal, Service, ic, service_update, text
from ic_python_logging import get_logger

logger = get_logger("api.quarter_provisioning")


def _unwrap_call_text(result) -> str:
    """Extract the text payload from an inter-canister ``CallResult``.

    Basilisk hands back a ``CallResult`` variant (``{Ok, Err}``); ``str(result)``
    yields its Python repr (``{'Ok': '...'}``), which is *not* valid JSON. Mirror
    the unwrap used in ``api/file_registry.py`` so callers can ``json.loads`` the
    actual canister response. A rejection (``Err``) is surfaced as a parseable
    ``{"err": ...}`` envelope.
    """
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("Ok", result.get("ok", str(result)))
    if hasattr(result, "Ok") and result.Ok is not None:
        return result.Ok
    if hasattr(result, "Err") and result.Err is not None:
        return json.dumps({"err": str(result.Err)})
    return str(result)


def parse_casals_spec(manifest_data: str, next_index: int) -> Dict:
    """Parse the ``casals`` provisioning block out of a realm's ``manifest_data``.

    Returns the spec dict consumed by ``process_quarter_scaling`` or ``None`` when
    the required ``stand``/``backend_wasm_key`` are missing. Pure + importable so
    it can be unit-tested without importing the canister ``main`` module.
    """
    try:
        manifest = json.loads(manifest_data or "{}")
    except Exception:
        manifest = {}
    cas = (manifest.get("casals") if isinstance(manifest, dict) else None) or {}
    stand = (cas.get("stand") or "").strip()
    backend_wasm_key = (cas.get("backend_wasm_key") or "").strip()
    if not stand or not backend_wasm_key:
        return None
    return {
        "stand": stand,
        "backend_wasm_key": backend_wasm_key,
        "name": f"{stand}-{next_index}",
        "casals_canister_id": (cas.get("casals_canister_id") or "").strip(),
        "registry_canister_id": (cas.get("registry_canister_id") or "").strip(),
        "codex": cas.get("codex") or None,
        "extensions": cas.get("extensions") or [],
        "frontend_canister_id": (cas.get("frontend_canister_id") or "").strip(),
    }


class InstallerProvisionService(Service):
    """Remote interface of the realm_installer ``provision_quarter`` broker."""

    @service_update
    def provision_quarter(self, args: text) -> text:
        ...


class CasalsProvisionService(Service):
    """Remote interface of the Casals orchestrator's ``create_canister``.

    Args (JSON): ``{stand, name, kind, wasm_key}``. Authorized for the stand's
    commander — which, for a capital provisioning its own quarters, is the
    capital's own backend canister.
    """

    @service_update
    def create_canister(self, args: text) -> text:
        ...


class QuarterBootstrapService(Service):
    """Remote interface of a freshly minted quarter's bootstrap entry point.

    Runs on the quarter (same realm-backend WASM); the capital may call it
    because Casals co-added the capital as a controller of the new canister.
    """

    @service_update
    def bootstrap_as_quarter(self, args: text) -> text:
        ...


def request_casals_create_canister(casals_canister_id: str, args: Dict) -> Async[Dict]:
    """Ask Casals to mint a backend-only quarter canister in the capital's stand.

    ``args`` is forwarded as JSON (``{stand, name, kind, wasm_key}``). Returns
    ``{"ok": True, "canister_id": ...}`` or ``{"ok": False, "error": ...}``.
    """
    logger.info(f"Requesting create_canister from Casals {casals_canister_id}: {args}")
    try:
        service = CasalsProvisionService(Principal.from_str(casals_canister_id))
        result: CallResult[text] = yield service.create_canister(json.dumps(args))
        raw = _unwrap_call_text(result)
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"ok": False, "error": f"Unparseable Casals response: {raw[:200]}"}
        # Casals replies {"ok": {...fields...}} on success, {"err": "..."} on error.
        if isinstance(parsed, dict) and parsed.get("ok") is not None and isinstance(parsed.get("ok"), dict):
            payload = parsed["ok"]
            return {"ok": True, "canister_id": (payload.get("canister_id") or "").strip(), "raw": payload}
        if isinstance(parsed, dict) and parsed.get("err") is not None:
            return {"ok": False, "error": str(parsed.get("err"))}
        # Some builds return a flat {canister_id: ...} or {success, ...}.
        cid = (parsed.get("canister_id") or "").strip() if isinstance(parsed, dict) else ""
        if cid:
            return {"ok": True, "canister_id": cid, "raw": parsed}
        return {"ok": False, "error": f"No canister_id in Casals response: {raw[:200]}"}
    except Exception as e:
        logger.error(f"Error calling Casals create_canister via {casals_canister_id}: {e}")
        return {"ok": False, "error": str(e)}


def bootstrap_quarter(quarter_canister_id: str, args: Dict) -> Async[Dict]:
    """Drive ``bootstrap_as_quarter`` on a freshly minted quarter canister.

    ``args`` is forwarded as JSON (parent realm id, registry id, optional codex
    and extension lists). Returns the parsed quarter response.
    """
    logger.info(f"Bootstrapping quarter {quarter_canister_id}: {args}")
    try:
        service = QuarterBootstrapService(Principal.from_str(quarter_canister_id))
        result: CallResult[text] = yield service.bootstrap_as_quarter(json.dumps(args))
        raw = _unwrap_call_text(result)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": f"Unparseable quarter response: {raw[:200]}"}
    except Exception as e:
        logger.error(f"Error bootstrapping quarter {quarter_canister_id}: {e}")
        return {"success": False, "error": str(e)}


def request_provision_quarter(installer_canister_id: str, args: Dict) -> Async[Dict]:
    """Ask the installer to provision a new backend-only quarter via Casals.

    ``args`` is forwarded as JSON (``{stand, backend_wasm_key, name?}``).
    Returns the parsed installer response, e.g. ``{"ok": True, "canister_id": ...}``
    or ``{"ok": False, "error": ...}``.
    """
    logger.info(f"Requesting quarter provisioning from installer {installer_canister_id}")
    try:
        service = InstallerProvisionService(Principal.from_str(installer_canister_id))
        result: CallResult[text] = yield service.provision_quarter(json.dumps(args))
        raw = _unwrap_call_text(result)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"ok": False, "error": f"Unparseable installer response: {raw[:200]}"}
    except Exception as e:
        logger.error(f"Error provisioning quarter via {installer_canister_id}: {e}")
        return {"ok": False, "error": str(e)}
