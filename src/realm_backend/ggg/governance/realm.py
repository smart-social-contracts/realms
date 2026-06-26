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
    __version__ = 5
    name = String(min_length=2, max_length=256)
    manifesto = String(max_length=256)

    @classmethod
    def migrate(cls, obj, from_version, to_version):
        if from_version < 2:
            obj["manifesto"] = obj.pop("description", "")
        if from_version < 3:
            if obj.get("ai_assistant_enabled") is None:
                obj["ai_assistant_enabled"] = True
        if from_version < 4:
            obj.setdefault("auto_scale_enabled", True)
            obj.setdefault("scale_in_flight", False)
            obj.setdefault("scale_requested_at", "")
        if from_version < 5:
            obj.setdefault("bootstrap_state", "")
        return obj
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
    # Shared infrastructure canister IDs (typically set from deploy descriptor infra section)
    file_registry_canister_id = String(max_length=64)
    marketplace_canister_id = String(max_length=64)
    # Quarter/Federation fields (dormant for single-quarter realms)
    is_quarter = Boolean(default=False)
    is_capital = Boolean(default=False)  # This quarter coordinates federation governance
    federation_realm_id = String(max_length=64)  # parent realm ID if this is a quarter
    quarter_ids = OneToMany("Quarter", "federation")
    federation_codex = OneToOne("Codex", "federation")
    # Auto-scaling / sharding (issue #156). When enabled, a new quarter deploy
    # is requested once the fullest quarter reaches 90% of N (see core.autoscale).
    auto_scale_enabled = Boolean(default=True)
    # Idempotent guard: True while a quarter provisioning job is queued/running.
    # Set by the user-registration trigger, cleared by the async provisioning
    # endpoint on success/failure so the next threshold crossing can re-trigger.
    scale_in_flight = Boolean(default=False)
    scale_requested_at = String(max_length=32, default="")
    # Quarter-local self-bootstrap progress (issue #156). JSON install plan +
    # cursor persisted on a freshly minted quarter; the recurring TaskManager
    # task in core.quarter_bootstrap installs one item per tick from this state.
    bootstrap_state = String(max_length=8192, default="")
    # Canister id of the realm_installer broker used to provision new quarters
    # via Casals. Empty => auto-scale records intent but cannot self-provision.
    installer_canister_id = String(max_length=64, default="")
    # Comma-separated canister principal IDs trusted for inter-canister calls
    # (DAO controllers, AI agents, parent realms). These bypass User-based access checks.
    trusted_principals = String(max_length=2048, default="")
    # When False (default), all users must present an invite code to join.
    # When True, anyone can join as member without a code. Admin always requires a code.
    open_registration = Boolean(default=False)
    # When True (default), the AI assistant sidebar and Explain actions are available.
    # Admins can disable via update_realm_config without uninstalling llm_chat.
    ai_assistant_enabled = Boolean(default=True)
    # Branding URLs (optional; frontend falls back to static /images/ assets)
    logo_url = String(max_length=512, default="")
    background_image_url = String(max_length=512, default="")
    # Deployed version (set by set_canister_config or CI post-deploy)
    installed_version = String(max_length=32, default="")
    # IC network this realm is deployed on (e.g. "test", "staging", "demo", "ic")
    network = String(max_length=16, default="")
    # Test mode flags (set via set_canister_config; hard-rejected on network=="ic")
    test_mode = Boolean(default=False)
    test_mode_ii_bypass = Boolean(default=False)
    test_mode_user_self_registration = Boolean(default=False)
    test_mode_demo_data = Boolean(default=False)
    test_mode_skip_terms = Boolean(default=False)
    test_mode_skip_passport_zkproof = Boolean(default=False)
    test_mode_skip_authentication = Boolean(default=False)
