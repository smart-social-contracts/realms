from kybra_simple_db import Entity, Integer, OneToMany, OneToOne, String, TimestampedMixin
from kybra_simple_logging import get_logger

logger = get_logger("entity.realm")


class Realm(Entity, TimestampedMixin):
    __alias__ = "name"
    name = String(min_length=2, max_length=256)
    description = String(max_length=256)
    logo = String(max_length=512)  # Path or URL to realm logo
    welcome_image = String(max_length=512)  # Path or URL to welcome page background image
    welcome_message = String(max_length=1024)  # Welcome message displayed on landing page
    treasury = OneToOne("Treasury", "realm")
    funds = OneToMany("Fund", "realm")
    justice_systems = OneToMany("JusticeSystem", "realm")
    principal_id = String(max_length=64)
    # Canister IDs for this realm (set post-deployment via set_canister_config)
    frontend_canister_id = String(max_length=64)
    token_canister_id = String(max_length=64)
    nft_canister_id = String(max_length=64)
