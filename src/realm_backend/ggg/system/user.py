from typing import Any

from ic_basilisk_toolkit.crypto import EncryptedString
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
    # Public data (visible to community)
    nickname = String(max_length=256)
    avatar = String(max_length=512)
    # Quarter federation
    home_quarter = String(max_length=64)  # Canister ID of user's home quarter
    # Private data (encrypted at rest via vetKeys + basilisk OS crypto)
    # JSON blob — schema defined in realm manifest
    private_data = EncryptedString()
    # Unidirectional (issue #242): profiles/extensions/departments fan out to
    # every user, so the target side keeps only an O(1) counter
    # (e.g. profile.reverse_count("users")) instead of an ID array that would
    # be rewritten on each registration. Reverse *listing* is a paginated user
    # scan — see core.membership.
    profiles = ManyToMany(["UserProfile"], "users", unidirectional=True)
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
    extensions = ManyToMany(["Extension"], "users", unidirectional=True)
    departments = ManyToMany(["Department"], "members", unidirectional=True)
    headed_departments = OneToMany("Department", "head")
    # transfers_from = OneToMany("Transfer", "from_user")
    # transfers_to = OneToMany("Transfer", "to_user")
    # trades_a = OneToMany("Trade", "user_a")
    # trades_b = OneToMany("Trade", "user_b")
    # owned_lands = OneToMany("Land", "owner_user")

    def __repr__(self):
        return f"User(id={self.id!r})"

    @staticmethod
    def user_register_posthook(user: "User"):
        """Named posthook point called after user registration (issue #244).

        Dispatch order:
          1. the active hook-API codex's ``on_user_register`` hook — the
             standard integration point for ``kind: codex`` packages;
          2. legacy fallback — a Codex entity named ``user_registration_hook``
             (or ``user_registration_hook_codex``), exec'd directly. The old
             manifest-based ``entity_method_overrides`` monkey-patch replaces
             this method entirely, so pre-hook codices bypass this body.
        """
        try:
            from core.codex_hooks import dispatch_on_user_register

            if dispatch_on_user_register(user.id):
                return
        except Exception as e:
            logger.error(f"Codex on_user_register dispatch failed: {e}")

        try:
            from ggg.governance.codex import Codex

            _HOOK_NAMES = ("user_registration_hook", "user_registration_hook_codex")
            for codex in Codex.instances():
                if codex.name in _HOOK_NAMES and codex.code:
                    import ggg as _ggg
                    from _cdk import ic as _ic

                    ns = {"ic": _ic, "ggg": _ggg, "__builtins__": __builtins__}
                    exec(compile(codex.code, f"{codex.name}.py", "exec"), ns)
                    if "user_register_posthook" in ns:
                        logger.info(
                            f"Executing codex user_register_posthook for user {user.id}"
                        )
                        ns["user_register_posthook"](user)
                        return
        except Exception as e:
            logger.error(f"Error executing user_registration_hook codex: {e}")
            import traceback

            logger.error(traceback.format_exc())
        logger.info(
            f"Hook called after user registration. User {user.id} registered with profile {user.profiles}"
        )
        return

    @staticmethod
    def role_assign_prehook(user: "User", profile_name: str, assigner_principal: str) -> bool:
        """Called before assigning a profile. Codex override can reject (raise) or allow.

        Default: allow. Codex overrides implement governance policy
        (e.g., require approved proposal for sensitive roles).
        """
        try:
            from ggg.governance.codex import Codex

            _HOOK_NAMES = ("role_management_hook", "role_management_hook_codex")
            for codex in Codex.instances():
                if codex.name in _HOOK_NAMES and codex.code:
                    import ggg as _ggg
                    from _cdk import ic as _ic

                    ns = {"ic": _ic, "ggg": _ggg, "__builtins__": __builtins__}
                    exec(compile(codex.code, f"{codex.name}.py", "exec"), ns)
                    if "role_assign_prehook" in ns:
                        logger.info(
                            f"Executing codex role_assign_prehook for user {user.id}, profile {profile_name}"
                        )
                        return ns["role_assign_prehook"](user, profile_name, assigner_principal)
        except Exception as e:
            logger.error(f"Error in role_assign_prehook codex: {e}")
            import traceback

            logger.error(traceback.format_exc())
            raise
        return True

    @staticmethod
    def role_assign_posthook(user: "User", profile_name: str, assigner_principal: str):
        """Called after successful profile assignment. Codex can handle notifications, logging, etc."""
        try:
            from ggg.governance.codex import Codex

            _HOOK_NAMES = ("role_management_hook", "role_management_hook_codex")
            for codex in Codex.instances():
                if codex.name in _HOOK_NAMES and codex.code:
                    import ggg as _ggg
                    from _cdk import ic as _ic

                    ns = {"ic": _ic, "ggg": _ggg, "__builtins__": __builtins__}
                    exec(compile(codex.code, f"{codex.name}.py", "exec"), ns)
                    if "role_assign_posthook" in ns:
                        logger.info(
                            f"Executing codex role_assign_posthook for user {user.id}, profile {profile_name}"
                        )
                        ns["role_assign_posthook"](user, profile_name, assigner_principal)
                        return
        except Exception as e:
            logger.error(f"Error in role_assign_posthook codex: {e}")
            import traceback

            logger.error(traceback.format_exc())
        logger.info(
            f"Profile '{profile_name}' assigned to user {user.id} by {assigner_principal}"
        )

    @staticmethod
    def role_revoke_prehook(user: "User", profile_name: str, revoker_principal: str) -> bool:
        """Called before revoking a profile. Codex override can reject (raise) or allow.

        Default: allow. Same pattern as role_assign_prehook.
        """
        try:
            from ggg.governance.codex import Codex

            _HOOK_NAMES = ("role_management_hook", "role_management_hook_codex")
            for codex in Codex.instances():
                if codex.name in _HOOK_NAMES and codex.code:
                    import ggg as _ggg
                    from _cdk import ic as _ic

                    ns = {"ic": _ic, "ggg": _ggg, "__builtins__": __builtins__}
                    exec(compile(codex.code, f"{codex.name}.py", "exec"), ns)
                    if "role_revoke_prehook" in ns:
                        logger.info(
                            f"Executing codex role_revoke_prehook for user {user.id}, profile {profile_name}"
                        )
                        return ns["role_revoke_prehook"](user, profile_name, revoker_principal)
        except Exception as e:
            logger.error(f"Error in role_revoke_prehook codex: {e}")
            import traceback

            logger.error(traceback.format_exc())
            raise
        return True

    @staticmethod
    def role_revoke_posthook(user: "User", profile_name: str, revoker_principal: str):
        """Called after successful profile revocation. Codex can handle notifications, logging, etc."""
        try:
            from ggg.governance.codex import Codex

            _HOOK_NAMES = ("role_management_hook", "role_management_hook_codex")
            for codex in Codex.instances():
                if codex.name in _HOOK_NAMES and codex.code:
                    import ggg as _ggg
                    from _cdk import ic as _ic

                    ns = {"ic": _ic, "ggg": _ggg, "__builtins__": __builtins__}
                    exec(compile(codex.code, f"{codex.name}.py", "exec"), ns)
                    if "role_revoke_posthook" in ns:
                        logger.info(
                            f"Executing codex role_revoke_posthook for user {user.id}, profile {profile_name}"
                        )
                        ns["role_revoke_posthook"](user, profile_name, revoker_principal)
                        return
        except Exception as e:
            logger.error(f"Error in role_revoke_posthook codex: {e}")
            import traceback

            logger.error(traceback.format_exc())
        logger.info(
            f"Profile '{profile_name}' revoked from user {user.id} by {revoker_principal}"
        )


def user_register(principal: str, profile: str) -> dict[str, Any]:
    logger.info(f"Registering user {principal} with profile {profile}")

    user_profi = UserProfile[profile]
    if not user_profi:
        raise ValueError(f"Profile {profile} not found")

    user = User[principal]
    is_new_user = user is None
    if is_new_user:
        user = User(id=principal, profiles=[user_profi])
        logger.info(f"Created new user {principal} with profile {profile}")
    else:
        # Add profile only if not already assigned
        if user_profi not in user.profiles:
            user.profiles.add(user_profi)
            logger.info(f"Added profile {profile} to existing user {principal}")
        else:
            logger.info(f"User {principal} already has profile {profile}")

    if is_new_user:
        User.user_register_posthook(user)  # type: ignore[arg-type]
        # Auto-scaling: evaluate whether the federation should spawn a new
        # quarter now that population grew. Runs for *all* user-creation paths
        # (so a codex posthook override can't disable sharding). Non-blocking —
        # it only records intent; provisioning happens out of band.
        try:
            from core.autoscale import maybe_request_quarter_scale

            if maybe_request_quarter_scale():
                logger.info(f"Quarter auto-scale requested after registering {principal}")
        except Exception as e:
            logger.error(f"Auto-scale evaluation failed for {principal}: {e}")

    return {
        "principal": user.id,
        "profiles": [profile.name for profile in user.profiles],
        "nickname": user.nickname or "",
        "avatar": user.avatar or "",
        "private_data": user.private_data or "",
        "home_quarter": user.home_quarter or "",
    }
