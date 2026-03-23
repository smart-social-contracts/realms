from ic_python_db import Boolean, Entity, Integer, OneToMany, OneToOne, String, TimestampedMixin
from ic_python_logging import get_logger
from ..system.constants import STATUS_MAX_LENGTH

logger = get_logger("entity.realm")


class RealmStatus:
    ALPHA = "alpha"              # Gathering interest, deposits refundable
    BETA = "beta"                # Deposits locked, auctions & land bidding
    PRODUCTION = "production"    # Fully operational
    DEPRECATION = "deprecation"  # Winding down, no new members
    TERMINATED = "terminated"    # Closed, read-only archive


class Realm(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    description = String(max_length=256)
    logo = String(max_length=512)  # Path or URL to realm logo
    welcome_image = String(max_length=512)  # Path or URL to welcome page background image
    welcome_message = String(max_length=1024)  # Welcome message displayed on landing page
    status = String(max_length=STATUS_MAX_LENGTH, default=RealmStatus.ALPHA)
    manifest_data = String(max_length=4096, default="{}")
    calendar = OneToOne("Calendar", "realm")
    treasury = OneToOne("Treasury", "realm")
    funds = OneToMany("Fund", "realm")
    justice_systems = OneToMany("JusticeSystem", "realm")
    accounting_currency = String(max_length=16, default="ckBTC")
    accounting_currency_decimals = Integer(default=8)
    principal_id = String(max_length=64)
    # Canister IDs for this realm (set post-deployment via set_canister_config)
    frontend_canister_id = String(max_length=64)
    token_canister_id = String(max_length=64)
    nft_canister_id = String(max_length=64)
    # Quarter/Federation fields (dormant for single-quarter realms)
    is_quarter = Boolean(default=False)
    federation_realm_id = String(max_length=64)  # parent realm ID if this is a quarter
    quarter_ids = OneToMany("Quarter", "federation")
    federation_codex = OneToOne("Codex", "federation")
