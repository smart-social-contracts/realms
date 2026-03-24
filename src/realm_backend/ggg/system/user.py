from typing import Any

from ic_python_db import (
    Entity,
    ManyToMany,
    OneToMany,
    OneToOne,
    String,
    TimestampedMixin,
)
from ic_python_logging import get_logger

from .user_profile import UserProfile

logger = get_logger("entity.user")


class User(Entity, TimestampedMixin):
    __alias__ = "id"
    id = String()
    profile_picture_url = String(max_length=512)
    profiles = ManyToMany(["UserProfile"], "users")
    human = OneToOne("Human", "user")
    member = OneToOne("Member", "user")
    proposals = OneToMany("Proposal", "proposer")
    votes = OneToMany("Vote", "voter")
    notifications = OneToMany("Notification", "user")
    services = OneToMany("Service", "user")
    tax_records = OneToMany("TaxRecord", "user")
    disputes_requested = OneToMany("Dispute", "requester")
    disputes_defendant = OneToMany("Dispute", "defendant")
    payment_accounts = OneToMany("PaymentAccount", "user")
    invoices = OneToMany("Invoice", "user")
    zones = OneToMany("Zone", "user")
    ledger_entries = OneToMany("LedgerEntry", "user")
    cases_as_plaintiff = OneToMany("Case", "plaintiff")
    cases_as_defendant = OneToMany("Case", "defendant")
    penalties_received = OneToMany("Penalty", "target_user")
    appeals_filed = OneToMany("Appeal", "appellant")
    permissions = ManyToMany(["Permission"], "users")
    # transfers_from = OneToMany("Transfer", "from_user")
    # transfers_to = OneToMany("Transfer", "to_user")
    # trades_a = OneToMany("Trade", "user_a")
    # trades_b = OneToMany("Trade", "user_b")
    # owned_lands = OneToMany("Land", "owner_user")

    def __repr__(self):
        return f"User(id={self.id!r})"

    @staticmethod
    def user_register_posthook(user: "User"):
        """Hook called after user registration. Dynamically loads codex override if available."""
        try:
            from ggg.governance.codex import Codex
            for codex in Codex.instances():
                if codex.name == "user_registration_hook" and codex.code:
                    import ggg as _ggg
                    from _cdk import ic as _ic
                    ns = {"ic": _ic, "ggg": _ggg, "__builtins__": __builtins__}
                    exec(compile(codex.code, "user_registration_hook.py", "exec"), ns)
                    if "user_register_posthook" in ns:
                        logger.info(f"Executing codex user_register_posthook for user {user.id}")
                        ns["user_register_posthook"](user)
                        return
        except Exception as e:
            logger.error(f"Error executing user_registration_hook_codex: {e}")
            import traceback
            logger.error(traceback.format_exc())
        logger.info(f"Hook called after user registration. User {user.id} registered with profile {user.profiles}")
        return


def user_register(principal: str, profile: str) -> dict[str, Any]:
    logger.info(f"Registering user {principal} with profile {profile}")

    user_profi = UserProfile[profile]
    if not user_profi:
        raise ValueError(f"Profile {profile} not found")

    user = User[principal]
    if not user:
        user = User(id=principal, profiles=[user_profi])
        logger.info(f"Created new user {principal} with profile {profile}")
    else:
        # Add profile only if not already assigned
        if user_profi not in user.profiles:
            user.profiles.add(user_profi)
            logger.info(f"Added profile {profile} to existing user {principal}")
        else:
            logger.info(f"User {principal} already has profile {profile}")

    User.user_register_posthook(user)  # type: ignore[arg-type]

    return {
        "principal": user.id,
        "profiles": [profile.name for profile in user.profiles],
        "profile_picture_url": user.profile_picture_url or "",
    }