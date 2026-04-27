"""
Status API for Realm DAO system

Provides health check and system status information
"""

import json
import sys
from typing import Any

from _cdk import ic
from ggg import (
    Codex,
    Dispute,
    Instrument,
    License,
    Mandate,
    Organization,
    Proposal,
    Quarter,
    Realm,
    Registry,
    Task,
    Trade,
    Transfer,
    User,
    UserProfile,
    Vote,
)
from ic_python_logging import get_logger

# Initialize logger
logger = get_logger("api.status")


def get_status() -> "dict[str, Any]":
    """
    Get current system status and health information

    Optimized to minimize instruction count for query calls.

    Returns:
        Status: Object with status information conforming to the Candid type
    """
    logger.info("Status check requested")

    # Get entity counts from the database (count() is optimized by ic_python_db)
    users_count = User.count()
    organizations_count = Organization.count()
    realms_count = Realm.count()
    mandates_count = Mandate.count()
    tasks_count = Task.count()
    transfers_count = Transfer.count()
    instruments_count = Instrument.count()
    codexes_count = Codex.count()
    disputes_count = Dispute.count()
    licenses_count = License.count()
    trades_count = Trade.count()
    proposals_count = Proposal.count()
    votes_count = Vote.count()
    user_profiles_count = UserProfile.count()

    realm_name = ""
    realm_logo = "/images/logo.png"
    realm_welcome_image = "/images/background.png"
    realm_welcome_message = ""
    realm_description = ""
    try:
        first_realm = Realm.load("1")
        if first_realm:
            realm_name = first_realm.name or ""
            realm_welcome_message = getattr(first_realm, "welcome_message", None) or ""
            realm_description = getattr(first_realm, "description", None) or ""
    except Exception:
        pass

    # Extension discovery with version, commit, and datetime from manifests
    extensions_commit = "EXTENSIONS_COMMIT_HASH_PLACEHOLDER"
    extensions_commit_datetime = "EXTENSIONS_COMMIT_DATETIME_PLACEHOLDER"
    extension_entries = []
    try:
        from api.extensions import get_all_extension_manifests

        manifests = get_all_extension_manifests()
        for ext_name, manifest in manifests.items():
            extension_entries.append(
                json.dumps(
                    {
                        "name": ext_name,
                        "version": manifest.get("version", ""),
                        "commit": extensions_commit,
                        "commit_datetime": extensions_commit_datetime,
                    }
                )
            )
    except Exception as e:
        logger.warning(f"Could not list extensions: {e}")

    # Static values — placeholders replaced at build time by CI
    commit_hash = "COMMIT_HASH_PLACEHOLDER"
    commit_datetime = "COMMIT_DATETIME_PLACEHOLDER"
    version = "VERSION_PLACEHOLDER"
    test_mode = False

    # Skip expensive TaskManager status to stay under instruction limit
    # TaskManager status can be queried via separate endpoint if needed
    task_manager_status = {"status": "available"}  # Simplified to reduce instructions

    # Get canister IDs - backend is self, others from Realm entity
    canisters = []

    # Backend canister (self)
    try:
        backend_id = ic.id().to_str()
        canisters.append({"canister_id": backend_id, "canister_type": "realm_backend"})
    except Exception as e:
        logger.warning(f"Could not get backend canister ID: {e}")

    # Load other canister IDs from Realm entity (set via set_canister_config)
    try:
        first_realm = Realm.load("1")
        if first_realm:
            if getattr(first_realm, "frontend_canister_id", None):
                canisters.append(
                    {
                        "canister_id": first_realm.frontend_canister_id,
                        "canister_type": "realm_frontend",
                    }
                )
            if getattr(first_realm, "token_canister_id", None):
                canisters.append(
                    {
                        "canister_id": first_realm.token_canister_id,
                        "canister_type": "token_backend",
                    }
                )
            if getattr(first_realm, "nft_canister_id", None):
                canisters.append(
                    {
                        "canister_id": first_realm.nft_canister_id,
                        "canister_type": "nft_backend",
                    }
                )
    except Exception as e:
        logger.warning(f"Could not load canister IDs from Realm entity: {e}")

    # Get registries this realm is registered with
    registries = []
    try:
        for reg in Registry.instances():
            if getattr(reg, "principal_id", None):
                registries.append(
                    {"canister_id": reg.principal_id, "canister_type": "registry"}
                )
    except Exception as e:
        logger.warning(f"Could not load registries: {e}")

    # Accounting currency
    accounting_currency = "ckBTC"
    accounting_currency_decimals = 8
    try:
        first_realm = Realm.load("1")
        if first_realm:
            accounting_currency = (
                getattr(first_realm, "accounting_currency", None) or "ckBTC"
            )
            accounting_currency_decimals = (
                getattr(first_realm, "accounting_currency_decimals", None) or 8
            )
    except Exception as e:
        logger.warning(f"Could not load accounting currency: {e}")

    # Quarter discovery
    quarters = []
    is_quarter = False
    is_capital = False
    parent_realm_canister_id = ""
    try:
        first_realm = Realm.load("1")
        if first_realm:
            is_quarter = getattr(first_realm, "is_quarter", False) or False
            is_capital = getattr(first_realm, "is_capital", False) or False
            parent_realm_canister_id = (
                getattr(first_realm, "federation_realm_id", "") or ""
            )
            # Include the capital (self) as quarter 0
            # Compute population dynamically from User.home_quarter
            own_id = ic.id().to_str()
            all_users = list(User.instances())
            quarter_entities = list(Quarter.instances())
            quarter_cids = {q.canister_id for q in quarter_entities if q.canister_id}
            capital_pop = sum(
                1 for u in all_users
                if (getattr(u, "home_quarter", "") or "") in ("", own_id)
            )
            quarters.append(
                {
                    "name": "Capital",
                    "canister_id": own_id,
                    "population": capital_pop,
                    "status": "active",
                    "is_capital": True,
                }
            )
            for q in quarter_entities:
                qcid = q.canister_id or ""
                q_pop = sum(
                    1 for u in all_users
                    if (getattr(u, "home_quarter", "") or "") == qcid
                )
                quarters.append(
                    {
                        "name": q.name or "",
                        "canister_id": qcid,
                        "population": q_pop,
                        "status": q.status or "active",
                        "is_capital": False,
                    }
                )
    except Exception as e:
        logger.warning(f"Could not load quarter info: {e}")

    # Dependency versions injected at build time (runtime detection doesn't work in WASM)
    dependencies = [
        "ic-basilisk==BASILISK_VERSION_PLACEHOLDER",
        "ic-basilisk-toolkit==IC_BASILISK_TOOLKIT_VERSION_PLACEHOLDER",
        "ic-python-db==IC_PYTHON_DB_VERSION_PLACEHOLDER",
        "ic-python-logging==IC_PYTHON_LOGGING_VERSION_PLACEHOLDER",
    ]

    # Return data in the format expected by the Status Candid type
    return {
        "version": version,
        "status": "ok",
        "realm_name": realm_name,
        "realm_logo": realm_logo,
        "realm_welcome_image": realm_welcome_image,
        "realm_welcome_message": realm_welcome_message,
        "realm_description": realm_description,
        "users_count": users_count,
        "organizations_count": organizations_count,
        "realms_count": realms_count,
        "mandates_count": mandates_count,
        "tasks_count": tasks_count,
        "transfers_count": transfers_count,
        "instruments_count": instruments_count,
        "codexes_count": codexes_count,
        "user_profiles_count": user_profiles_count,
        "disputes_count": disputes_count,
        "licenses_count": licenses_count,
        "trades_count": trades_count,
        "proposals_count": proposals_count,
        "votes_count": votes_count,
        "commit": commit_hash,
        "commit_datetime": commit_datetime,
        "extensions": extension_entries,
        "test_mode": test_mode,
        "task_manager": task_manager_status,
        "canisters": canisters,
        "registries": registries,
        "dependencies": dependencies,
        "python_version": sys.version,
        "quarters": quarters,
        "is_quarter": is_quarter,
        "is_capital": is_capital,
        "parent_realm_canister_id": parent_realm_canister_id,
        "accounting_currency": accounting_currency,
        "accounting_currency_decimals": accounting_currency_decimals,
    }
