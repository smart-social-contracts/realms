"""Marketplace singleton configuration.

Stores the file_registry canister id, the billing-service principal
allowed to call ``record_license_payment``, and license pricing.

All mutators are controller-only; the marketplace canister's
controller list is curated by Smart Social Contracts.
"""

from typing import Dict

from _cdk import ic
from core.models import MarketplaceConfigEntity
from ic_python_logging import get_logger

logger = get_logger("api.config")

CONFIG_ID = "config"

DEFAULT_LICENSE_PRICE_USD_CENTS = 9900             # $99.00 / year
DEFAULT_LICENSE_DURATION_SECONDS = 365 * 24 * 3600  # 1 year


def _is_controller() -> bool:
    try:
        return bool(ic.is_controller(ic.caller()))
    except Exception:
        return False


def _require_controller() -> Dict:
    if not _is_controller():
        return {"success": False, "error": "Unauthorized: controller-only"}
    return {"success": True}


def _ensure_config() -> MarketplaceConfigEntity:
    cfg = MarketplaceConfigEntity[CONFIG_ID]
    if cfg is None:
        cfg = MarketplaceConfigEntity(
            id=CONFIG_ID,
            file_registry_canister_id="",
            billing_service_principal="",
            license_price_usd_cents=DEFAULT_LICENSE_PRICE_USD_CENTS,
            license_duration_seconds=DEFAULT_LICENSE_DURATION_SECONDS,
        )
    return cfg


def get_config() -> Dict:
    cfg = _ensure_config()
    return {
        "success": True,
        "config": {
            "file_registry_canister_id": cfg.file_registry_canister_id or "",
            "billing_service_principal": cfg.billing_service_principal or "",
            "license_price_usd_cents": int(cfg.license_price_usd_cents or DEFAULT_LICENSE_PRICE_USD_CENTS),
            "license_duration_seconds": int(cfg.license_duration_seconds or DEFAULT_LICENSE_DURATION_SECONDS),
        },
    }


def get_file_registry_canister_id() -> str:
    cfg = _ensure_config()
    return cfg.file_registry_canister_id or ""


def set_file_registry_canister_id(canister_id: str) -> Dict:
    err = _require_controller()
    if not err["success"]:
        return err
    cfg = _ensure_config()
    cfg.file_registry_canister_id = canister_id.strip()
    logger.info(f"set_file_registry_canister_id -> {cfg.file_registry_canister_id!r}")
    return {"success": True, "file_registry_canister_id": cfg.file_registry_canister_id}


def get_billing_service_principal() -> str:
    cfg = _ensure_config()
    return cfg.billing_service_principal or ""


def set_billing_service_principal(principal: str) -> Dict:
    err = _require_controller()
    if not err["success"]:
        return err
    cfg = _ensure_config()
    cfg.billing_service_principal = principal.strip()
    logger.info(f"set_billing_service_principal -> {cfg.billing_service_principal!r}")
    return {"success": True, "billing_service_principal": cfg.billing_service_principal}


def get_license_pricing() -> Dict:
    cfg = _ensure_config()
    return {
        "success": True,
        "pricing": {
            "license_price_usd_cents": int(cfg.license_price_usd_cents or DEFAULT_LICENSE_PRICE_USD_CENTS),
            "license_duration_seconds": int(cfg.license_duration_seconds or DEFAULT_LICENSE_DURATION_SECONDS),
        },
    }


def set_license_pricing(usd_cents: int, duration_seconds: int) -> Dict:
    err = _require_controller()
    if not err["success"]:
        return err
    if usd_cents <= 0 or duration_seconds <= 0:
        return {"success": False, "error": "pricing values must be positive"}
    cfg = _ensure_config()
    cfg.license_price_usd_cents = int(usd_cents)
    cfg.license_duration_seconds = int(duration_seconds)
    logger.info(
        f"set_license_pricing -> {cfg.license_price_usd_cents} cents / {cfg.license_duration_seconds}s"
    )
    return {
        "success": True,
        "license_price_usd_cents": cfg.license_price_usd_cents,
        "license_duration_seconds": cfg.license_duration_seconds,
    }


def init_config_from_args(file_registry_canister_id: str, billing_service_principal: str) -> None:
    """Best-effort initialisation called from main.py on canister init.

    Empty strings leave the existing value untouched (so a re-deploy
    with no init args doesn't clobber the configured registry id).
    """
    cfg = _ensure_config()
    if file_registry_canister_id:
        cfg.file_registry_canister_id = file_registry_canister_id.strip()
        logger.info(f"init: file_registry_canister_id = {cfg.file_registry_canister_id!r}")
    if billing_service_principal:
        cfg.billing_service_principal = billing_service_principal.strip()
        logger.info(f"init: billing_service_principal = {cfg.billing_service_principal!r}")
    if not cfg.license_price_usd_cents:
        cfg.license_price_usd_cents = DEFAULT_LICENSE_PRICE_USD_CENTS
    if not cfg.license_duration_seconds:
        cfg.license_duration_seconds = DEFAULT_LICENSE_DURATION_SECONDS
