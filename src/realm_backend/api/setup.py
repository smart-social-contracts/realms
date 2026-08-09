"""In-realm setup wizard API (issue #8 / GaaS setup flow)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from _cdk import Async, CallResult, Principal, StableBTreeMap, ic
from ic_python_logging import get_logger

from api.file_registry import FileRegistryService, _unwrap_call_result
from core.setup import (
    get_realm_registry_canister_id,
    get_setup_config,
    get_setup_state_payload,
    is_setup_stage,
    notify_registry_setup_completed,
    require_setup_authorized,
    update_setup_config,
    validate_branding_payload,
)
from ggg.governance.realm import RealmStatus

logger = get_logger("api.setup")

# Durable catalog cache (separate from Realm.manifest_data, which is capped at
# 4096 chars). memory_id=2 avoids colliding with ic_python_db storage (id=1).
_SETUP_CATALOG_CACHE = StableBTreeMap[str, str](
    memory_id=2, max_key_size=64, max_value_size=262_144
)
_SETUP_CATALOG_CACHE_KEY = "catalog"


def _read_catalog_cache() -> Optional[Dict[str, Any]]:
    raw = _SETUP_CATALOG_CACHE.get(_SETUP_CATALOG_CACHE_KEY)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_catalog_cache(envelope: Dict[str, Any]) -> None:
    payload = dict(envelope)
    payload["fetched_at"] = ic.time()
    _SETUP_CATALOG_CACHE.insert(_SETUP_CATALOG_CACHE_KEY, json.dumps(payload))


def get_available_codices_cached() -> str:
    cached = _read_catalog_cache()
    if not cached or not cached.get("codices"):
        return json.dumps({"success": False, "error": "empty"})
    return json.dumps({"success": True, "codices": cached.get("codices") or []})


def get_setup_state() -> str:
    return json.dumps(get_setup_state_payload())


def list_available_codices() -> Async[str]:
    from ggg import Realm

    realm = Realm.load("1")
    if not realm:
        return json.dumps({"success": False, "error": "Realm not found"})

    registry_id = (getattr(realm, "file_registry_canister_id", "") or "").strip()
    if not registry_id:
        return json.dumps(
            {"success": False, "error": "file_registry_canister_id not configured"}
        )

    registry = FileRegistryService(Principal.from_str(registry_id))
    codex_res: CallResult = yield registry.list_codices()
    raw = _unwrap_call_result(codex_res)
    entries = json.loads(raw) if raw else []

    catalog = []
    for entry in entries:
        codex_id = entry.get("codex_id") or entry.get("id") or ""
        if not codex_id:
            continue
        versions = entry.get("versions") or []
        name = codex_id
        description = ""
        latest = entry.get("latest") or (versions[-1] if versions else "")
        if latest:
            try:
                manifest_res: CallResult = yield registry.get_extension_manifest(
                    json.dumps({"ext_id": codex_id, "version": latest})
                )
                manifest = json.loads(_unwrap_call_result(manifest_res))
                if isinstance(manifest, dict) and not manifest.get("error"):
                    name = manifest.get("name") or name
                    description = manifest.get("description") or ""
            except Exception as manifest_err:
                logger.debug(
                    "Could not load manifest for codex %s@%s: %s",
                    codex_id,
                    latest,
                    manifest_err,
                )
        catalog.append(
            {
                "id": codex_id,
                "versions": versions,
                "name": name,
                "description": description,
            }
        )

    envelope = {"success": True, "codices": catalog}
    _write_catalog_cache(envelope)
    return json.dumps(envelope)


def setup_install_codex(args_json: str) -> Async[str]:
    auth_err = require_setup_authorized()
    if auth_err:
        return json.dumps(auth_err)

    try:
        params = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid JSON"})

    package = (params.get("package") or params.get("codex_id") or "").strip()
    version = params.get("version")
    if version is not None:
        version = str(version).strip() or None
    extra_params = params.get("params")

    if not package:
        return json.dumps({"success": False, "error": "package is required"})

    from ggg import Realm

    realm = Realm.load("1")
    if not realm:
        return json.dumps({"success": False, "error": "Realm not found"})

    registry_id = (getattr(realm, "file_registry_canister_id", "") or "").strip()
    if not registry_id:
        return json.dumps(
            {"success": False, "error": "file_registry_canister_id not configured"}
        )

    from api.file_registry import install_codex_from_registry as _install

    frontend_id = (getattr(realm, "frontend_canister_id", "") or "").strip() or None
    result_raw = yield from _install(
        registry_id,
        package,
        version,
        True,
        frontend_canister_id=frontend_id,
    )
    try:
        result = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Unexpected install response"})

    if not result.get("success"):
        return json.dumps(result)

    resolved_version = (result.get("version") or version or "").strip()
    codex_record: Dict[str, Any] = {
        "package": package,
        "version": resolved_version,
    }
    if isinstance(extra_params, dict) and extra_params:
        codex_record["params"] = extra_params

    update_setup_config(realm, {"codex": codex_record})
    result["setup_codex"] = codex_record
    return json.dumps(result)


def setup_configure_token(args_json: str) -> str:
    auth_err = require_setup_authorized()
    if auth_err:
        return json.dumps(auth_err)

    try:
        params = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid JSON"})

    token_canister_id = (params.get("token_canister_id") or "").strip()
    if not token_canister_id:
        return json.dumps({"success": False, "error": "token_canister_id is required"})

    # TODO(setup-wizard): support provisioning a new token canister from the wizard.
    token_record = {
        "token_canister_id": token_canister_id,
        "symbol": (params.get("symbol") or "").strip(),
        "decimals": params.get("decimals"),
        "indexer_canister_id": (params.get("indexer_canister_id") or "").strip(),
        "token_type": (params.get("token_type") or "realm").strip() or "realm",
    }

    from ggg import Realm

    realm = Realm.load("1")
    if not realm:
        return json.dumps({"success": False, "error": "Realm not found"})

    realm.token_canister_id = token_canister_id
    update_setup_config(realm, {"token": token_record})

    if token_canister_id:
        try:
            from api.tokens import register_treasury_token

            sym = token_record["symbol"] or getattr(realm, "accounting_currency", "") or "REALMS"
            indexer = token_record["indexer_canister_id"] or token_canister_id
            decimals = int(token_record["decimals"] if token_record["decimals"] is not None else getattr(realm, "accounting_currency_decimals", 8) or 8)
            register_treasury_token(
                symbol=sym,
                ledger_canister_id=token_canister_id,
                indexer_canister_id=indexer,
                decimals=decimals,
                token_type=token_record["token_type"],
            )
        except Exception as token_err:
            logger.warning("setup_configure_token treasury registration failed: %s", token_err)

    return json.dumps({"success": True, "token": token_record})


def setup_set_branding(args_json: str) -> str:
    auth_err = require_setup_authorized()
    if auth_err:
        return json.dumps(auth_err)

    try:
        params = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError:
        return json.dumps({"success": False, "error": "Invalid JSON"})

    branding = {
        key: params[key]
        for key in ("logo_data_url", "background_data_url", "colors")
        if key in params
    }
    if not branding:
        return json.dumps({"success": False, "error": "No branding fields provided"})

    branding_err = validate_branding_payload(branding)
    if branding_err:
        return json.dumps({"success": False, "error": branding_err})

    from ggg import Realm

    realm = Realm.load("1")
    if not realm:
        return json.dumps({"success": False, "error": "Realm not found"})

    existing = get_setup_config(realm).get("branding") or {}
    if isinstance(existing, dict):
        merged = dict(existing)
        merged.update(branding)
    else:
        merged = branding

    update_setup_config(realm, {"branding": merged})
    return json.dumps({"success": True, "branding": merged})


def complete_setup() -> Async[str]:
    auth_err = require_setup_authorized()
    if auth_err:
        return json.dumps(auth_err)

    from ggg import Realm

    realm = Realm.load("1")
    if not realm:
        return json.dumps({"success": False, "error": "Realm not found"})

    if not is_setup_stage(realm):
        return json.dumps(
            {"success": False, "error": "Realm is not in setup stage"}
        )

    setup = get_setup_config(realm)
    codex = setup.get("codex")
    if not isinstance(codex, dict) or not (codex.get("package") or codex.get("version")):
        return json.dumps({"success": False, "error": "A codex must be installed before completing setup"})

    completed_at = str(ic.time())
    update_setup_config(
        realm,
        {
            "setup_completed_at": completed_at,
            "codex": codex,
        },
    )
    realm.status = RealmStatus.ALPHA

    registry_id = get_realm_registry_canister_id(realm)
    if registry_id:
        yield from notify_registry_setup_completed(registry_id)
    else:
        logger.warning(
            "complete_setup: no realm_registry_canister_id configured; skipping registry notify"
        )

    return json.dumps(
        {
            "success": True,
            "status": RealmStatus.ALPHA,
            "setup_completed_at": completed_at,
            "codex": codex,
            "registry_notified": bool(registry_id),
        }
    )
