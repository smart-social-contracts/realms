"""ic_python_db Entity models for the marketplace backend.

Five families:

  * ExtensionListingEntity / CodexListingEntity — what's for sale.
  * PurchaseEntity                              — record of a buy_*.
  * LikeEntity                                  — one row per (user, item).
  * DeveloperLicenseEntity                      — paid annual license.
  * MarketplaceConfigEntity                     — singleton config (file_registry id, billing service principal, license pricing).

All record fields are stored on-chain in the canister's StableBTreeMap
via ic_python_db. New fields can be added in future upgrades; existing
data without those fields reads back as ``None`` and our APIs always
guard with ``or 0`` / ``or ""``.
"""

from ic_python_db import (
    Boolean,
    Entity,
    Float,
    Integer,
    String,
    TimestampedMixin,
)


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------

class ExtensionListingEntity(Entity, TimestampedMixin):
    """One row per (extension_id) — latest version wins.

    The actual files live in a file_registry canister at the namespace
    ``ext/{extension_id}/{version}``; we only store the pointer + metadata.
    """
    __alias__ = "extension_id"

    extension_id              = String(max_length=128)
    developer                 = String(max_length=128)   # principal text
    name                      = String(max_length=256)
    description               = String(max_length=2048)
    version                   = String(max_length=32)
    price_e8s                 = Integer()                 # display only — no on-chain transfer
    icon                      = String(max_length=64)     # short emoji / lucide name
    categories                = String(max_length=256)    # comma-separated
    file_registry_canister_id = String(max_length=64)
    file_registry_namespace   = String(max_length=256)
    download_url              = String(max_length=512)    # legacy / fallback
    installs                  = Integer()
    likes                     = Integer()
    verification_status       = String(max_length=32)     # unverified | pending_audit | verified | rejected
    verification_notes        = String(max_length=1024)
    is_active                 = Boolean()
    created_at                = Float()
    updated_at                = Float()


class CodexListingEntity(Entity, TimestampedMixin):
    """One row per codex package.

    ``codex_id`` may contain ``/`` (e.g. ``"syntropia/membership"``);
    the entity alias is ``codex_alias`` which is the slash-safe form
    (``"syntropia__membership"``). Helpers are in ``api.codices``.
    """
    __alias__ = "codex_alias"

    codex_alias               = String(max_length=128)
    codex_id                  = String(max_length=128)
    realm_type                = String(max_length=64)
    developer                 = String(max_length=128)
    name                      = String(max_length=256)
    description               = String(max_length=2048)
    version                   = String(max_length=32)
    price_e8s                 = Integer()
    icon                      = String(max_length=64)
    categories                = String(max_length=256)
    file_registry_canister_id = String(max_length=64)
    file_registry_namespace   = String(max_length=256)
    installs                  = Integer()
    likes                     = Integer()
    verification_status       = String(max_length=32)
    verification_notes        = String(max_length=1024)
    is_active                 = Boolean()
    created_at                = Float()
    updated_at                = Float()


# ---------------------------------------------------------------------------
# Purchases
# ---------------------------------------------------------------------------

class PurchaseEntity(Entity):
    """One row per buy_* call.

    Used by both extension and codex purchases (``item_kind`` discriminates).
    """
    __alias__ = "purchase_id"

    purchase_id     = String(max_length=128)
    realm_principal = String(max_length=128)
    item_kind       = String(max_length=16)              # "ext" | "codex"
    item_id         = String(max_length=128)
    developer       = String(max_length=128)
    price_paid_e8s  = Integer()
    purchased_at    = Float()


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------

class LikeEntity(Entity):
    """One row per (principal, item_kind, item_id).

    ``like_id`` is the composite key ``"{principal}|{item_kind}|{item_id}"``.
    Listing entities carry a denormalised ``likes`` counter that this
    table is the source of truth for.
    """
    __alias__ = "like_id"

    like_id    = String(max_length=384)
    principal  = String(max_length=128)
    item_kind  = String(max_length=16)
    item_id    = String(max_length=128)
    created_at = Float()


# ---------------------------------------------------------------------------
# Developer licenses
# ---------------------------------------------------------------------------

class DeveloperLicenseEntity(Entity):
    """Paid annual license — gates ``request_audit``.

    Anyone can publish without a license; the license unlocks the audit
    flow run by Smart Social Contracts curators (controllers).
    ``last_payment_amount_usd_cents`` mirrors what the user actually
    paid for the most recent extension/renewal, kept on the row purely
    as an audit trail.
    """
    __alias__ = "principal"

    principal                     = String(max_length=128)
    created_at                    = Float()
    expires_at                    = Float()
    last_payment_id               = String(max_length=128)  # Stripe checkout session id
    last_payment_amount_usd_cents = Integer()
    payment_method                = String(max_length=32)   # stripe | manual | voucher
    note                          = String(max_length=512)
    is_active                     = Boolean()


# ---------------------------------------------------------------------------
# Singleton configuration
# ---------------------------------------------------------------------------

class MarketplaceConfigEntity(Entity):
    """Singleton — ``alias = "config"``.

    Holds:
      * ``file_registry_canister_id`` — where listings store their files.
      * ``billing_service_principal`` — principal allowed to call
        ``record_license_payment`` (the off-chain Stripe relay).
      * ``license_price_usd_cents`` and ``license_duration_seconds`` —
        displayed on the developer page; the billing service uses the
        same pricing when creating a checkout session.
    """
    __alias__ = "id"

    id                          = String(max_length=16)  # always "config"
    file_registry_canister_id   = String(max_length=64)
    billing_service_principal   = String(max_length=128)
    license_price_usd_cents     = Integer()
    license_duration_seconds    = Integer()
