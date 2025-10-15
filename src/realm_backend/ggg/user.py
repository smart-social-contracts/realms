from ggg import Trade, Transfer
from kybra_simple_db import (
    Entity,
    ManyToMany,
    OneToMany,
    OneToOne,
    String,
    TimestampedMixin,
)
from kybra_simple_logging import get_logger

logger = get_logger("entity.user")


class User(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    profile_picture_url = String(max_length=512)
    profiles = ManyToMany(["UserProfile"], "users")
    human = OneToOne("Human", "user")
    citizen = OneToOne("Citizen", "user")
    # transfers_from = OneToMany("Transfer", "from_user")
    # transfers_to = OneToMany("Transfer", "to_user")
    # trades_a = OneToMany("Trade", "user_a")
    # trades_b = OneToMany("Trade", "user_b")
    # owned_lands = OneToMany("Land", "owner_user")
