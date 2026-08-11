"""Embedded RealmsGOS env-services snapshots for on-chain resolution.

Casals maintains the source of truth under
``casals-config/realmsgos/env-services/{network}.json``. Realm backends run as
Basilisk WASM on the IC and cannot read that host filesystem, so this module
embeds JSON snapshots as Python constants.

Regenerate after editing the JSON files::

    python3 casals-config/realmsgos/scripts/sync_env_services_py.py
"""

from __future__ import annotations

from typing import Any, Optional

# fmt: off
# --- BEGIN GENERATED: env-services snapshots (do not edit by hand) ---
_ENV_SERVICES_SNAPSHOTS: dict[str, dict[str, Any]] = {
    "demo": {
        "casals_backend": "uvvmt-xaaaa-aaaae-agzta-cai",
        "casals_frontend": "usukh-2yaaa-aaaae-agztq-cai",
        "file_registry": "vi64l-3aaaa-aaaae-qj4va-cai",
        "file_registry_frontend": "7ja5c-dqaaa-aaaae-qj5oa-cai",
        "marketplace_backend": "ehyfg-wyaaa-aaaae-qg3qq-cai",
        "marketplace_frontend": "ulsvn-pyaaa-aaaae-qj4tq-cai",
        "multisig": "v72oj-vqaaa-aaaae-agzua-cai",
        "network": "demo",
        "nft_backend": "6hrip-iiaaa-aaaaf-qdoha-cai",
        "nft_frontend": "6aqo3-fqaaa-aaaaf-qdohq-cai",
        "token_backend": "xbkkh-syaaa-aaaah-qq3ya-cai",
        "token_frontend": "xglmt-7aaaa-aaaah-qq3yq-cai",
        "tokens": {
            "REALMS": {
                "ledger": "xbkkh-syaaa-aaaah-qq3ya-cai",
                "symbol": "REALMS"
            }
        }
    },
    "staging": {
        "casals_backend": "bjzut-ryaaa-aaaaj-a6uta-cai",
        "casals_frontend": "boysh-4aaaa-aaaaj-a6utq-cai",
        "file_registry": "iebdk-kqaaa-aaaau-agoxq-cai",
        "file_registry_frontend": "rbex3-xyaaa-aaaah-qumma-cai",
        "marketplace_backend": "jji3o-uyaaa-aaaah-qreja-cai",
        "marketplace_frontend": "joj52-zaaaa-aaaah-qrejq-cai",
        "multisig": "adwwj-tiaaa-aaaaj-a6uua-cai",
        "network": "staging",
        "nft_backend": "27sff-mqaaa-aaaah-quntq-cai",
        "nft_frontend": "3s4bl-dyaaa-aaaah-qunua-cai",
        "token_backend": "2rqin-xaaaa-aaaah-qunsq-cai",
        "token_frontend": "2ytdr-biaaa-aaaah-qunta-cai",
        "tokens": {
            "REALMS": {
                "ledger": "2rqin-xaaaa-aaaah-qunsq-cai",
                "symbol": "REALMS"
            }
        }
    },
    "test": {
        "casals_backend": "qugvi-7yaaa-aaaap-quwnq-cai",
        "casals_frontend": "qtht4-saaaa-aaaap-quwna-cai",
        "file_registry": "uq2mu-kaaaa-aaaah-avqcq-cai",
        "file_registry_frontend": "2no7h-xqaaa-aaaad-qlxeq-cai",
        "marketplace_backend": "2wldc-niaaa-aaaad-qlxga-cai",
        "marketplace_frontend": "mxyd5-3qaaa-aaaao-ba2xq-cai",
        "multisig": "qbbef-6qaaa-aaaap-quwoa-cai",
        "network": "test",
        "nft_backend": "eelas-yyaaa-aaaao-qps7a-cai",
        "nft_frontend": "ysrkl-eqaaa-aaaas-qgosa-cai",
        "token_backend": "nusyl-jiaaa-aaaae-qj6mq-cai",
        "token_frontend": "33mmr-pyaaa-aaaam-ai47q-cai",
        "tokens": {
            "REALMS": {
                "ledger": "nusyl-jiaaa-aaaae-qj6mq-cai",
                "symbol": "REALMS"
            }
        }
    }
}
# --- END GENERATED: env-services snapshots ---
# fmt: on

_SERVICE_KEY_ALIASES: dict[str, str] = {
    "casals": "casals_backend",
    "casals_backend": "casals_backend",
    "casals_frontend": "casals_frontend",
    "multisig": "multisig",
    "token": "token_backend",
    "token_backend": "token_backend",
    "token_frontend": "token_frontend",
    "nft": "nft_backend",
    "nft_backend": "nft_backend",
    "nft_frontend": "nft_frontend",
    "marketplace": "marketplace_backend",
    "marketplace_backend": "marketplace_backend",
    "marketplace_frontend": "marketplace_frontend",
    "file_registry": "file_registry",
    "file_registry_frontend": "file_registry_frontend",
}

# Defaults for tokens declared in env-services but without full ICRC metadata.
_TOKEN_DEFAULTS: dict[str, dict[str, Any]] = {
    "REALMS": {
        "decimals": 8,
        "name": "REALMS Token",
    },
}


def _normalize_network(network: str) -> str:
    return (network or "").strip().lower()


def load_env_services(network: str) -> dict[str, Any]:
    """Return the env-services snapshot for *network*.

    On canister WASM only the embedded snapshots are available. When running
    off-chain (e.g. unit tests), a host checkout may also read
    ``casals-config/realmsgos/env-services/<network>.json`` if present.
    """
    net = _normalize_network(network)
    if not net:
        raise ValueError("network is required")

    try:
        from pathlib import Path

        json_path = (
            Path(__file__).resolve().parents[3]
            / "casals-config"
            / "realmsgos"
            / "env-services"
            / f"{net}.json"
        )
        if json_path.is_file():
            import json

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
    except Exception:
        pass

    snapshot = _ENV_SERVICES_SNAPSHOTS.get(net)
    if snapshot is None:
        raise ValueError(f"Unknown env-services network: {net!r}")
    return dict(snapshot)


def resolve_env_service(network: str, key: str) -> str:
    """Resolve a shared infra canister ID (marketplace, file_registry, …)."""
    services = load_env_services(network)
    raw_key = (key or "").strip()
    if not raw_key:
        raise KeyError("key is required")
    env_key = _SERVICE_KEY_ALIASES.get(raw_key, raw_key)
    value = services.get(env_key)
    if value is None:
        raise KeyError(f"Unknown env service key: {raw_key!r}")
    text = str(value).strip()
    if not text or text.lower() == "none":
        raise ValueError(
            f"Env service {raw_key!r} is not configured for network {network!r}"
        )
    return text


def _token_entry(symbol: str, cfg: dict[str, Any], services: dict[str, Any]) -> dict[str, Any]:
    sym = (symbol or "").strip()
    ledger = (cfg.get("ledger") or services.get("token_backend") or "").strip()
    if not ledger:
        return {}
    defaults = _TOKEN_DEFAULTS.get(sym.upper(), {})
    indexer = (cfg.get("indexer") or defaults.get("indexer") or ledger).strip()
    decimals = int(cfg.get("decimals", defaults.get("decimals", 8)))
    name = (cfg.get("name") or defaults.get("name") or sym).strip()
    out = {
        "ledger": ledger,
        "indexer": indexer,
        "decimals": decimals,
        "name": name,
        "symbol": (cfg.get("symbol") or sym).strip(),
    }
    return out


def resolve_shared_token(symbol: str, network: str) -> Optional[dict[str, Any]]:
    """Resolve a shared token symbol from env-services snapshots."""
    sym = (symbol or "").strip()
    if not sym:
        return None
    try:
        services = load_env_services(network)
    except ValueError:
        return None

    tokens = services.get("tokens") or {}
    if not isinstance(tokens, dict):
        return None

    cfg = tokens.get(sym)
    if cfg is None:
        upper = sym.upper()
        for key, value in tokens.items():
            if str(key).upper() == upper:
                cfg = value
                sym = str(key)
                break
    if not isinstance(cfg, dict):
        return None

    out = _token_entry(sym, cfg, services)
    return out or None


def resolve_shared_token_by_ledger(
    ledger_canister_id: str, network: str = ""
) -> Optional[dict[str, Any]]:
    """Reverse lookup: ledger canister ID -> env-services token metadata."""
    ledger = (ledger_canister_id or "").strip()
    if not ledger:
        return None

    net = _normalize_network(network)
    networks = [net] if net else sorted(_ENV_SERVICES_SNAPSHOTS.keys())
    for net_key in networks:
        try:
            services = load_env_services(net_key)
        except ValueError:
            continue
        tokens = services.get("tokens") or {}
        if not isinstance(tokens, dict):
            continue
        for sym, cfg in tokens.items():
            if not isinstance(cfg, dict):
                continue
            if (cfg.get("ledger") or "").strip() == ledger:
                out = _token_entry(str(sym), cfg, services)
                return out or None
        if (services.get("token_backend") or "").strip() == ledger:
            for sym, cfg in tokens.items():
                if isinstance(cfg, dict):
                    out = _token_entry(str(sym), cfg, services)
                    if out:
                        return out
    return None
