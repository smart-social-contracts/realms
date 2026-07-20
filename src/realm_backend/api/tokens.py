"""Realm treasury token and NFT canister resolution + Wallet registration."""

from typing import Optional

from _cdk import (
    CallResult,
    Opt,
    Principal,
    Record,
    Service,
    Variant,
    blob,
    nat,
    null,
    service_update,
    text,
)
from ic_python_logging import get_logger

logger = get_logger("api.tokens")


# Candid types for the realm token (fungible) canister's authority interface
# (ERC-3643-style: forced_transfer, freeze_account, unfreeze_account).
class TokenAccount(Record):
    owner: Principal
    subaccount: Opt[blob]


class ForcedTransferArgs(Record):
    from_: TokenAccount
    to: TokenAccount
    amount: nat
    memo: Opt[text]


class FreezeAccountArgs(Record):
    account: TokenAccount
    reason: Opt[text]


class TokenAuthorityError(Variant, total=False):
    Unauthorized: null
    InsufficientBalance: null
    InvalidRecipient: null
    GenericError: text


class TokenAuthorityResult(Variant, total=False):
    Ok: nat
    Err: TokenAuthorityError


_TOKEN_ACCOUNT_TYPE = "record { owner : principal; subaccount : opt blob }"
_FORCED_TRANSFER_ARG_TYPE = (
    f"record {{ from : {_TOKEN_ACCOUNT_TYPE}; to : {_TOKEN_ACCOUNT_TYPE}; "
    "amount : nat; memo : opt text }"
)
_FREEZE_ACCOUNT_ARG_TYPE = f"record {{ account : {_TOKEN_ACCOUNT_TYPE}; reason : opt text }}"
_TOKEN_AUTHORITY_RESULT_TYPE = (
    "variant { Ok : nat; "
    "Err : variant { Unauthorized : null; InsufficientBalance : null; "
    "InvalidRecipient : null; GenericError : text } }"
)


class TokenAuthorityService(Service):
    _arg_types = {
        "forced_transfer": _FORCED_TRANSFER_ARG_TYPE,
        "freeze_account": _FREEZE_ACCOUNT_ARG_TYPE,
        "unfreeze_account": _TOKEN_ACCOUNT_TYPE,
    }
    _return_types = {
        "forced_transfer": _TOKEN_AUTHORITY_RESULT_TYPE,
        "freeze_account": _TOKEN_AUTHORITY_RESULT_TYPE,
        "unfreeze_account": _TOKEN_AUTHORITY_RESULT_TYPE,
    }

    @service_update
    def forced_transfer(self, args: ForcedTransferArgs) -> TokenAuthorityResult:
        ...

    @service_update
    def freeze_account(self, args: FreezeAccountArgs) -> TokenAuthorityResult:
        ...

    @service_update
    def unfreeze_account(self, account: TokenAccount) -> TokenAuthorityResult:
        ...


def _token_authority_error_message(error) -> str:
    if error is None:
        return "Token authority operation failed"

    def _has(key):
        if isinstance(error, dict):
            return key in error
        return hasattr(error, key)

    if _has("Unauthorized"):
        return (
            "Realm is not the ledger authority for this token — it must be the "
            "token canister's authority (or a controller)"
        )
    if _has("InsufficientBalance"):
        return "Source account has insufficient balance"
    if _has("InvalidRecipient"):
        return "Source and destination accounts are the same"
    if _has("GenericError"):
        ge = error["GenericError"] if isinstance(error, dict) else error.GenericError
        return str(ge)
    return str(error)


def _unwrap_token_authority_result(result) -> dict:
    """Unwrap a CallResult[TokenAuthorityResult] from the typed service call."""
    outer_err = None
    if isinstance(result, dict):
        outer_err = result.get("Err")
    elif hasattr(result, "Err"):
        outer_err = result.Err
    if outer_err is not None:
        logger.error(f"Inter-canister token authority call failed: {outer_err}")
        return {"success": False, "error": f"Call failed: {outer_err}"}

    inner = None
    if isinstance(result, dict):
        inner = result.get("Ok")
    elif hasattr(result, "Ok"):
        inner = result.Ok
    if inner is None:
        logger.error(f"Unexpected token authority response (Ok is None): {result}")
        return {"success": False, "error": "Unexpected empty response from token canister"}

    if isinstance(inner, dict):
        if "Ok" in inner:
            return {"success": True, "block_index": str(inner["Ok"])}
        if "Err" in inner:
            return {"success": False, "error": _token_authority_error_message(inner["Err"])}
    elif hasattr(inner, "Ok"):
        return {"success": True, "block_index": str(inner.Ok)}
    elif hasattr(inner, "Err"):
        return {"success": False, "error": _token_authority_error_message(inner.Err)}

    logger.error(f"Unexpected inner token authority result: {inner}")
    return {"success": False, "error": f"Unexpected result from token canister: {inner}"}


def _token_account(principal_text: str) -> dict:
    return {"owner": Principal.from_str(principal_text), "subaccount": None}


def forced_transfer_tokens(
    ledger_canister_id: str,
    from_principal: str,
    to_principal: str,
    amount: int,
    memo: str = "",
):
    """Force-move tokens between two accounts via the realm's ledger authority."""
    logger.info(
        f"Forced token transfer: {from_principal} -> {to_principal}, "
        f"amount={amount}, memo={memo!r}"
    )
    try:
        args = {
            "from_": _token_account(from_principal),
            "to": _token_account(to_principal),
            "amount": amount,
            "memo": memo or None,
        }
        service = TokenAuthorityService(Principal.from_str(ledger_canister_id))
        result: CallResult[TokenAuthorityResult] = yield service.forced_transfer(args)
        logger.info(f"Token forced_transfer result: {result}")
        return _unwrap_token_authority_result(result)
    except Exception as e:
        logger.error(f"Error in forced token transfer: {e}")
        return {"success": False, "error": f"Failed to force-transfer tokens: {e}"}


def freeze_token_account_call(ledger_canister_id: str, principal_text: str, reason: str = ""):
    """Freeze a token account (blocks outgoing transfers) via the ledger authority."""
    logger.info(f"Freeze token account: {principal_text}, reason={reason!r}")
    try:
        args = {"account": _token_account(principal_text), "reason": reason or None}
        service = TokenAuthorityService(Principal.from_str(ledger_canister_id))
        result: CallResult[TokenAuthorityResult] = yield service.freeze_account(args)
        logger.info(f"Token freeze_account result: {result}")
        return _unwrap_token_authority_result(result)
    except Exception as e:
        logger.error(f"Error freezing token account: {e}")
        return {"success": False, "error": f"Failed to freeze account: {e}"}


def unfreeze_token_account_call(ledger_canister_id: str, principal_text: str):
    """Unfreeze a token account via the ledger authority."""
    logger.info(f"Unfreeze token account: {principal_text}")
    try:
        service = TokenAuthorityService(Principal.from_str(ledger_canister_id))
        result: CallResult[TokenAuthorityResult] = yield service.unfreeze_account(
            _token_account(principal_text)
        )
        logger.info(f"Token unfreeze_account result: {result}")
        return _unwrap_token_authority_result(result)
    except Exception as e:
        logger.error(f"Error unfreezing token account: {e}")
        return {"success": False, "error": f"Failed to unfreeze account: {e}"}


def _valid_canister_id(value: str) -> bool:
    value = (value or "").strip()
    if not value or not value.endswith("-cai"):
        return False
    parts = value.split("-")
    if len(parts) < 2:
        return False
    for part in parts[:-1]:
        if len(part) != 5 or not part.isalnum() or not part.islower():
            return False
    return True

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


def resolve_shared_token_by_ledger(ledger_canister_id: str, network: str = "") -> Optional[dict]:
    """Reverse lookup: ledger canister ID -> shared token metadata."""
    ledger = (ledger_canister_id or "").strip()
    if not ledger:
        return None
    net = (network or "").strip().lower()
    networks = [net] if net else list(_SHARED_TOKEN_LEDGERS.keys())
    for net_key in networks:
        net_map = _SHARED_TOKEN_LEDGERS.get(net_key, {})
        for sym, cfg in net_map.items():
            if (cfg.get("ledger") or "").strip() == ledger:
                out = dict(cfg)
                out["symbol"] = sym
                return out
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


def get_treasury_token_indexer(symbol: str = "", ledger_canister_id: str = "") -> str:
    """Return the registered indexer for the treasury token, else ledger ID."""
    sym = (symbol or "").strip()
    if sym:
        try:
            from ggg import Token

            token = Token[sym]
            if token:
                indexer = (getattr(token, "indexer", "") or "").strip()
                if indexer:
                    return indexer
        except Exception as e:
            logger.warning(f"Could not load Token[{sym}] indexer: {e}")
    ledger = (ledger_canister_id or "").strip()
    if ledger:
        realm = _realm_entity()
        network = getattr(realm, "network", "") if realm else ""
        shared = resolve_shared_token_by_ledger(ledger, network)
        if shared and shared.get("indexer"):
            return str(shared["indexer"])
    return ledger


def resolve_ledger_token_info_sync(ledger_canister_id: str, network: str = "") -> dict:
    """Resolve symbol/decimals/indexer from the shared registry (sync)."""
    ledger = (ledger_canister_id or "").strip()
    if not ledger:
        return {"success": False, "error": "ledger_canister_id is required"}
    if not _valid_canister_id(ledger):
        return {"success": False, "error": "Invalid ledger canister ID format"}

    shared = resolve_shared_token_by_ledger(ledger, network)
    if not shared:
        return {
            "success": False,
            "error": "Unknown ledger — not in shared token registry for this network",
        }

    symbol = (shared.get("symbol") or shared.get("name") or "TOKEN")[:16]
    decimals = int(shared.get("decimals", 8))
    indexer = (shared.get("indexer") or ledger).strip()
    return {
        "success": True,
        "ledger_canister_id": ledger,
        "symbol": symbol,
        "decimals": decimals,
        "indexer_canister_id": indexer,
        "source": "shared_registry",
    }


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
