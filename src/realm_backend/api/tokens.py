"""Realm treasury token and NFT canister resolution + Wallet registration."""

from typing import Optional

from ic_python_logging import get_logger

logger = get_logger("api.tokens")

# Shared ledger IDs per network (mirrors canister_ids.json + well-known IC tokens).
_SHARED_TOKEN_LEDGERS = {
    "staging": {
        "REALMS": {
            "ledger": "2rqin-xaaaa-aaaah-qunsq-cai",
            "indexer": "2rqin-xaaaa-aaaah-qunsq-cai",
            "decimals": 8,
            "name": "REALMS Token",
        },
        "ckBTC": {
            "ledger": "mxzaz-hqaaa-aaaar-qaada-cai",
            "indexer": "n5wcd-faaaa-aaaar-qaaea-cai",
            "decimals": 8,
            "name": "ckBTC",
        },
        "ckUSDC": {
            "ledger": "xckus-ciaaa-aaaam-qbssa-cai",
            "indexer": "ufqgi-4qaaa-aaaam-qbsna-cai",
            "decimals": 6,
            "name": "ckUSDC",
        },
    },
    "demo": {
        "REALMS": {
            "ledger": "xbkkh-syaaa-aaaah-qq3ya-cai",
            "indexer": "xbkkh-syaaa-aaaah-qq3ya-cai",
            "decimals": 8,
            "name": "REALMS Token",
        },
        "ckBTC": {
            "ledger": "mxzaz-hqaaa-aaaar-qaada-cai",
            "indexer": "n5wcd-faaaa-aaaar-qaaea-cai",
            "decimals": 8,
            "name": "ckBTC",
        },
        "ckUSDC": {
            "ledger": "xckus-ciaaa-aaaam-qbssa-cai",
            "indexer": "ufqgi-4qaaa-aaaam-qbsna-cai",
            "decimals": 6,
            "name": "ckUSDC",
        },
    },
    "test": {
        "REALMS": {
            "ledger": "nusyl-jiaaa-aaaae-qj6mq-cai",
            "indexer": "nusyl-jiaaa-aaaae-qj6mq-cai",
            "decimals": 8,
            "name": "REALMS Token",
        },
        "ckBTC": {
            "ledger": "mxzaz-hqaaa-aaaar-qaada-cai",
            "indexer": "n5wcd-faaaa-aaaar-qaaea-cai",
            "decimals": 8,
            "name": "ckBTC",
        },
        "ckUSDC": {
            "ledger": "xckus-ciaaa-aaaam-qbssa-cai",
            "indexer": "ufqgi-4qaaa-aaaam-qbsna-cai",
            "decimals": 6,
            "name": "ckUSDC",
        },
    },
}


def _realm_entity():
    try:
        from ggg import Realm

        return Realm.load("1")
    except Exception as e:
        logger.warning(f"Could not load Realm entity: {e}")
        return None


def get_token_canister_id() -> Optional[str]:
    """Return the realm treasury token ledger ID (entity first, then static config)."""
    realm = _realm_entity()
    if realm:
        token_id = (getattr(realm, "token_canister_id", "") or "").strip()
        if token_id:
            return token_id
    try:
        from config import CANISTER_IDS

        for key in ("token_backend", "realm_token_ledger"):
            value = (CANISTER_IDS.get(key) or "").strip()
            if value:
                return value
    except Exception as e:
        logger.warning(f"Could not get token canister ID from config: {e}")
    return None


def get_nft_canister_id() -> Optional[str]:
    """Return the realm land NFT canister ID (entity first, then static config)."""
    realm = _realm_entity()
    if realm:
        nft_id = (getattr(realm, "nft_canister_id", "") or "").strip()
        if nft_id:
            return nft_id
    try:
        from config import CANISTER_IDS

        value = (CANISTER_IDS.get("nft_backend") or "").strip()
        if value:
            return value
    except Exception as e:
        logger.warning(f"Could not get NFT canister ID from config: {e}")
    return None


def resolve_shared_token(symbol: str, network: str) -> Optional[dict]:
    """Resolve a shared token symbol to ledger metadata for a network."""
    sym = (symbol or "").strip()
    if not sym:
        return None
    net_map = _SHARED_TOKEN_LEDGERS.get((network or "").strip().lower(), {})
    if sym in net_map:
        return dict(net_map[sym])
    upper = sym.upper()
    for key, cfg in net_map.items():
        if key.upper() == upper:
            return dict(cfg)
    return None


def register_treasury_token(
    symbol: str,
    ledger_canister_id: str,
    indexer_canister_id: str = "",
    decimals: int = 8,
    token_type: str = "realm",
) -> None:
    """Register (or update) the realm treasury token in the Basilisk Wallet."""
    sym = (symbol or "").strip()
    ledger = (ledger_canister_id or "").strip()
    if not sym or not ledger:
        return
    indexer = (indexer_canister_id or ledger).strip()
    try:
        from ggg import Token

        existing = Token[sym]
        if existing:
            existing.ledger = ledger
            existing.indexer = indexer
            existing.decimals = int(decimals)
            existing.symbol = sym
            existing.token_type = token_type
            existing.enabled = "true"
            logger.info(f"Updated treasury token {sym} -> {ledger}")
            return
        token = Token(
            name=sym,
            ledger=ledger,
            indexer=indexer,
            decimals=int(decimals),
        )
        token.symbol = sym
        token.token_type = token_type
        token.enabled = "true"
        logger.info(f"Registered treasury token {sym} -> {ledger}")
    except Exception as e:
        logger.warning(f"Could not register treasury token {sym}: {e}")
