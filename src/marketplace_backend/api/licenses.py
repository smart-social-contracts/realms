"""Developer licenses — paid annual badge that unlocks audit eligibility.

Anyone can publish without one. The license matters for **audit
eligibility**: only license-holders may call ``request_audit`` on
their listings, which surfaces them in the curator dashboard.

Payment flow (off-chain → canister):

  Developer browser ──▶ POST /marketplace/license/checkout (billing service)
                  ▶  redirect to Stripe Checkout
                       ▶ Stripe webhook ──▶ billing service
                                        ──▶ marketplace_backend.record_license_payment(...)

``record_license_payment`` is gated to either a controller or to the
``billing_service_principal`` configured via ``set_billing_service_principal``.
``grant_manual_license`` is a controller escape hatch for vouchers and
local development.
"""

from typing import Any, Dict

from _cdk import ic
from api.config import get_billing_service_principal
from core.models import DeveloperLicenseEntity
from ic_python_logging import get_logger

logger = get_logger("api.licenses")


def _is_controller() -> bool:
    try:
        return bool(ic.is_controller(ic.caller()))
    except Exception:
        return False


def _now() -> float:
    return float(ic.time())


def _to_dict(lic: DeveloperLicenseEntity) -> Dict[str, Any]:
    return {
        "principal": str(lic.principal or ""),
        "created_at": float(lic.created_at or 0),
        "expires_at": float(lic.expires_at or 0),
        "last_payment_id": str(lic.last_payment_id or ""),
        "payment_method": str(lic.payment_method or ""),
        "note": str(lic.note or ""),
        "is_active": bool(lic.is_active) if lic.is_active is not None else False,
    }


def check_license(principal: str) -> Dict:
    lic = DeveloperLicenseEntity[principal]
    if lic is None:
        return {"success": False, "error": "No license found"}
    if not (lic.is_active if lic.is_active is not None else False):
        return {"success": False, "error": "License is inactive"}
    if float(lic.expires_at or 0) < _now():
        return {"success": False, "error": "License expired"}
    return {"success": True, "license": _to_dict(lic)}


def has_active_license(principal: str) -> bool:
    return check_license(principal).get("success", False)


def record_license_payment(
    *,
    principal: str,
    stripe_session_id: str,
    duration_seconds: int,
    payment_method: str = "stripe",
    note: str = "",
) -> Dict:
    """Called by the billing service after Stripe success (or by a controller).

    Either creates a new license or extends an existing one by
    ``duration_seconds``.
    """
    caller = str(ic.caller())
    billing_principal = get_billing_service_principal()
    if not _is_controller() and (not billing_principal or caller != billing_principal):
        return {"success": False, "error": "Unauthorized: caller is not the billing service or a controller"}
    if not principal or not principal.strip():
        return {"success": False, "error": "principal is required"}
    if duration_seconds <= 0:
        return {"success": False, "error": "duration_seconds must be positive"}

    now = _now()
    lic = DeveloperLicenseEntity[principal]
    if lic is None:
        lic = DeveloperLicenseEntity(
            principal=principal,
            created_at=now,
            expires_at=now + duration_seconds,
            last_payment_id=stripe_session_id,
            payment_method=payment_method,
            note=note,
            is_active=True,
        )
        action = "created"
    else:
        # Extend from the later of (now, current expiry) so we never shorten
        # an active license.
        base = max(now, float(lic.expires_at or 0))
        lic.expires_at = base + duration_seconds
        lic.last_payment_id = stripe_session_id or lic.last_payment_id
        lic.payment_method = payment_method or lic.payment_method
        lic.note = note or lic.note
        lic.is_active = True
        action = "extended"

    logger.info(
        f"license {action} for {principal} via {payment_method} "
        f"(expires_at={lic.expires_at}, session={stripe_session_id})"
    )
    return {"success": True, "action": action, "license": _to_dict(lic)}


def grant_manual_license(*, principal: str, duration_seconds: int, note: str = "") -> Dict:
    if not _is_controller():
        return {"success": False, "error": "Unauthorized: controller-only"}
    return record_license_payment(
        principal=principal,
        stripe_session_id="",
        duration_seconds=duration_seconds,
        payment_method="manual",
        note=note or "manual grant",
    )


def revoke_license(principal: str) -> Dict:
    if not _is_controller():
        return {"success": False, "error": "Unauthorized: controller-only"}
    lic = DeveloperLicenseEntity[principal]
    if lic is None:
        return {"success": False, "error": "No license found"}
    lic.is_active = False
    lic.note = "revoked"
    logger.info(f"license revoked for {principal}")
    return {"success": True, "license": _to_dict(lic)}
