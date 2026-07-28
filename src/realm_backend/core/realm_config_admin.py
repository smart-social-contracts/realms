"""Realm configuration mutations, governed by root org policy (issue #262).

The apply function is called from two places that must never diverge:

- ``main.update_realm_config`` when the root policy is 1/1 (direct), and
- proposal replay (core.governed_action.execute_backend_replay) after a
  root-scoped vote passes on any other policy.
"""

import json

from ic_python_logging import get_logger

logger = get_logger("core.realm_config_admin")


def describe_realm_config(config: dict) -> str:
    """One-line human summary for proposal titles and audit logs."""
    keys = sorted(k for k in config.keys() if k != "confirm")
    label = ", ".join(keys[:8])
    if len(keys) > 8:
        label += ", …"
    return f"Update realm configuration ({label})"


def apply_realm_config(config: dict) -> dict:
    """Apply a realm configuration change. No access checks here — callers
    (endpoint or approved proposal) are responsible for authorization."""
    from ggg import Realm

    realms = list(Realm.instances())
    if not realms:
        logger.error("apply_realm_config: no realm found")
        return {"success": False, "error": "No realm found"}

    realm = realms[0]
    updated_fields = []

    if "name" in config and config["name"]:
        realm.name = config["name"]
        updated_fields.append(f"name={config['name']}")

    if "manifesto" in config and config["manifesto"]:
        realm.manifesto = config["manifesto"]
        updated_fields.append(f"manifesto={config['manifesto'][:50]}...")

    if "welcome_message" in config:
        realm.welcome_message = config["welcome_message"] or ""
        updated_fields.append(
            f"welcome_message={config['welcome_message'][:50] if config['welcome_message'] else ''}..."
        )

    if "open_registration" in config:
        # Codex init owns registration when manifest_data carries a policy
        # (issue #244). Ignore wizard/installer overrides in that case.
        codex_pins_registration = False
        try:
            md = json.loads(getattr(realm, "manifest_data", "") or "{}")
            reg = (md.get("onboarding") or {}).get("registration") or {}
            codex_pins_registration = "open_registration" in reg
        except (json.JSONDecodeError, TypeError):
            pass
        if not codex_pins_registration:
            realm.open_registration = bool(config["open_registration"])
            updated_fields.append(f"open_registration={realm.open_registration}")
        else:
            logger.info(
                "Skipping open_registration update — codex registration "
                f"policy is authoritative ({realm.open_registration})"
            )

    # Marketplace trust policy (issue #267). Guarded by its own operation at
    # the endpoint, since switching it off admits unreviewed code.
    if "require_marketplace_approval" in config:
        realm.require_marketplace_approval = bool(
            config["require_marketplace_approval"]
        )
        updated_fields.append(
            f"require_marketplace_approval={realm.require_marketplace_approval}"
        )

    if "trusted_approvers" in config:
        raw = config["trusted_approvers"]
        if isinstance(raw, list):
            raw = ",".join(str(p) for p in raw)
        approvers = ",".join(p.strip() for p in str(raw or "").split(",") if p.strip())
        realm.trusted_approvers = approvers
        updated_fields.append(f"trusted_approvers={approvers or '(marketplace)'}")

    if "config_overrides" in config:
        # Per-deployment codex parameter overrides chosen in the creation
        # wizard (issue #253). Stored under manifest_data.config_overrides;
        # codex_hooks.get_config() applies them over codex-declared values.
        overrides = config["config_overrides"]
        if not isinstance(overrides, dict):
            return {
                "success": False,
                "error": "config_overrides must be an object",
            }
        try:
            md = json.loads(getattr(realm, "manifest_data", "") or "{}")
            if not isinstance(md, dict):
                md = {}
        except (json.JSONDecodeError, TypeError):
            md = {}
        existing = md.get("config_overrides")
        if isinstance(existing, dict):
            merged_overrides = dict(existing)
            merged_overrides.update(overrides)
        else:
            merged_overrides = dict(overrides)
        md["config_overrides"] = merged_overrides
        serialized_md = json.dumps(md)
        if len(serialized_md) > 4096:
            return {
                "success": False,
                "error": f"manifest_data would exceed 4096 chars ({len(serialized_md)})",
            }
        realm.manifest_data = serialized_md
        updated_fields.append(f"config_overrides={list(merged_overrides.keys())}")

        # The voting window lives on the Calendar entity (seconds), not in
        # manifest_data — sync it from the effective merged config so a
        # wizard override of governance.voting_window_days actually changes
        # how long ballots stay open.
        try:
            from core.codex_hooks import get_config as _get_codex_config

            effective = _get_codex_config()
            days = (effective.get("governance") or {}).get("voting_window_days")
            if days is not None and realm.calendar:
                seconds = max(1, int(round(float(days) * 86400)))
                realm.calendar.voting_window = seconds
                updated_fields.append(f"calendar.voting_window={seconds}s")
        except Exception as cal_err:
            logger.warning(f"Could not sync calendar voting_window: {cal_err}")

    if "quarter_join_mode" in config:
        mode = str(config["quarter_join_mode"] or "auto").strip().lower()
        if mode not in ("auto", "choice"):
            return {
                "success": False,
                "error": "quarter_join_mode must be 'auto' or 'choice'",
            }
        realm.quarter_join_mode = mode
        updated_fields.append(f"quarter_join_mode={realm.quarter_join_mode}")

    if "ai_assistant_enabled" in config:
        realm.ai_assistant_enabled = bool(config["ai_assistant_enabled"])
        updated_fields.append(f"ai_assistant_enabled={realm.ai_assistant_enabled}")

    if "email_service_config" in config:
        email_config = config["email_service_config"]
        if not isinstance(email_config, dict):
            return {
                "success": False,
                "error": "email_service_config must be an object",
            }
        try:
            md = json.loads(getattr(realm, "manifest_data", "") or "{}")
            if not isinstance(md, dict):
                md = {}
        except (json.JSONDecodeError, TypeError):
            md = {}

        # Validate shape: only non-sensitive, realm-level settings are stored
        # on-chain. SMTP credentials live in the off-chain worker env.
        allowed_keys = {
            "enabled",
            "from_name",
            "from_address",
            "reply_to",
            "events",
            "templates",
        }
        if set(email_config.keys()) - allowed_keys:
            return {
                "success": False,
                "error": (
                    "email_service_config may only contain: "
                    f"{', '.join(sorted(allowed_keys))}"
                ),
            }

        # Normalize the events map so the UI always sees a consistent set.
        default_events = {
            "proposal_created": True,
            "vote_reminder": True,
            "vote_ended": True,
            "mention": True,
            "task_assigned": True,
        }
        events = email_config.get("events") or {}
        if not isinstance(events, dict):
            events = {}
        normalized_events = {**default_events, **events}
        email_config["events"] = normalized_events

        md["email"] = email_config
        serialized_md = json.dumps(md)
        if len(serialized_md) > 4096:
            return {
                "success": False,
                "error": f"manifest_data would exceed 4096 chars ({len(serialized_md)})",
            }
        realm.manifest_data = serialized_md
        updated_fields.append(f"email={list(email_config.keys())}")

    if "logo_url" in config:
        realm.logo_url = config["logo_url"] or ""
        updated_fields.append(f"logo_url={realm.logo_url[:50]}...")

    if "background_image_url" in config:
        realm.background_image_url = config["background_image_url"] or ""
        updated_fields.append(
            f"background_image_url={realm.background_image_url[:50]}..."
        )

    if "file_registry_canister_id" in config:
        realm.file_registry_canister_id = config["file_registry_canister_id"] or ""
        updated_fields.append(
            f"file_registry_canister_id={realm.file_registry_canister_id}"
        )

    if "marketplace_canister_id" in config:
        realm.marketplace_canister_id = config["marketplace_canister_id"] or ""
        updated_fields.append(
            f"marketplace_canister_id={realm.marketplace_canister_id}"
        )

    if "accounting_currency" in config:
        symbol = str(config["accounting_currency"] or "").strip()
        if not symbol:
            return {
                "success": False,
                "error": "accounting_currency must be a non-empty symbol (e.g. ckBTC)",
            }
        if len(symbol) > 16:
            return {
                "success": False,
                "error": "accounting_currency must be at most 16 characters",
            }
        realm.accounting_currency = symbol
        updated_fields.append(f"accounting_currency={realm.accounting_currency}")

    if "accounting_currency_decimals" in config:
        try:
            decimals = int(config["accounting_currency_decimals"])
        except (TypeError, ValueError):
            return {
                "success": False,
                "error": "accounting_currency_decimals must be an integer",
            }
        if decimals < 0 or decimals > 18:
            return {
                "success": False,
                "error": "accounting_currency_decimals must be between 0 and 18",
            }
        realm.accounting_currency_decimals = decimals
        updated_fields.append(
            f"accounting_currency_decimals={realm.accounting_currency_decimals}"
        )

    if "token_canister_id" in config:
        token_id = str(config.get("token_canister_id") or "").strip()
        realm.token_canister_id = token_id
        updated_fields.append(f"token_canister_id={token_id}")

    if "nft_canister_id" in config:
        nft_id = str(config.get("nft_canister_id") or "").strip()
        realm.nft_canister_id = nft_id
        updated_fields.append(f"nft_canister_id={nft_id}")

    token_ledger = getattr(realm, "token_canister_id", "") or ""
    if token_ledger and (
        "token_canister_id" in config
        or "token_indexer_canister_id" in config
        or "accounting_currency" in config
    ):
        from api.tokens import register_treasury_token

        sym = str(getattr(realm, "accounting_currency", "") or "").strip() or "REALMS"
        indexer = str(config.get("token_indexer_canister_id") or "").strip()
        if not indexer:
            from api.tokens import get_treasury_token_indexer

            indexer = get_treasury_token_indexer(sym, token_ledger)
        decimals = int(getattr(realm, "accounting_currency_decimals", 8) or 8)
        register_treasury_token(
            symbol=sym,
            ledger_canister_id=token_ledger,
            indexer_canister_id=indexer,
            decimals=decimals,
        )
        updated_fields.append(f"treasury_token={sym}@{token_ledger}")

    logger.info(f"✅ Realm config updated: {', '.join(updated_fields)}")
    return {"success": True, "updated_fields": updated_fields}
