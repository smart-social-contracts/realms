import base64
import hashlib
import importlib
import json
import sys
import traceback

import api

__basilisk_features__ = ["shell", "browse"]

from _cdk import (
    Async,
    Func,
    Opt,
    Principal,
    Query,
    Record,
    StableBTreeMap,
    Tuple,
    Variant,
    Vec,
    blob,
    ic,
    init,
    nat,
    nat16,
    post_upgrade,
    query,
    text,
    update,
    void,
)
from api.crypto import get_envelope as crypto_get_envelope
from api.crypto import group_add_member as crypto_group_add
from api.crypto import group_create as crypto_group_create
from api.crypto import group_delete as crypto_group_delete
from api.crypto import group_list as crypto_group_list
from api.crypto import group_members as crypto_group_members
from api.crypto import grant_many as crypto_grant_many
from api.crypto import group_remove_member as crypto_group_remove
from api.crypto import list_envelopes as crypto_list_envelopes
from api.crypto import revoke_many as crypto_revoke_many
from api.crypto import list_scopes as crypto_list_scopes
from api.crypto import revoke_group as crypto_revoke_group
from api.crypto import revoke_principal as crypto_revoke_principal
from api.crypto import share_with_group as crypto_share_group
from api.crypto import share_with_principal as crypto_share_principal
from api.crypto import store_envelope as crypto_store_envelope
from api.extensions import list_extensions
from api.ggg_entities import (
    list_objects,
    list_objects_paginated,
    search_objects,
)
from api.quarter_provisioning import (
    request_provision_quarter as _request_provision_quarter,
    request_casals_create_canister as _request_casals_create_canister,
    bootstrap_quarter as _bootstrap_quarter,
    parse_casals_spec as _parse_casals_spec,
)
from api.messaging import send_realm_message as _send_realm_message
from api.nft import get_nft_canister_id, mint_land_nft
from api.registry import get_registry_info, register_realm
from api.status import get_status
from api.user import (
    user_get,
    user_register,
    user_update_private_data,
    user_update_public_profile,
)
from api.vetkeys import (
    derive_vetkey,
    derive_vetkey_for_sharing,
    get_root_public_key,
    get_vetkey_public_key,
)
from api.zones import get_zone_aggregation
from core.access import _check_access, require, require_controller, set_controller
from core.cross_quarter import (
    ResolutionStatus,
    classify_ref,
    walk_chain,
)
from core.realm_ref import RealmRef
from core.task_manager import TaskManager
from ggg import Call, Codex, Task, TaskSchedule, TaskStep
from ggg.system.user_profile import Operations
from ic_python_db import Database
from ic_python_logging import get_logger

# NOTE: Record/Variant types MUST be defined in this file (not imported from
# another module) because basilisk's Candid .did generator only parses main.py's
# AST for type definitions.  Duplicated from core/candid_types_realm.py.


class PaginationInfo(Record):
    page_num: int
    page_size: int
    total_items_count: int
    total_pages: int


class CanisterInfo(Record):
    canister_id: text
    canister_type: text


class QuarterInfoRecord(Record):
    name: text
    canister_id: text
    population: nat
    status: text
    index: nat


class StatusRecord(Record):
    version: text
    status: text
    users_count: nat
    organizations_count: nat
    realms_count: nat
    mandates_count: nat
    tasks_count: nat
    transfers_count: nat
    instruments_count: nat
    codexes_count: nat
    disputes_count: nat
    licenses_count: nat
    trades_count: nat
    proposals_count: nat
    votes_count: nat
    commit: text
    commit_datetime: text
    extensions: Vec[text]
    test_mode: bool
    test_mode_ii_bypass: bool
    test_mode_user_self_registration: bool
    test_mode_demo_data: bool
    test_mode_skip_terms: bool
    test_mode_skip_passport_zkproof: bool
    realm_name: text
    realm_manifesto: text
    realm_welcome_message: text
    realm_stage: text
    open_registration: bool
    ai_assistant_enabled: bool
    user_profiles_count: nat
    canisters: Vec[CanisterInfo]
    registries: Vec[CanisterInfo]
    dependencies: Vec[text]
    python_version: text
    quarters: Vec[QuarterInfoRecord]
    is_quarter: bool
    parent_realm_canister_id: text
    accounting_currency: text
    accounting_currency_decimals: nat
    logo_url: text
    background_image_url: text
    file_registry_canister_id: text
    marketplace_canister_id: text
    realm_logo: text
    realm_description: text
    realm_welcome_image: text


class UserGetRecord(Record):
    principal: Principal
    profiles: Vec[text]
    nickname: text
    avatar: text
    private_data: text
    assigned_quarter: text


class ObjectsListRecordPaginated(Record):
    objects: Vec[text]
    pagination: PaginationInfo


class ObjectsListRecord(Record):
    objects: Vec[text]


class ExtensionsListRecord(Record):
    extensions: Vec[text]


class RealmResponseData(Variant):
    status: StatusRecord
    userGet: UserGetRecord
    error: text
    message: text
    objectsList: ObjectsListRecord
    objectsListPaginated: ObjectsListRecordPaginated
    extensionsList: ExtensionsListRecord


class RealmResponse(Record):
    success: bool
    data: RealmResponseData


class EnvelopeRecord(Record):
    scope: text
    principal_id: text
    wrapped_dek: text


class EnvelopeListRecord(Record):
    envelopes: Vec["EnvelopeRecord"]


class ScopeListRecord(Record):
    scopes: Vec[text]


class GroupRecord(Record):
    name: text
    description: text


class GroupListRecord(Record):
    groups: Vec["GroupRecord"]


class GroupMemberRecord(Record):
    principal_id: text
    role: text


class GroupMembersRecord(Record):
    members: Vec["GroupMemberRecord"]


class CryptoResponseData(Variant):
    envelope: EnvelopeRecord
    envelopeList: EnvelopeListRecord
    scopeList: ScopeListRecord
    group: GroupRecord
    groupList: GroupListRecord
    groupMembers: GroupMembersRecord
    error: text
    message: text


class CryptoResponse(Record):
    success: bool
    data: CryptoResponseData


class ExtensionCallArgs(Record):
    extension_name: text
    function_name: text
    args: text


class ExtensionCallResponse(Record):
    success: bool
    response: text


storage = StableBTreeMap[str, str](memory_id=1, max_key_size=100, max_value_size=10000)
Database.init(db_storage=storage, audit_enabled=True)

def _get_frontend_canister_id() -> str:
    """Read the frontend canister ID from the Realm entity."""
    try:
        from ggg import Realm
        realm = list(Realm.instances())[0] if Realm.instances() else None
        return str(realm.frontend_canister_id or "") if realm else ""
    except Exception:
        return ""

logger = get_logger("main")

def _make_codex_proxy(codex_name: str, func_name: str, method_type: str = "method"):
    """Create a dynamic proxy that always exec()s the latest Codex code.

    Instead of caching a function extracted from codex code at bind time,
    this proxy re-reads the codex on every call so that governance proposals
    that update a codex take effect immediately without a canister restart
    or a reload_entity_method_overrides() call.
    """

    def _proxy(*args, **kwargs):
        import ggg as _ggg
        from _cdk import Async as _Async
        from ggg import Codex as _Codex
        from ic_python_logging import get_logger as _get_logger

        target = _Codex[codex_name]
        if not target or not target.code:
            raise RuntimeError(f"Codex '{codex_name}' not found or has no code")
        ns = {
            "ic": ic,
            "logger": _get_logger(f"codex.{codex_name}"),
            "ggg": _ggg,
            "Async": _Async,
        }
        exec(str(target.code), ns)
        fn = ns.get(func_name)
        if not fn:
            raise RuntimeError(
                f"Function '{func_name}' not found in Codex '{codex_name}'"
            )
        return fn(*args, **kwargs)

    _proxy.__qualname__ = f"codex_proxy<{codex_name}.{func_name}>"
    _proxy.__name__ = func_name
    return _proxy


# HTTP types used by http_transform endpoint
from _cdk import (
    HttpResponse,
    HttpTransformArgs,
)

# Types for incoming HTTP requests (http_request query)
Header = Tuple[str, str]


class HttpRequest(Record):
    method: str
    url: str
    headers: Vec["Header"]
    body: blob


class HttpResponseIncoming(Record):
    status_code: nat16
    headers: Vec["Header"]
    body: blob
    streaming_strategy: Opt["StreamingStrategy"]
    upgrade: Opt[bool]


class StreamingStrategy(Variant):
    Callback: "CallbackStrategy"


class CallbackStrategy(Record):
    callback: "Callback"  # type: ignore
    token: "StreamingToken"


Callback = Func(Query[["StreamingToken"], "StreamingCallbackHttpResponse"])


class StreamingCallbackHttpResponse(Record):
    body: blob
    token: Opt["StreamingToken"]


class StreamingToken(Record):
    key: str


@query
def status() -> RealmResponse:
    try:
        logger.info("Status query executed")
        return RealmResponse(
            success=True, data=RealmResponseData(status=StatusRecord(**get_status()))
        )
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def get_quarter_info() -> RealmResponse:
    """Get quarter information for this realm (workaround for Basilisk Record field limitation)"""
    try:
        import json as _json

        from ggg import Quarter, Realm

        quarters = []
        is_quarter = False
        is_capital = False
        parent_realm_canister_id = ""

        first_realm = Realm.load("1")
        if first_realm:
            is_quarter = bool(getattr(first_realm, "is_quarter", False))
            is_capital = bool(getattr(first_realm, "is_capital", False))
            parent_realm_canister_id = (
                getattr(first_realm, "federation_realm_id", "") or ""
            )
            from ggg import User
            own_id = ic.id().to_str()
            quarter_entities = list(Quarter.instances())

            if quarter_entities:
                all_users = list(User.instances())
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
                        "index": 0,
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
                            "index": int(getattr(q, "index", 0) or 0),
                            "is_capital": False,
                        }
                    )
            else:
                quarters.append(
                    {
                        "name": "Capital",
                        "canister_id": own_id,
                        "population": User.count(),
                        "status": "active",
                        "index": 0,
                        "is_capital": True,
                    }
                )

        result = _json.dumps(
            {
                "quarters": quarters,
                "is_quarter": is_quarter,
                "is_capital": is_capital,
                "parent_realm_canister_id": parent_realm_canister_id,
            }
        )
        return RealmResponse(success=True, data=RealmResponseData(message=result))
    except Exception as e:
        logger.error(f"Error getting quarter info: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def get_extensions() -> RealmResponse:
    """Get all available extensions with their metadata"""
    return list_extensions(ic.caller().to_str())


def _assign_quarter(principal: str, realm, quarters, preferred_quarter: str) -> str:
    """Assign a quarter via federation_codex, or fall back to random.

    The federation codex may define an ``assign_quarter(principal, quarters,
    preferred_quarter)`` function.  It receives the list of active Quarter
    entities and should return a canister_id string.  If the codex raises,
    the error propagates to the caller so the user gets a clear rejection
    reason (e.g. "quarter is full").

    When no codex is present the default behaviour is deterministic random
    assignment (hash of principal) which guarantees uniform load.
    """
    active_quarters = [q for q in quarters if q.status == "active"]
    if not active_quarters:
        return ""

    codex = realm.federation_codex
    if codex and codex.code:
        ns = {}
        exec(str(codex.code), ns)
        assign_fn = ns.get("assign_quarter")
        if assign_fn:
            result = assign_fn(principal, active_quarters, preferred_quarter)
            if result:
                return str(result)

    # Default: deterministic random (hash-based)
    idx = hash(principal) % len(active_quarters)
    return active_quarters[idx].canister_id


@update
def join_realm(profile: str, preferred_quarter: text, invite_code_checksum_hex: text) -> RealmResponse:
    """Register the caller in the realm.

    Registration modes:
    - Code-based (default): caller must provide a valid invite_code.
      The code's profile determines the granted role.
    - Open registration: if Realm.open_registration is True, members
      may join without a code. Admin always requires a code.
    - Controller bypass: IC controllers can join with any profile
      without a code (for manual dfx deploys).
    - Test mode: when test_mode_user_self_registration (or
      test_mode_ii_bypass) is True, the sha256-matched codes "admin",
      "member", and "dev"/"developer" grant the respective profiles, so
      a caller may self-register without a real invite code.
    """
    try:
        caller = ic.caller().to_str()
        from ggg import Quarter, Realm, User

        realm = Realm.load("1")
        has_invite = bool(invite_code_checksum_hex and invite_code_checksum_hex.strip())
        granted_profile = profile

        # --- Determine access ---

        is_controller = False
        try:
            is_controller = ic.is_controller(caller)
        except Exception:
            pass

        if has_invite:
            # Test mode shortcuts: sha256("admin") / sha256("member") / sha256("dev") / sha256("developer") grant respective profiles
            _ADMIN_TEST_CODE_CHECKSUM_HEX = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
            _MEMBER_TEST_CODE_CHECKSUM_HEX = "e31ab643c44f7a0ec824b59d1194d60dac334200d845e61d2d289daa0f087ea4"
            _DEV_TEST_CODE_CHECKSUM_HEX = "ef260e9aa3c673af240d17a2660480361a8e081d1ffeca2a5ed0e3219fc18567"
            _DEVELOPER_TEST_CODE_CHECKSUM_HEX = "88fa0d759f845b47c044c2cd44e29082cf6fea665c30c146374ec7c8f3d699e3"
            _test_bypass = bool(getattr(realm, "test_mode_user_self_registration", False)) or bool(
                getattr(realm, "test_mode_ii_bypass", False)
            )
            if _test_bypass and invite_code_checksum_hex == _ADMIN_TEST_CODE_CHECKSUM_HEX:
                granted_profile = "admin"
            elif _test_bypass and invite_code_checksum_hex == _MEMBER_TEST_CODE_CHECKSUM_HEX:
                granted_profile = "member"
            elif _test_bypass and invite_code_checksum_hex in (_DEV_TEST_CODE_CHECKSUM_HEX, _DEVELOPER_TEST_CODE_CHECKSUM_HEX):
                granted_profile = "developer"
            else:
                # Code-based path: validate and consume the invite code
                from ggg.system.registration_code import consume_registration_code
                consume_result = consume_registration_code(invite_code_checksum_hex, caller)

                if not consume_result.get("success"):
                    error_msg = consume_result.get("error", "Invalid or expired invitation code")
                    return RealmResponse(
                        success=False,
                        data=RealmResponseData(error=error_msg),
                    )

                consume_data = consume_result.get("data", {})
                invite_profile = (consume_data if isinstance(consume_data, dict) else consume_result).get("profile", "member")
                if profile and profile != invite_profile:
                    return RealmResponse(
                        success=False,
                        data=RealmResponseData(
                            error=f"Invitation grants '{invite_profile}' profile, but '{profile}' was requested"
                        ),
                    )
                granted_profile = invite_profile

        elif is_controller:
            # Controllers can join with any profile without a code
            pass

        elif profile == "admin":
            _test_bypass = bool(getattr(realm, "test_mode_user_self_registration", False)) or bool(
                getattr(realm, "test_mode_ii_bypass", False)
            )
            if not _test_bypass:
                return RealmResponse(
                    success=False,
                    data=RealmResponseData(
                        error="Admin registration requires an invitation code."
                    ),
                )

        else:
            # Member/developer join without code: allowed if open_registration is on or test bypass
            open_reg = realm and realm.open_registration
            _test_bypass = bool(getattr(realm, "test_mode_user_self_registration", False)) or bool(
                getattr(realm, "test_mode_ii_bypass", False)
            )
            if not open_reg and not _test_bypass:
                return RealmResponse(
                    success=False,
                    data=RealmResponseData(
                        error="Registration requires an invitation code."
                    ),
                )

        # --- Coordinator-only capital guard (issue #156) ---
        # Once this realm acts as a capital (it is not itself a quarter and has
        # >=1 active sub-quarter) it stops accepting brand-new members directly:
        # new members register on a quarter (the /join page routes them there).
        # Controllers and test-mode bypass stay exempt so admin tooling and demos
        # still work, and existing members can idempotently re-join.
        _is_quarter_realm = bool(getattr(realm, "is_quarter", False))
        _test_bypass_guard = bool(getattr(realm, "test_mode_user_self_registration", False)) or bool(
            getattr(realm, "test_mode_ii_bypass", False)
        )
        if realm and not _is_quarter_realm and not is_controller and not _test_bypass_guard:
            own_id = ic.id().to_str()
            has_active_sub = any(
                (q.canister_id and q.canister_id != own_id and (q.status or "active") == "active")
                for q in Quarter.instances()
            )
            already_member = False
            try:
                already_member = bool(User[caller])
            except Exception:
                already_member = False
            if has_active_sub and not already_member:
                return RealmResponse(
                    success=False,
                    data=RealmResponseData(
                        error="This realm is coordinator-only. Please join through a quarter."
                    ),
                )

        # --- Register user and assign quarter ---

        user = user_register(caller, granted_profile)
        profiles = Vec[text]()
        if "profiles" in user and user["profiles"]:
            for p in user["profiles"]:
                profiles.append(p)

        assigned_quarter_canister_id = ""
        quarters = list(Quarter.instances()) if realm else []
        if realm and quarters:
            assigned_quarter_canister_id = _assign_quarter(
                caller, realm, quarters, preferred_quarter
            )
            u = User[caller]
            if u and assigned_quarter_canister_id:
                u.home_quarter = assigned_quarter_canister_id

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                userGet=UserGetRecord(
                    principal=Principal.from_str(user["principal"]),
                    profiles=profiles,
                    nickname=user.get("nickname", ""),
                    avatar=user.get("avatar", ""),
                    private_data=user.get("private_data", ""),
                    assigned_quarter=assigned_quarter_canister_id,
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require_controller
def store_admin_invite_hash(args_json: text) -> RealmResponse:
    """Controller-only endpoint to store a pre-computed admin invite hash."""
    try:
        args = json.loads(args_json)
        code_hash = args.get("code_hash", "").strip()
        expires_in_hours = args.get("expires_in_hours", 24)
        if not code_hash:
            return RealmResponse(
                success=False,
                data=RealmResponseData(error="code_hash is required"),
            )

        from ggg.system.registration_code import create_registration_code
        reg_code = create_registration_code(
            code_hash=code_hash,
            profile="admin",
            max_uses=1,
            expires_in_hours=expires_in_hours,
            created_by=ic.caller().to_str(),
            user_id="installer",
        )
        result = {
            "success": True,
            "data": {
                "code_hash": code_hash[:8],
                "expires_at": reg_code.expires_at,
                "profile": "admin",
            },
        }
        result_str = json.dumps(result)
        return RealmResponse(
            success=True,
            data=RealmResponseData(message=result_str),
        )
    except Exception as e:
        logger.error(f"Error storing admin invite hash: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


# ── Principal delegation (Power of Attorney) ─────────────────────────────


@update
def grant_delegation_json(args: text) -> text:
    """Grant scoped act-on-behalf authority from grantor to delegate.

    JSON args: grantor, delegate, scope ({operations: [...]} or {all: true}),
    optional label, expires_in_hours (default 168), requires_acceptance (default true).
    Caller must be grantor or realm admin.
    """
    try:
        from core.delegation import grant_delegation

        params = json.loads(args) if args else {}
        grantor = (params.get("grantor") or "").strip()
        delegate = (params.get("delegate") or "").strip()
        scope = params.get("scope") or {}
        caller = ic.caller().to_str()

        if caller != grantor and not _check_access(caller, Operations.REALM_ADMIN):
            return json.dumps({
                "success": False,
                "error": "Only the grantor or a realm admin may create this delegation",
            })

        result = grant_delegation(
            grantor,
            delegate,
            scope,
            label=(params.get("label") or "").strip(),
            expires_in_hours=int(params.get("expires_in_hours") or 168),
            requires_acceptance=bool(params.get("requires_acceptance", True)),
            granted_by=caller,
        )
        return json.dumps(result)
    except Exception as e:
        logger.error(f"grant_delegation_json error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
def accept_delegation_json(args: text) -> text:
    """Accept a pending delegation. JSON args: delegation_id."""
    try:
        from core.delegation import accept_delegation

        params = json.loads(args) if args else {}
        delegation_id = (params.get("delegation_id") or "").strip()
        if not delegation_id:
            return json.dumps({"success": False, "error": "delegation_id is required"})
        return json.dumps(accept_delegation(delegation_id))
    except Exception as e:
        logger.error(f"accept_delegation_json error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
def revoke_delegation_json(args: text) -> text:
    """Revoke a delegation. JSON args: delegation_id."""
    try:
        from core.delegation import revoke_delegation

        params = json.loads(args) if args else {}
        delegation_id = (params.get("delegation_id") or "").strip()
        if not delegation_id:
            return json.dumps({"success": False, "error": "delegation_id is required"})
        return json.dumps(revoke_delegation(delegation_id))
    except Exception as e:
        logger.error(f"revoke_delegation_json error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@query
def list_delegations_json() -> text:
    """List delegations where the caller is grantor or delegate."""
    try:
        from core.delegation import list_delegations_for_caller

        return json.dumps(list_delegations_for_caller())
    except Exception as e:
        logger.error(f"list_delegations_json error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.SELF_CHANGE_QUARTER)
def change_quarter(new_quarter_canister_id: text) -> RealmResponse:
    """Change the caller's assigned quarter."""
    try:
        from ggg import Quarter, Realm

        caller = ic.caller().to_str()

        # Validate the target quarter exists and is active
        realm = Realm.load("1")
        if not realm:
            return RealmResponse(
                success=False, data=RealmResponseData(error="Realm not found")
            )

        # The capital (self) counts as quarter 0
        own_canister_id = ic.id().to_str()
        is_capital_target = new_quarter_canister_id == own_canister_id

        if not is_capital_target:
            quarters = list(Quarter.instances())
            target = None
            for q in quarters:
                if q.canister_id == new_quarter_canister_id and q.status == "active":
                    target = q
                    break

            if not target:
                return RealmResponse(
                    success=False,
                    data=RealmResponseData(
                        error=f"Quarter '{new_quarter_canister_id}' not found or not active"
                    ),
                )

        # Run codex eligibility check if available
        codex = realm.federation_codex
        if codex and codex.code:
            ns = {}
            exec(str(codex.code), ns)
            assign_fn = ns.get("assign_quarter")
            if assign_fn:
                target = target if not is_capital_target else None
                assign_fn(caller, [target] if target else [], new_quarter_canister_id)

        # Persist the new assignment on the User entity
        from ggg import User

        u = User[caller]
        if u:
            u.home_quarter = new_quarter_canister_id

        return RealmResponse(
            success=True,
            data=RealmResponseData(message=new_quarter_canister_id),
        )
    except Exception as e:
        logger.error(f"Error changing quarter: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def get_my_principal() -> text:
    return ic.caller().to_str()


@query
def get_canister_id() -> text:
    """Return this canister's principal ID"""
    return ic.id().to_str()


def _set_canister_config_impl(
    frontend_canister_id=None,
    token_canister_id=None,
    nft_canister_id=None,
    file_registry_canister_id=None,
    marketplace_canister_id=None,
    installed_version=None,
    network=None,
    test_flags_json=None,
) -> RealmResponse:
    """
    Set canister IDs and metadata for this realm (admin only).
    Called post-deployment to enable canister discovery via status().

    Args:
        frontend_canister_id: The realm_frontend canister ID
        token_canister_id: Optional token_backend canister ID
        nft_canister_id: Optional nft_backend canister ID
        file_registry_canister_id: Optional file_registry canister ID (shared infra)
        marketplace_canister_id: Optional marketplace_backend canister ID (shared infra)
        installed_version: Optional deployed version string (e.g. "0.3.5")
        network: Optional IC network name (e.g. "test", "staging", "demo", "ic")
        test_flags_json: Optional JSON with test mode flags, e.g.
            {"test_mode":true,"ii_bypass":true,"user_self_registration":true,...}
            Rejected on mainnet (network=="ic") for security.
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
        if not realm:
            return RealmResponse(
                success=False, data=RealmResponseData(error="Realm not found")
            )

        if frontend_canister_id:
            realm.frontend_canister_id = frontend_canister_id
        if token_canister_id:
            realm.token_canister_id = token_canister_id
        if nft_canister_id:
            realm.nft_canister_id = nft_canister_id
        if file_registry_canister_id:
            realm.file_registry_canister_id = file_registry_canister_id
        if marketplace_canister_id:
            realm.marketplace_canister_id = marketplace_canister_id
        if installed_version:
            realm.installed_version = installed_version
        if network:
            realm.network = network

        # Apply test flags (network-gated: rejected on mainnet)
        if test_flags_json:
            effective_network = network or getattr(realm, "network", "") or ""
            flags = json.loads(test_flags_json)
            any_flag_true = any(v for v in flags.values() if v)
            if any_flag_true and effective_network == "ic":
                return RealmResponse(
                    success=False,
                    data=RealmResponseData(
                        error="Test mode flags cannot be enabled on mainnet (network=ic)"
                    ),
                )
            _FLAG_MAP = {
                "test_mode": "test_mode",
                "ii_bypass": "test_mode_ii_bypass",
                "user_self_registration": "test_mode_user_self_registration",
                "demo_data": "test_mode_demo_data",
                "skip_terms": "test_mode_skip_terms",
                "skip_passport_zkproof": "test_mode_skip_passport_zkproof",
                "skip_authentication": "test_mode_skip_authentication",
            }
            for key, attr in _FLAG_MAP.items():
                if key in flags:
                    setattr(realm, attr, bool(flags[key]))

        logger.info(
            f"Updated canister config: frontend={frontend_canister_id}, "
            f"token={token_canister_id}, nft={nft_canister_id}, "
            f"file_registry={file_registry_canister_id}, marketplace={marketplace_canister_id}, "
            f"version={installed_version}, network={network}, "
            f"test_flags={test_flags_json}"
        )

        return RealmResponse(
            success=True, data=RealmResponseData(message="Canister config updated")
        )
    except Exception as e:
        logger.error(
            f"Error setting canister config: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def set_canister_config(
    frontend_canister_id: Opt[text],
    token_canister_id: Opt[text],
    nft_canister_id: Opt[text],
    file_registry_canister_id: Opt[text],
    marketplace_canister_id: Opt[text],
    installed_version: Opt[text] = None,
    network: Opt[text] = None,
    test_flags_json: Opt[text] = None,
) -> RealmResponse:
    """Set canister IDs and metadata for this realm (admin only). Candid multi-arg
    form; see _set_canister_config_impl for the full argument docs."""
    return _set_canister_config_impl(
        frontend_canister_id,
        token_canister_id,
        nft_canister_id,
        file_registry_canister_id,
        marketplace_canister_id,
        installed_version,
        network,
        test_flags_json,
    )


@update
@require(Operations.REALM_ADMIN)
def set_canister_config_json(args: text) -> text:
    """JSON text-in / text-out variant of set_canister_config.

    Lets a single declarative call configure a realm post-deploy — e.g. a Casals
    arrangement step ``{target, method: "set_canister_config_json", args: {...}}``.
    The multi-arg Candid form (set_canister_config) cannot be expressed as one
    text argument; this wrapper can.

    Args (JSON, all optional): {frontend_canister_id, token_canister_id,
    nft_canister_id, file_registry_canister_id, marketplace_canister_id,
    installed_version, network, and either test_flags_json (a JSON string) or
    test_flags (a JSON object, e.g. {"test_mode":true,"demo_data":true})}.

    Returns: {"success": bool, "message"?: str, "error"?: str}.
    """
    try:
        params = json.loads(args) if args else {}
        flags = params.get("test_flags_json")
        if flags is None and isinstance(params.get("test_flags"), dict):
            flags = json.dumps(params["test_flags"])
        resp = _set_canister_config_impl(
            frontend_canister_id=params.get("frontend_canister_id"),
            token_canister_id=params.get("token_canister_id"),
            nft_canister_id=params.get("nft_canister_id"),
            file_registry_canister_id=params.get("file_registry_canister_id"),
            marketplace_canister_id=params.get("marketplace_canister_id"),
            installed_version=params.get("installed_version"),
            network=params.get("network"),
            test_flags_json=flags,
        )
        data = getattr(resp, "data", None)
        out = {"success": bool(getattr(resp, "success", False))}
        msg = getattr(data, "message", None) if data is not None else None
        err = getattr(data, "error", None) if data is not None else None
        if msg:
            out["message"] = msg
        if err:
            out["error"] = err
        return json.dumps(out)
    except Exception as e:
        logger.error(f"set_canister_config_json error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.QUARTER_REGISTER)
def register_quarter(quarter_name: text, quarter_canister_id: text) -> RealmResponse:
    """
    Register a new quarter under this realm.
    Creates a Quarter entity linked to the realm.

    Args:
        quarter_name: Human-readable name for the quarter
        quarter_canister_id: The canister principal ID of the quarter backend
    """
    try:
        from ggg import Quarter, Realm

        realm = Realm.load("1")
        if not realm:
            return RealmResponse(
                success=False, data=RealmResponseData(error="Realm not found")
            )

        # Check for duplicate canister ID
        for q in Quarter.instances():
            if q.canister_id == quarter_canister_id:
                return RealmResponse(
                    success=False,
                    data=RealmResponseData(
                        error=f"Quarter with canister ID {quarter_canister_id} already registered"
                    ),
                )

        # Assign a stable, monotonic catalog index (capital is 0, quarters >=1).
        # Users can recover their home quarter from this small integer without
        # any central per-user location index.
        next_index = 1
        for q in Quarter.instances():
            try:
                next_index = max(next_index, int(q.index or 0) + 1)
            except Exception:
                continue

        quarter = Quarter(
            name=quarter_name,
            canister_id=quarter_canister_id,
            index=next_index,
        )
        quarter.federation = realm

        logger.info(
            f"Registered quarter '{quarter_name}' (canister: {quarter_canister_id}, index: {next_index})"
        )

        # Keep the capital's view of quarter populations fresh now that a
        # sub-quarter exists (issue #156). Best-effort: registration must not
        # fail if task seeding hiccups.
        try:
            ensure_population_sync_task()
        except Exception as e:
            logger.error(f"ensure_population_sync_task (register_quarter) failed: {e}")

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                message=f"Quarter '{quarter_name}' registered with ID {quarter._id} (index {next_index})"
            ),
        )
    except Exception as e:
        logger.error(f"Error registering quarter: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.QUARTER_DEREGISTER)
def deregister_quarter(quarter_canister_id: text) -> RealmResponse:
    """
    Remove a quarter from this realm by its canister ID.

    Args:
        quarter_canister_id: The canister principal ID of the quarter to remove
    """
    try:
        from ggg import Quarter

        for q in Quarter.instances():
            if q.canister_id == quarter_canister_id:
                q.delete()
                logger.info(
                    f"Deregistered quarter with canister ID {quarter_canister_id}"
                )
                return RealmResponse(
                    success=True,
                    data=RealmResponseData(message=f"Quarter '{q.name}' deregistered"),
                )

        return RealmResponse(
            success=False,
            data=RealmResponseData(
                error=f"Quarter with canister ID {quarter_canister_id} not found"
            ),
        )
    except Exception as e:
        logger.error(f"Error deregistering quarter: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.QUARTER_CONFIGURE)
def set_quarter_config(parent_realm_canister_id: text) -> RealmResponse:
    """
    Configure this realm as a quarter of a parent realm.
    Sets is_quarter=True and stores the parent realm's canister ID.

    Args:
        parent_realm_canister_id: The canister principal ID of the parent realm
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
        if not realm:
            return RealmResponse(
                success=False, data=RealmResponseData(error="Realm not found")
            )

        realm.is_quarter = True
        realm.federation_realm_id = parent_realm_canister_id

        logger.info(f"Configured realm as quarter of parent {parent_realm_canister_id}")

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                message=f"Realm configured as quarter of {parent_realm_canister_id}"
            ),
        )
    except Exception as e:
        logger.error(
            f"Error setting quarter config: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.QUARTER_CONFIGURE)
def bootstrap_as_quarter(args: text) -> text:
    """Seed a quarter-local self-bootstrap to bring a freshly minted quarter to
    parity (config + federation codex + extensions).

    Called by the capital immediately after Casals mints this canister. Because
    Casals co-adds the capital (the stand commander) as a controller of canisters
    in its stand, the capital passes the controller bypass on this gated call.

    Rather than install everything in this single message (impossible past a
    handful of extensions, given the IC instruction/time limit), this endpoint:

      1. Does the cheap config synchronously: mark as a quarter of the parent and
         trust the parent for future inter-canister calls.
      2. Records an install *plan* (codex + extensions) on the local ``Realm``.
      3. Seeds a recurring ``TaskManager`` task that installs **one item per
         tick** with retry/backoff (see ``core.quarter_bootstrap``).

    Returns immediately; progress is observable via ``get_bootstrap_status``.

    Args (JSON)::

        {
          "parent_realm_canister_id": "ihbn6-...",   # required
          "registry_canister_id": "iebdk-...",        # required for codex/extensions
          "codices": [{"codex_id": "...", "version": null, "run_init": true}, ...],
          "codex": {"codex_id": "...", "version": null} | null,  # back-compat single
          "extensions": [{"ext_id": "...", "version": null}, ...],
          "frontend_canister_id": "",                  # optional (backend-only quarters)
          "config": {                                  # capital's runtime config + branding
            "name": "Agora", "manifesto": "...", "welcome_message": "...",
            "open_registration": false, "network": "staging",
            "file_registry_canister_id": "...", "test_flags": {...}, ...
          }
        }

    The capital auto-derives ``codices``/``extensions`` from its own live
    installed set (see ``derive_capital_install_set``) so the quarter mirrors
    the capital; ``codex`` (single) is still accepted for older callers.
    """
    try:
        params = json.loads(args or "{}")
    except Exception as e:
        return json.dumps({"success": False, "error": f"bad args: {e}"})

    parent = (params.get("parent_realm_canister_id") or "").strip()

    try:
        from ggg import Realm
        from core.quarter_bootstrap import (
            apply_quarter_config,
            build_bootstrap_plan,
            save_state,
            seed_bootstrap_task,
        )

        realm = Realm.load("1")
        if not realm:
            return json.dumps({"success": False, "error": "Realm not found on quarter"})

        # 1. Synchronous config: mark as a quarter + trust the parent.
        realm.is_quarter = True
        realm.federation_realm_id = parent
        if parent:
            trusted = [p.strip() for p in str(realm.trusted_principals or "").split(",") if p.strip()]
            if parent not in trusted:
                trusted.append(parent)
                realm.trusted_principals = ",".join(trusted)

        # 1b. Mirror the capital's runtime config + branding so the quarter is
        # immediately branded and registration-ready (issue #156). The codex/
        # extension *code* arrives via the install plan below; this brings the
        # *identity* + runtime flags (name, manifesto, registration, canister
        # ids) that otherwise only come from out-of-band arrangement steps.
        applied_config = []
        cfg = params.get("config")
        if isinstance(cfg, dict) and cfg:
            try:
                applied_config = apply_quarter_config(realm, cfg)
            except Exception as e:
                logger.error(f"apply_quarter_config failed: {e}\n{traceback.format_exc()}")

        # 2. Record the install plan for the local driver.
        plan = build_bootstrap_plan(params)
        save_state(realm, plan)

        # 3. Seed the recurring TaskManager task that installs one item per tick.
        seeded = False
        if plan.get("items"):
            try:
                seed_bootstrap_task()
                seeded = True
            except Exception as e:
                logger.error(f"Failed to seed quarter bootstrap task: {e}\n{traceback.format_exc()}")

        planned = len(plan.get("items", []))
        status = "bootstrapping" if seeded else ("complete" if not planned else "blocked")
        logger.info(
            f"bootstrap_as_quarter seeded plan ({planned} items, parent={parent}, "
            f"status={status}, config_applied={len(applied_config)})"
        )
        return json.dumps({
            "success": True,
            "status": status,
            "parent": parent,
            "planned": planned,
            "seeded": seeded,
            "config_applied": applied_config,
        })
    except Exception as e:
        logger.error(f"bootstrap_as_quarter failed: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@query
def get_bootstrap_status() -> text:
    """Report this quarter's self-bootstrap progress (issue #156).

    Returns the persisted install plan + cursor so the capital (or an operator)
    can watch a freshly minted quarter reach parity without polling the registry.
    """
    try:
        from ggg import Realm
        from core.quarter_bootstrap import load_state

        realm = Realm.load("1")
        if not realm:
            return json.dumps({"success": False, "error": "Realm not found"})
        state = load_state(realm)
        if not state:
            return json.dumps({"success": True, "status": "none", "plan": None})
        items = state.get("items") or []
        return json.dumps({
            "success": True,
            "status": state.get("status", "unknown"),
            "cursor": int(state.get("cursor") or 0),
            "total": len(items),
            "done": state.get("done", []),
            "failed": state.get("failed", []),
            "current": items[int(state.get("cursor") or 0)].get("id")
            if int(state.get("cursor") or 0) < len(items) else None,
        })
    except Exception as e:
        logger.error(f"get_bootstrap_status failed: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.QUARTER_SECEDE)
def declare_independence() -> RealmResponse:
    """Secede from the federation, becoming an independent realm.

    Sets is_quarter=False, is_capital=False, clears federation_realm_id.
    All local users, data, governance, and extensions remain intact.
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
        if not realm:
            return RealmResponse(
                success=False, data=RealmResponseData(error="Realm not found")
            )

        if not realm.is_quarter:
            return RealmResponse(
                success=False,
                data=RealmResponseData(error="This realm is not a quarter of any federation"),
            )

        old_federation = realm.federation_realm_id or "unknown"
        realm.is_quarter = False
        realm.is_capital = False
        realm.federation_realm_id = ""

        logger.info(f"Declared independence from federation {old_federation}")

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                message=f"Independence declared. Former federation: {old_federation}"
            ),
        )
    except Exception as e:
        logger.error(f"Error declaring independence: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.QUARTER_JOIN_FEDERATION)
def join_federation(capital_canister_id: text, as_capital: bool = False) -> RealmResponse:
    """Join an existing federation as a quarter.

    Sets is_quarter=True, stores the capital's canister ID, and optionally
    designates this quarter as the capital.

    Args:
        capital_canister_id: The canister principal ID of the federation's capital
        as_capital: If True, designate this quarter as the capital
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
        if not realm:
            return RealmResponse(
                success=False, data=RealmResponseData(error="Realm not found")
            )

        if realm.is_quarter:
            return RealmResponse(
                success=False,
                data=RealmResponseData(
                    error=f"Already a quarter of federation {realm.federation_realm_id}"
                ),
            )

        realm.is_quarter = True
        realm.is_capital = as_capital
        realm.federation_realm_id = capital_canister_id

        role = "capital" if as_capital else "quarter"
        logger.info(f"Joined federation {capital_canister_id} as {role}")

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                message=f"Joined federation {capital_canister_id} as {role}"
            ),
        )
    except Exception as e:
        logger.error(f"Error joining federation: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


# ── Cross-quarter / cross-realm addressing (realm:// refs) ─────────────────
# See issue #156. A canister id is a canister id, so the same machinery serves
# both cross-quarter (same realm) and cross-realm references; only the locator
# fallback (gossip vs registry) differs by scope.


def _load_local_entity(entity_type: str, entity_id: str):
    """Return the live entity for (type, id) on THIS canister, or None."""
    try:
        results = list_objects([(entity_type, entity_id)])
        return results[0] if results else None
    except Exception:
        return None


def _find_migration_stub(subject: str):
    """Return the EntityMigration forwarding stub for ``subject`` here, or None."""
    try:
        from ggg import EntityMigration

        for m in EntityMigration.instances():
            if m.subject == subject:
                return m
        return None
    except Exception:
        return None


def _local_stub_next(ref) -> str:
    """stub_lookup for walk_chain: only this canister's stubs are visible.

    A quarter only knows the forwarding stubs it stored itself, so chain
    resolution beyond the first remote hop is the caller's/frontend's job
    (hop to ``next_ref``'s canister and call ``resolve_ref`` again).
    """
    self_id = ic.id().to_str()
    if not ref.is_local(self_id):
        return ""
    stub = _find_migration_stub(ref.entity_id)
    return stub.next_ref if (stub and stub.next_ref) else ""


@query
def resolve_ref(ref_uri: text) -> text:
    """Resolve a ``realm://<canister>/<Type>/<id>`` reference.

    Returns JSON describing where the entity currently lives:

    * ``status=local``  — entity is on this canister; ``object`` is its JSON.
    * ``status=remote`` — entity is elsewhere; ``final_ref`` + ``canister_id``
      tell the frontend which backend to switch its actor to.
    * ``status=moved``  — a local forwarding stub points onward (``final_ref``).
    * ``status=not_found`` / ``invalid`` / ``loop`` / ``too_deep`` on failure.
    """
    try:
        self_id = ic.id().to_str()
        result = walk_chain(
            ref_uri,
            self_id,
            local_lookup=lambda r: _load_local_entity(r.entity_type, r.entity_id),
            stub_lookup=_local_stub_next,
        )
        out = {
            "status": result["status"],
            "final_ref": result.get("final_ref"),
            "hops": result.get("hops", []),
        }
        final = result.get("final_ref")
        if final:
            fref = RealmRef.try_parse(final)
            if fref:
                out["canister_id"] = fref.canister_id
                out["entity_type"] = fref.entity_type
                out["entity_id"] = fref.entity_id
        if result["status"] == ResolutionStatus.LOCAL and final:
            fref = RealmRef.parse(final)
            obj = _load_local_entity(fref.entity_type, fref.entity_id)
            if obj is not None:
                out["object"] = obj.serialize()
        return json.dumps(out)
    except Exception as e:
        logger.error(f"Error resolving ref {ref_uri!r}: {e}\n{traceback.format_exc()}")
        return json.dumps({"status": "error", "error": str(e)})


@query
def get_objects_by_ref(refs: Vec[text]) -> text:
    """Batch-resolve realm refs. Local hits return objects; remote return routes.

    Returns JSON ``{"results": [ {ref, status, object?, canister_id?, ...}, ... ]}``.
    """
    try:
        self_id = ic.id().to_str()
        results = []
        for ref_uri in refs:
            info = classify_ref(ref_uri, self_id)
            entry = {"ref": ref_uri, "status": info["status"]}
            if info["status"] == ResolutionStatus.LOCAL:
                obj = _load_local_entity(info["entity_type"], info["entity_id"])
                if obj is not None:
                    entry["object"] = obj.serialize()
                else:
                    # Local ref but no entity — maybe it moved on.
                    stub = _find_migration_stub(info["entity_id"])
                    if stub and stub.next_ref:
                        entry["status"] = ResolutionStatus.MOVED
                        entry["final_ref"] = stub.next_ref
                    else:
                        entry["status"] = ResolutionStatus.NOT_FOUND
            elif info["status"] == ResolutionStatus.REMOTE:
                entry["canister_id"] = info["canister_id"]
                entry["entity_type"] = info["entity_type"]
                entry["entity_id"] = info["entity_id"]
            results.append(entry)
        return json.dumps({"results": results})
    except Exception as e:
        logger.error(f"Error in get_objects_by_ref: {e}\n{traceback.format_exc()}")
        return json.dumps({"results": [], "error": str(e)})


@query
def get_migration(subject: text) -> text:
    """Return this canister's forwarding stub for ``subject`` (for chain walks).

    JSON: ``{"found": bool, "next_ref": str, "prev_ref": str, "moved_at": str}``.
    """
    try:
        stub = _find_migration_stub(subject)
        if not stub:
            return json.dumps({"found": False})
        return json.dumps({
            "found": True,
            "subject": stub.subject,
            "entity_type": stub.entity_type,
            "prev_ref": stub.prev_ref or "",
            "next_ref": stub.next_ref or "",
            "moved_at": stub.moved_at or "",
        })
    except Exception as e:
        logger.error(f"Error in get_migration: {e}")
        return json.dumps({"found": False, "error": str(e)})


@update
@require(Operations.SELF_CHANGE_QUARTER)
def record_migration(args_json: text) -> text:
    """Record a forwarding stub: this subject left here for ``next_ref``.

    Args (JSON): ``{subject, next_ref, entity_type?, prev_ref?, signature?}``.
    ``next_ref`` must be a valid absolute ``realm://`` URI. Idempotent per
    subject — re-recording updates the existing stub.
    """
    try:
        from ggg import EntityMigration

        args = json.loads(args_json)
        subject = (args.get("subject") or "").strip()
        next_ref = (args.get("next_ref") or "").strip()
        if not subject:
            return json.dumps({"success": False, "error": "subject is required"})
        if not RealmRef.is_ref(next_ref):
            return json.dumps({
                "success": False,
                "error": f"next_ref must be a valid realm:// URI (got {next_ref!r})",
            })

        entity_type = (args.get("entity_type") or "User").strip()
        prev_ref = (args.get("prev_ref") or "").strip()
        signature = (args.get("signature") or "").strip()
        moved_at = str(ic.time())

        stub = _find_migration_stub(subject)
        if stub:
            stub.next_ref = next_ref
            stub.entity_type = entity_type
            if prev_ref:
                stub.prev_ref = prev_ref
            if signature:
                stub.signature = signature
            stub.moved_at = moved_at
        else:
            EntityMigration(
                subject=subject,
                entity_type=entity_type,
                prev_ref=prev_ref,
                next_ref=next_ref,
                moved_at=moved_at,
                signature=signature,
            )
        logger.info(f"Recorded migration for {subject} -> {next_ref}")
        return json.dumps({"success": True, "subject": subject, "next_ref": next_ref})
    except Exception as e:
        logger.error(f"Error in record_migration: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@query
def get_quarter_directory() -> text:
    """Coarse quarter directory for gossip — containers only, never contents.

    JSON: ``{"quarters": [{name, canister_id, population, status}, ...]}``.
    Includes this canister plus every Quarter entity it knows about.
    """
    try:
        from ggg import Quarter, Realm, User

        self_id = ic.id().to_str()
        realm = Realm.load("1")
        quarters = []
        seen = set()
        if realm is not None:
            try:
                self_pop = int(User.count())
            except Exception:
                self_pop = 0
            quarters.append({
                "name": getattr(realm, "name", "") or "",
                "canister_id": self_id,
                "population": self_pop,
                "status": "active",
                "index": 0,
                "is_self": True,
            })
            seen.add(self_id)
        for q in Quarter.instances():
            cid = q.canister_id or ""
            if cid in seen:
                continue
            seen.add(cid)
            quarters.append({
                "name": q.name or "",
                "canister_id": cid,
                "population": int(q.population or 0),
                "status": q.status or "active",
                "index": int(q.index or 0),
            })
        return json.dumps({"quarters": quarters})
    except Exception as e:
        logger.error(f"Error in get_quarter_directory: {e}\n{traceback.format_exc()}")
        return json.dumps({"quarters": [], "error": str(e)})


@query
def get_join_targets() -> text:
    """Public join policy for the registration page (issue #156).

    Tells the /join page where a *new* member may register. Returns:
    ``{mode, default_quarter, capital_id, quarters: [{canister_id, name,
    population, status, index, is_capital, joinable}, ...]}``.

    Policy:
    - ``mode`` is the capital's ``quarter_join_mode`` ("auto" | "choice") and
      only governs open/codeless joins (invite links always target the encoded
      quarter regardless of mode).
    - Once >=1 active sub-quarter exists the capital becomes coordinator-only:
      it is listed with ``joinable=false`` and ``default_quarter`` points at the
      newest active sub-quarter (highest index). With no sub-quarters the capital
      itself is the joinable default.

    Public (no auth): the caller is typically anonymous at this point.
    """
    try:
        from ggg import Quarter, Realm

        self_id = ic.id().to_str()
        realm = Realm.load("1")
        mode = (getattr(realm, "quarter_join_mode", "auto") or "auto") if realm else "auto"
        capital_name = (getattr(realm, "name", "") or "") if realm else ""

        sub_quarters = []
        if realm is not None:
            for q in Quarter.instances():
                cid = q.canister_id or ""
                if not cid or cid == self_id:
                    continue
                status = q.status or "active"
                sub_quarters.append({
                    "canister_id": cid,
                    "name": q.name or "",
                    "population": int(q.population or 0),
                    "status": status,
                    "index": int(getattr(q, "index", 0) or 0),
                    "is_capital": False,
                    "joinable": status == "active",
                })

        active_subs = [q for q in sub_quarters if q["joinable"]]
        capital_joinable = len(active_subs) == 0

        quarters = [{
            "canister_id": self_id,
            "name": capital_name or "Capital",
            "population": 0,
            "status": "active",
            "index": 0,
            "is_capital": True,
            "joinable": capital_joinable,
        }] + sub_quarters

        if active_subs:
            newest = max(active_subs, key=lambda q: q["index"])
            default_quarter = newest["canister_id"]
        else:
            default_quarter = self_id

        return json.dumps({
            "mode": mode,
            "default_quarter": default_quarter,
            "capital_id": self_id,
            "quarters": quarters,
        })
    except Exception as e:
        logger.error(f"Error in get_join_targets: {e}\n{traceback.format_exc()}")
        return json.dumps({
            "mode": "auto",
            "default_quarter": "",
            "capital_id": "",
            "quarters": [],
            "error": str(e),
        })


@update
@require(Operations.QUARTER_REGISTER)
def sync_quarters(peer_canister_id: text) -> Async[text]:
    """Gossip: pull a peer quarter's coarse directory and merge it into ours.

    Adds Quarter entities for peers we did not know about and updates known
    populations. Carries only container-level data (see issue #156).

    Delegates to ``core.quarter_bootstrap.sync_one_peer`` — the same un-gated
    merge the recurring population-sync task uses, so both paths stay identical.
    """
    from core.quarter_bootstrap import sync_one_peer

    res = yield from sync_one_peer(peer_canister_id)
    return json.dumps(res)


@query
def get_scale_status() -> text:
    """Report the federation's auto-scaling state (issue #156).

    JSON: ``{auto_scale_enabled, scale_in_flight, scale_requested_at, network,
    n, threshold, populations, should_scale}``. Used by admins/tests/frontend
    to observe sharding decisions; carries no per-user data.
    """
    try:
        from ggg import Realm

        from core.autoscale import (
            default_threshold_n,
            quarter_populations,
            resolve_should_scale,
            scale_at,
            _codex_should_deploy_fn,
        )

        realm = Realm.load("1")
        if not realm:
            return json.dumps({"success": False, "error": "Realm not found"})

        network = getattr(realm, "network", "") or ""
        pops = quarter_populations(realm)
        n = default_threshold_n(network)
        codex_fn = _codex_should_deploy_fn(realm)
        return json.dumps({
            "success": True,
            "auto_scale_enabled": bool(getattr(realm, "auto_scale_enabled", True)),
            "scale_in_flight": bool(getattr(realm, "scale_in_flight", False)),
            "scale_requested_at": getattr(realm, "scale_requested_at", "") or "",
            "network": network,
            "n": n,
            "threshold": scale_at(n),
            "populations": pops,
            "should_scale": resolve_should_scale(pops, network, codex_fn=codex_fn, realm=realm),
        })
    except Exception as e:
        logger.error(f"Error in get_scale_status: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def _quarter_casals_args(realm):
    """Build the provisioning spec for a new quarter from realm config.

    Reads the optional ``casals`` block persisted in ``manifest_data``::

        {
          "stand": "agora",                        # required
          "backend_wasm_key": "realm-backend@...", # required
          "casals_canister_id": "jj2e5-...",       # enables the direct path
          "registry_canister_id": "iebdk-...",     # for codex/extension pull
          "codex": {"codex_id": "...", "version": null},
          "extensions": [{"ext_id": "...", "version": null}, ...],
          "frontend_canister_id": ""               # quarters are backend-only
        }

    Returns None when the required ``stand``/``backend_wasm_key`` are missing.
    """
    # Name the new quarter after its prospective catalog index.
    next_index = 1
    try:
        from ggg import Quarter

        for q in Quarter.instances():
            next_index = max(next_index, int(q.index or 0) + 1)
    except Exception:
        pass
    return _parse_casals_spec(getattr(realm, "manifest_data", "") or "{}", next_index)


def _capital_runtime_config(realm) -> dict:
    """Snapshot the capital's runtime config + branding for a new quarter to
    mirror (issue #156), consumed by ``bootstrap_as_quarter`` via
    ``core.quarter_bootstrap.apply_quarter_config``.

    Copies identity (name/manifesto/welcome/branding), registration policy,
    accounting currency, shared infra canister ids, and the test-mode flags
    *verbatim* — so the quarter matches the capital's environment (a production
    capital has the flags off, so the quarter inherits them off). ``demo_data``
    is intentionally not propagated. ``frontend_canister_id`` is omitted: quarters
    are backend-only and keep their own empty value.
    """
    def g(attr, default=""):
        return getattr(realm, attr, default)

    return {
        "name": g("name"),
        "manifesto": g("manifesto"),
        "welcome_message": g("welcome_message"),
        "logo_url": g("logo_url"),
        "background_image_url": g("background_image_url"),
        "network": g("network"),
        "accounting_currency": g("accounting_currency"),
        "accounting_currency_decimals": int(g("accounting_currency_decimals", 0) or 0),
        "open_registration": bool(g("open_registration", False)),
        "ai_assistant_enabled": bool(g("ai_assistant_enabled", True)),
        "file_registry_canister_id": g("file_registry_canister_id"),
        "marketplace_canister_id": g("marketplace_canister_id"),
        "token_canister_id": g("token_canister_id"),
        "nft_canister_id": g("nft_canister_id"),
        "test_flags": {
            "test_mode": bool(g("test_mode", False)),
            "test_mode_ii_bypass": bool(g("test_mode_ii_bypass", False)),
            "test_mode_user_self_registration": bool(g("test_mode_user_self_registration", False)),
            "test_mode_skip_terms": bool(g("test_mode_skip_terms", False)),
            "test_mode_skip_passport_zkproof": bool(g("test_mode_skip_passport_zkproof", False)),
            "test_mode_skip_authentication": bool(g("test_mode_skip_authentication", False)),
        },
    }


@update
@require(Operations.QUARTER_CONFIGURE)
def set_quarter_provisioning_config(args: text) -> text:
    """Set/merge the ``casals`` provisioning block in this realm's ``manifest_data``.

    The whole auto-scale loop is gated on ``manifest_data.casals`` (consumed by
    ``parse_casals_spec``); this endpoint lets an admin wire it post-deploy
    without re-importing realm data. Provided keys are merged over any existing
    ``casals`` block (pass ``{"casals": {...}}`` or the flat fields directly), so
    a partial update (e.g. just ``casals_canister_id``) leaves the rest intact.

    Recognized keys: ``stand``, ``backend_wasm_key``, ``casals_canister_id``,
    ``registry_canister_id``, ``codex`` ({codex_id, version, run_init}),
    ``extensions`` ([{ext_id, version} | "ext_id", ...]), ``frontend_canister_id``.

    Returns ``{"success": bool, "casals": {...}, "error"?: str}``.
    """
    try:
        params = json.loads(args or "{}")
        if not isinstance(params, dict):
            return json.dumps({"success": False, "error": "args must be a JSON object"})
        incoming = params.get("casals") if isinstance(params.get("casals"), dict) else params

        from ggg import Realm

        realm = Realm.load("1")
        if not realm:
            return json.dumps({"success": False, "error": "Realm not found"})

        try:
            manifest = json.loads(getattr(realm, "manifest_data", "") or "{}")
            if not isinstance(manifest, dict):
                manifest = {}
        except Exception:
            manifest = {}

        casals = manifest.get("casals") if isinstance(manifest.get("casals"), dict) else {}
        allowed = (
            "stand", "backend_wasm_key", "casals_canister_id", "registry_canister_id",
            "codex", "extensions", "frontend_canister_id", "baton_canister_id",
        )
        for k in allowed:
            if k in incoming:
                casals[k] = incoming[k]
        manifest["casals"] = casals
        realm.manifest_data = json.dumps(manifest)
        logger.info(f"set_quarter_provisioning_config merged casals keys: {sorted(k for k in allowed if k in incoming)}")
        return json.dumps({"success": True, "casals": casals})
    except Exception as e:
        logger.error(f"set_quarter_provisioning_config error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def _orchestration_baton_id(realm) -> str:
    """This realm's Baton canister id from ``manifest_data.casals.baton_canister_id``."""
    try:
        manifest = json.loads(getattr(realm, "manifest_data", "") or "{}")
        cas = (manifest.get("casals") if isinstance(manifest, dict) else None) or {}
        return (cas.get("baton_canister_id") or "").strip()
    except Exception:
        return ""


def _parse_baton_text_reply(decoded) -> dict:
    """Parse a Baton text-method reply: plain JSON or candid-wrapped ("<json>")."""
    if isinstance(decoded, dict):
        return decoded
    if isinstance(decoded, (list, tuple)) and decoded:
        decoded = decoded[0]
    s = str(decoded or "").strip()
    if s.startswith("(") and ")" in s:
        inner = s[1:s.rfind(")")].strip().rstrip(",").strip()
        if inner.startswith('"') and inner.endswith('"'):
            try:
                inner_text = json.loads(inner)
                if isinstance(inner_text, str):
                    s = inner_text
            except json.JSONDecodeError:
                pass
    try:
        parsed = json.loads(s)
        return parsed if isinstance(parsed, dict) else {"result": parsed}
    except json.JSONDecodeError:
        return {"raw": s[:500]}


@update
@require(Operations.ORCHESTRATION_APPROVE)
def approve_orchestration_action(args: text) -> Async[text]:
    """Submit this realm's approval (or rejection) of a Baton orchestration
    action — the realm-backend half of the 2-of-2 (casals-backend +
    realm-backend) approval policy on this realm's Baton.

    Who may call this is realm governance: the codex grants the
    ``orchestration.approve`` operation to the right profiles (admins for
    dominion, organization representatives for agora, all members for
    syntropia); a voting extension resolving a proposal can also drive it.

    Args (JSON): {"action_id": "<baton action id>",
                  "decision"?: "approve" | "reject",
                  "baton_canister_id"?: "<override>"}

    The Baton id defaults to ``manifest_data.casals.baton_canister_id``
    (injected by the realm_installer at provisioning time).
    Returns the Baton's JSON reply (approval progress / quorum state).
    """
    try:
        params = json.loads(args or "{}")
        action_id = (params.get("action_id") or "").strip()
        if not action_id:
            return json.dumps({"success": False, "error": "action_id required"})
        decision = (params.get("decision") or "approve").strip().lower()
        if decision not in ("approve", "reject"):
            return json.dumps({"success": False, "error": "decision must be 'approve' or 'reject'"})

        from ggg import Realm
        realm = Realm.load("1")
        baton_id = (params.get("baton_canister_id") or "").strip() or (
            _orchestration_baton_id(realm) if realm else ""
        )
        if not baton_id:
            return json.dumps({
                "success": False,
                "error": "no baton configured (manifest_data.casals.baton_canister_id)",
            })

        method = "submit_approval" if decision == "approve" else "reject_action"
        escaped = action_id.replace("\\", "\\\\").replace('"', '\\"')
        call_res: CallResult = yield ic.call_raw(
            Principal.from_str(baton_id), method,
            ic.candid_encode(f'("{escaped}")'), 0,
        )
        if isinstance(call_res, dict):
            if call_res.get("Err") is not None:
                return json.dumps({"success": False, "error": str(call_res["Err"])})
            raw = call_res.get("Ok")
        elif hasattr(call_res, "Err") and call_res.Err is not None:
            return json.dumps({"success": False, "error": str(call_res.Err)})
        else:
            raw = getattr(call_res, "Ok", call_res)
        decoded = ic.candid_decode(raw) if isinstance(raw, (bytes, bytearray)) else raw
        reply = _parse_baton_text_reply(decoded)
        ok = bool(reply.get("ok")) if isinstance(reply, dict) else True
        logger.info(
            f"orchestration {decision} for action {action_id} on baton {baton_id}: "
            f"{str(reply)[:200]}"
        )
        return json.dumps({"success": ok, "decision": decision, "baton": baton_id, "reply": reply})
    except Exception as e:
        logger.error(f"approve_orchestration_action error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.QUARTER_REGISTER)
def process_quarter_scaling() -> Async[text]:
    """Act on a pending auto-scale request: provision a new quarter, bring it to
    parity, register it locally, then clear the in-flight guard.

    Two transports, preferred in order:

    1. **Direct** — when ``manifest_data.casals.casals_canister_id`` is set, the
       capital (commander of its Casals stand) asks Casals to ``create_canister``
       a backend-only quarter, then drives ``bootstrap_as_quarter`` on it (Casals
       co-adds the capital as a controller of canisters minted in its stand, so
       the gated bootstrap calls are authorized).
    2. **Broker** — otherwise, if ``installer_canister_id`` is set, ask the
       installer to provision via Casals on the capital's behalf.

    Non-blocking by design — user registration only sets ``scale_in_flight``;
    this endpoint (called by a controller, timer, or task manager) performs the
    actual provisioning out of band so joins never wait on a deploy.
    Idempotent: a no-op when no scale is in flight.
    """
    res = yield from _run_quarter_scaling()
    return res


def _run_quarter_scaling() -> Async[text]:
    """Core auto-scale provisioning driver (un-gated).

    Creates a quarter via Casals (direct) or the installer (broker), seeds the
    new quarter's local self-bootstrap, registers it locally, then clears the
    in-flight guard. Shared by the ``process_quarter_scaling`` endpoint and the
    recurring autoscale task (``run_autoscale_tick``).
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
        if not realm:
            return json.dumps({"success": False, "error": "Realm not found"})
        if not bool(getattr(realm, "scale_in_flight", False)):
            return json.dumps({"success": True, "status": "idle", "message": "no scale in flight"})

        spec = _quarter_casals_args(realm)
        if not spec:
            return json.dumps({
                "success": False,
                "status": "blocked",
                "error": "manifest_data.casals {stand, backend_wasm_key} required to provision",
            })

        casals_id = (spec.get("casals_canister_id") or "").strip()
        installer_id = (getattr(realm, "installer_canister_id", "") or "").strip()
        bootstrap_result = None

        # Auto-derive the install set from the capital's *own live state* so the
        # new quarter mirrors whatever the capital currently has installed — no
        # admin-curated codex/extension list to maintain (issue #156). The
        # configured casals-block lists are only a fallback for a capital that
        # has nothing runtime-installed (e.g. fully baked-in extensions).
        from core.quarter_bootstrap import derive_capital_install_set

        derived = derive_capital_install_set(spec.get("registry_canister_id", ""))
        registry_id = (derived.get("registry_canister_id") or spec.get("registry_canister_id", "")).strip()
        codices = derived.get("codices") or (
            [spec["codex"]] if spec.get("codex") else []
        )
        extensions = derived.get("extensions") or spec.get("extensions", [])
        # Snapshot the capital's runtime config + branding so the quarter comes
        # up branded and registration-ready (issue #156), not as a bare
        # "Default Realm" that rejects new users.
        capital_config = _capital_runtime_config(realm)
        logger.info(
            f"Auto-scale install set (mirroring capital): "
            f"{len(codices)} codices, {len(extensions)} extensions, registry={registry_id or 'none'}; "
            f"config name={capital_config.get('name')!r} open_reg={capital_config.get('open_registration')}"
        )

        if casals_id:
            # ── Direct path: the capital commands its own Casals stand. ──
            create_res = yield from _request_casals_create_canister(casals_id, {
                "stand": spec["stand"],
                "name": spec["name"],
                "kind": "backend",
                "wasm_key": spec["backend_wasm_key"],
            })
            if not create_res.get("ok"):
                realm.scale_in_flight = False
                return json.dumps({"success": False, "status": "failed",
                                   "error": f"Casals create_canister failed: {create_res.get('error')}"})
            new_canister_id = (create_res.get("canister_id") or "").strip()
            if not new_canister_id:
                realm.scale_in_flight = False
                return json.dumps({"success": False, "status": "failed",
                                   "error": "Casals create_canister returned no canister_id"})

            # Seed the new quarter's local self-bootstrap (config + codex +
            # extensions, installed one item per tick by its own TaskManager).
            bootstrap_result = yield from _bootstrap_quarter(new_canister_id, {
                "parent_realm_canister_id": ic.id().to_str(),
                "registry_canister_id": registry_id,
                "codices": codices,
                "extensions": extensions,
                "frontend_canister_id": spec.get("frontend_canister_id", ""),
                "config": capital_config,
            })
        elif installer_id:
            # ── Broker path: ask the installer to provision on our behalf. ──
            result = yield from _request_provision_quarter(installer_id, {
                "stand": spec["stand"],
                "backend_wasm_key": spec["backend_wasm_key"],
                "name": spec["name"],
            })
            if not result.get("ok"):
                realm.scale_in_flight = False
                return json.dumps({"success": False, "status": "failed",
                                   "error": result.get("error", "provision failed")})
            new_canister_id = (result.get("canister_id") or "").strip()
        else:
            # Intent recorded but no transport wired; keep the flag set so an
            # operator can finish wiring and retry.
            return json.dumps({
                "success": False,
                "status": "blocked",
                "error": "no provisioning transport: set manifest_data.casals.casals_canister_id "
                         "(direct) or installer_canister_id (broker)",
            })

        from ggg import Quarter

        # Register the freshly minted backend as a quarter (assign next index).
        already = any(q.canister_id == new_canister_id for q in Quarter.instances())
        new_index = 1
        if not already:
            for q in Quarter.instances():
                new_index = max(new_index, int(q.index or 0) + 1)
            q = Quarter(name=spec.get("name") or new_canister_id[:8], canister_id=new_canister_id, index=new_index)
            q.federation = realm

        # Start refreshing this quarter's population into the capital's view so
        # join-page counts don't go stale (issue #156). Best-effort.
        try:
            ensure_population_sync_task()
        except Exception as e:
            logger.error(f"ensure_population_sync_task (auto-scale) failed: {e}")

        # Provisioning complete; allow the next threshold crossing to re-trigger.
        realm.scale_in_flight = False
        logger.info(f"Auto-scale provisioned + registered quarter {new_canister_id} (index {new_index})")
        return json.dumps({
            "success": True,
            "status": "provisioned",
            "canister_id": new_canister_id,
            "index": new_index,
            "bootstrap": bootstrap_result,
        })
    except Exception as e:
        logger.error(f"Error in process_quarter_scaling: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def run_autoscale_tick() -> Async[text]:
    """Recurring autoscale driver step (issue #156).

    Provisions a quarter when a scale is in flight, otherwise disables the
    trigger schedule so the task stops firing until the next registration
    re-seeds it (see ``ensure_autoscale_task``). Also stops ticking on a
    ``blocked`` result (misconfiguration needing operator intervention) so a
    mis-wired realm never busy-loops. Invoked by the ``AUTOSCALE_TASK_NAME``
    TaskManager task via a tiny codex shim (``from main import run_autoscale_tick``).
    """
    try:
        from ggg import Realm
        from core.quarter_bootstrap import AUTOSCALE_TASK_NAME, disable_recurring_task

        realm = Realm.load("1")
        if not realm or not bool(getattr(realm, "scale_in_flight", False)):
            disable_recurring_task(AUTOSCALE_TASK_NAME)
            return json.dumps({"success": True, "status": "idle"})

        res = yield from _run_quarter_scaling()

        # Stop ticking once the flag is cleared (done/failed) or we're blocked.
        stop = False
        try:
            parsed = json.loads(res) if isinstance(res, str) else res
            if isinstance(parsed, dict) and parsed.get("status") == "blocked":
                stop = True
        except Exception:
            pass
        realm = Realm.load("1")
        if realm and not bool(getattr(realm, "scale_in_flight", False)):
            stop = True
        if stop:
            disable_recurring_task(AUTOSCALE_TASK_NAME)
        return res
    except Exception as e:
        logger.error(f"run_autoscale_tick failed: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def ensure_autoscale_task() -> bool:
    """Seed (or re-enable) the recurring TaskManager task that drives auto-scale
    provisioning while ``scale_in_flight`` is set. Idempotent; safe to call from
    the registration path each time a scale is newly requested."""
    try:
        from core.quarter_bootstrap import (
            AUTOSCALE_INTERVAL_S,
            AUTOSCALE_STEP_CODE,
            AUTOSCALE_TASK_NAME,
            seed_recurring_codex_task,
        )

        seed_recurring_codex_task(AUTOSCALE_TASK_NAME, AUTOSCALE_STEP_CODE, AUTOSCALE_INTERVAL_S)
        return True
    except Exception as e:
        logger.error(f"ensure_autoscale_task failed: {e}\n{traceback.format_exc()}")
        return False


def ensure_population_sync_task() -> bool:
    """Seed (or re-enable) the recurring population-sync task that keeps the
    capital's quarter populations fresh. Idempotent; safe to call every time a
    quarter is registered or auto-provisioned."""
    try:
        from core.quarter_bootstrap import (
            POP_SYNC_INTERVAL_S,
            POP_SYNC_STEP_CODE,
            POP_SYNC_TASK_NAME,
            seed_recurring_codex_task,
        )

        seed_recurring_codex_task(POP_SYNC_TASK_NAME, POP_SYNC_STEP_CODE, POP_SYNC_INTERVAL_S)
        return True
    except Exception as e:
        logger.error(f"ensure_population_sync_task failed: {e}\n{traceback.format_exc()}")
        return False


@query
def get_zones(resolution: nat = 6) -> text:
    """
    Get H3 zone aggregation data for users in this realm.
    Returns zones with user counts at each H3 cell.

    Args:
        resolution: H3 resolution level (0-15). Default 6.

    Returns:
        JSON string with zone data
    """
    try:
        result = get_zone_aggregation(resolution)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error getting zones: {e}")
        return json.dumps({"success": False, "error": str(e)})


@query
def get_my_user_status() -> RealmResponse:
    try:
        user = user_get(ic.caller().to_str())
        logger.info(f"User: {user}")
        if not user["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=user["error"])
            )

        profiles = Vec[text]()
        if "profiles" in user and user["profiles"]:
            for p in user["profiles"]:
                profiles.append(p)
        logger.info(f"Profiles: {profiles}")
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                userGet=UserGetRecord(
                    principal=Principal.from_str(user["principal"]),
                    profiles=profiles,
                    nickname=user.get("nickname", ""),
                    avatar=user.get("avatar", ""),
                    private_data=user.get("private_data", ""),
                    assigned_quarter=user.get("home_quarter", ""),
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


def _seeded_extension_names() -> set:
    """Return names of extensions that have explicit DB access grants.

    An extension is considered "seeded" when it has at least one user,
    department, or profile link in the database. Only seeded extensions are
    subject to strict whitelist filtering; un-seeded extensions fall back to
    manifest-level profile matching. This prevents a *partial* seed (e.g.
    installing a single extension, which links only that one to its profiles)
    from hiding every other extension that has not yet been seeded.
    """
    from ggg import Extension

    seeded = set()
    try:
        for ext in Extension.instances():
            try:
                if list(ext.users) or list(ext.departments) or list(ext.profiles):
                    seeded.add(ext.name)
            except Exception:
                continue
    except Exception:
        pass
    return seeded


def _user_granted_extension_names(user) -> set:
    """Union of extension names directly granted to a user via user, department,
    or profile links."""
    granted = set()
    if not user:
        return granted
    for ext in user.extensions:
        granted.add(ext.name)
    for dept in user.departments:
        for ext in dept.extensions:
            granted.add(ext.name)
    for profile in user.profiles:
        for ext in profile.extensions:
            granted.add(ext.name)
    return granted


@query
def get_my_extensions() -> text:
    """Return the list of extensions accessible to the calling user.

    For each installed extension:
      - If it has been seeded with DB access grants, it is visible only when
        the user holds a matching user/department/profile grant.
      - Otherwise (no DB grants for that extension), visibility falls back to
        manifest-level profile matching.

    This per-extension fallback ensures a partial seed never hides extensions
    that simply have not been linked in the database yet.

    Returns JSON: {"success": true, "extensions": ["voting", "vault", ...]}
    """
    try:
        from ggg import User
        from core.runtime_extensions import get_all_extension_manifests

        caller = ic.caller().to_str()
        user = User[caller]
        if not user:
            return json.dumps({"success": False, "error": "User not found"})

        user_granted = _user_granted_extension_names(user)
        seeded = _seeded_extension_names()
        user_profiles = [p.name for p in user.profiles] if user.profiles else []

        visible = set()
        for ext_id, m in get_all_extension_manifests().items():
            if not isinstance(m, dict):
                continue
            if ext_id in seeded:
                if ext_id in user_granted:
                    visible.add(ext_id)
            else:
                ext_profiles = m.get("profiles") or []
                if not ext_profiles or any(p in user_profiles for p in ext_profiles):
                    visible.add(ext_id)

        return json.dumps({"success": True, "extensions": sorted(visible)})
    except Exception as e:
        logger.error(f"Error getting user extensions: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.SELF_UPDATE_PUBLIC_PROFILE)
def update_my_public_profile(nickname: str, avatar: str) -> RealmResponse:
    try:
        result = user_update_public_profile(ic.caller().to_str(), nickname, avatar)
        if not result["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=result["error"])
            )

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                userGet=UserGetRecord(
                    principal=ic.caller(),
                    profiles=Vec[text](),
                    nickname=result["nickname"],
                    avatar=result["avatar"],
                    private_data="",
                    assigned_quarter="",
                )
            ),
        )
    except Exception as e:
        logger.error(
            f"Error updating public profile: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def update_my_private_data(private_data: str) -> RealmResponse:
    try:
        result = user_update_private_data(ic.caller().to_str(), private_data)
        if not result["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=result["error"])
            )

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                userGet=UserGetRecord(
                    principal=ic.caller(),
                    profiles=Vec[text](),
                    nickname="",
                    avatar="",
                    private_data=result["private_data"],
                    assigned_quarter="",
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error updating private data: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def get_my_vetkey_public_key() -> RealmResponse:
    """Get the vetKD public key for the caller's encryption context.

    The returned hex-encoded BLS12-381 G2 public key is used by the frontend
    to verify encrypted keys and set up the IBE scheme.
    """
    try:
        result = yield get_vetkey_public_key(ic.caller().to_str())
        if not result["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=result["error"])
            )
        return RealmResponse(
            success=True,
            data=RealmResponseData(message=result["public_key_hex"]),
        )
    except Exception as e:
        logger.error(
            f"Error getting vetkey public key: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def derive_my_vetkey(transport_public_key_hex: text) -> RealmResponse:
    """Derive an encrypted vetKey for the caller.

    The caller must supply a 48-byte BLS12-381 G1 transport public key
    (hex-encoded, 96 chars).  The management canister encrypts the derived
    symmetric key under this transport key so it can only be decrypted by
    the caller's frontend.
    """
    try:
        result = yield derive_vetkey(ic.caller().to_str(), transport_public_key_hex)
        if not result["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=result["error"])
            )
        return RealmResponse(
            success=True,
            data=RealmResponseData(message=result["encrypted_key_hex"]),
        )
    except Exception as e:
        logger.error(f"Error deriving vetkey: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def get_sharing_root_public_key() -> RealmResponse:
    """Get the shared *root* vetKD public key used for member data sharing.

    Unlike :func:`get_my_vetkey_public_key` (one key per principal), this is a
    single key shared by everyone. The frontend fetches it **once** and derives
    each recipient's IBE public key locally by using the recipient's principal
    as the IBE identity — eliminating the previous one-management-call-per-
    recipient cost. Only the holder of a recipient's sharing vetKey (derivable
    solely by that principal via :func:`derive_my_sharing_vetkey`) can decrypt.
    """
    try:
        result = yield get_root_public_key()
        if not result["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=result["error"])
            )
        return RealmResponse(
            success=True,
            data=RealmResponseData(message=result["public_key_hex"]),
        )
    except Exception as e:
        logger.error(
            f"Error getting sharing root public key: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def derive_my_sharing_vetkey(transport_public_key_hex: text) -> RealmResponse:
    """Derive the caller's sharing vetKey (root context, input = own principal).

    Because the vetKD ``input`` is bound to ``ic.caller()``, a caller can only
    ever obtain the key for their own identity, and therefore can only decrypt
    IBE ciphertexts addressed to their principal under the shared root key.
    """
    try:
        result = yield derive_vetkey_for_sharing(
            ic.caller().to_str(), transport_public_key_hex
        )
        if not result["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=result["error"])
            )
        return RealmResponse(
            success=True,
            data=RealmResponseData(message=result["encrypted_key_hex"]),
        )
    except Exception as e:
        logger.error(
            f"Error deriving sharing vetkey: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


# ---------------------------------------------------------------------------
# Crypto envelope & group endpoints
# ---------------------------------------------------------------------------


def _caller_can_manage_scope(scope: str) -> bool:
    """Whether the caller may grant/revoke read access for *scope*.

    Authorization is pluggable per scope *kind* (``user:``, ``dept:``,
    ``realm:``, …) and defined in :mod:`core.crypto_scopes`. This keeps the
    crypto engine generic and reusable for any payload, not just member
    personal data.
    """
    from core.crypto_scopes import caller_can_manage_scope, production_context

    return caller_can_manage_scope(scope, ic.caller().to_str(), production_context())


@update
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def crypto_store_my_envelope(scope: text, wrapped_dek: text) -> CryptoResponse:
    """Store (or update) a wrapped DEK envelope for the caller."""
    try:
        result = crypto_store_envelope(ic.caller().to_str(), scope, wrapped_dek)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                envelope=EnvelopeRecord(
                    scope=result["scope"],
                    principal_id=result["principal"],
                    wrapped_dek=result["wrapped_dek"],
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error storing envelope: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@query
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def crypto_get_my_envelope(scope: text) -> CryptoResponse:
    """Get the caller's envelope for a scope."""
    try:
        result = crypto_get_envelope(ic.caller().to_str(), scope)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                envelope=EnvelopeRecord(
                    scope=result["scope"],
                    principal_id=result["principal"],
                    wrapped_dek=result["wrapped_dek"],
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error getting envelope: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@query
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def crypto_get_my_scopes() -> CryptoResponse:
    """List all scopes the caller has access to."""
    try:
        result = crypto_list_scopes(ic.caller().to_str())
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(scopeList=ScopeListRecord(scopes=result["scopes"])),
        )
    except Exception as e:
        logger.error(f"Error listing scopes: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


# NOTE: These endpoints are generic over the scope *kind* — `user:`, `dept:`,
# `realm:`, or any kind registered in core.crypto_scopes. Authorization to
# manage a scope is enforced by `_caller_can_manage_scope`, so the same crypto
# sharing machinery is reusable for personal data, department documents,
# realm-level records, etc.


@update
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def crypto_grant_to_scope_batch(
    scope: text, wrapped_deks_json: text
) -> CryptoResponse:
    """Grant many principals access to a scope the caller may manage, in one call.

    ``wrapped_deks_json`` is a JSON object mapping ``principal -> wrapped_dek``
    (the DEK IBE-wrapped client-side for each recipient). Replacing N update
    calls with one both saves round-trips and lets the backend upsert all
    envelopes in a single linear pass.
    """
    try:
        if not _caller_can_manage_scope(scope):
            return CryptoResponse(
                success=False,
                data=CryptoResponseData(
                    error="You are not allowed to manage sharing for this scope"
                ),
            )
        try:
            wrapped_deks = json.loads(wrapped_deks_json)
        except Exception:
            return CryptoResponse(
                success=False,
                data=CryptoResponseData(error="Invalid wrapped_deks JSON"),
            )
        if not isinstance(wrapped_deks, dict):
            return CryptoResponse(
                success=False,
                data=CryptoResponseData(error="wrapped_deks must be a JSON object"),
            )
        result = crypto_grant_many(scope, wrapped_deks)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                message=f"Granted {result['envelopes_granted']} envelope(s) for {scope}"
            ),
        )
    except Exception as e:
        logger.error(f"Error batch granting to scope: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def crypto_revoke_from_scope_batch(
    scope: text, principals_json: text
) -> CryptoResponse:
    """Revoke many principals from a scope the caller may manage, in one call.

    ``principals_json`` is a JSON array of principal strings to revoke.
    """
    try:
        if not _caller_can_manage_scope(scope):
            return CryptoResponse(
                success=False,
                data=CryptoResponseData(
                    error="You are not allowed to manage sharing for this scope"
                ),
            )
        try:
            principals = json.loads(principals_json)
        except Exception:
            return CryptoResponse(
                success=False,
                data=CryptoResponseData(error="Invalid principals JSON"),
            )
        if not isinstance(principals, list):
            return CryptoResponse(
                success=False,
                data=CryptoResponseData(error="principals must be a JSON array"),
            )
        result = crypto_revoke_many(scope, principals)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                message=f"Revoked {result['envelopes_revoked']} envelope(s) from {scope}"
            ),
        )
    except Exception as e:
        logger.error(f"Error batch revoking from scope: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@query
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def crypto_list_scope_envelopes(scope: text) -> CryptoResponse:
    """List all principals with access to a scope the caller may manage."""
    try:
        if not _caller_can_manage_scope(scope):
            return CryptoResponse(
                success=False,
                data=CryptoResponseData(
                    error="You are not allowed to manage sharing for this scope"
                ),
            )
        result = crypto_list_envelopes(scope)
        envelopes = Vec["EnvelopeRecord"]()
        for e in result["envelopes"]:
            envelopes.append(
                EnvelopeRecord(
                    scope=e["scope"],
                    principal_id=e["principal"],
                    wrapped_dek=e["wrapped_dek"],
                )
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                envelopeList=EnvelopeListRecord(envelopes=envelopes)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing scope envelopes: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@query
@require(Operations.SELF_UPDATE_PRIVATE_DATA)
def list_share_audiences() -> RealmResponse:
    """List the audiences a member can share their private data with.

    Returns, as a JSON string in ``message``, the set of audiences plus the
    member principals each one resolves to. The member's browser needs these
    principals to wrap their data-encryption key for each recipient.

    Audiences:
      - ``Administrators`` — the member_data_readers crypto group.
      - one per ``Department`` — its current members.
    """
    try:
        audiences = []

        try:
            from api.crypto import group_members as _group_members

            res = _group_members("member_data_readers")
            principals = [m["principal"] for m in res.get("members", []) if m.get("principal")]
            audiences.append(
                {
                    "id": "group:member_data_readers",
                    "label": "Administrators",
                    "type": "admins",
                    "principals": principals,
                }
            )
        except Exception as e:
            logger.warning(f"list_share_audiences: admins group unavailable: {e}")

        try:
            from ggg import Department

            for dept in Department.instances():
                principals = []
                try:
                    for m in dept.members:
                        if getattr(m, "id", None):
                            principals.append(m.id)
                except Exception:
                    pass
                audiences.append(
                    {
                        "id": f"dept:{dept.name}",
                        "label": dept.name,
                        "type": "department",
                        "principals": principals,
                    }
                )
        except Exception as e:
            logger.warning(f"list_share_audiences: departments unavailable: {e}")

        return RealmResponse(
            success=True,
            data=RealmResponseData(message=json.dumps({"audiences": audiences})),
        )
    except Exception as e:
        logger.error(f"Error listing share audiences: {e}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def directory_list() -> RealmResponse:
    """Realm directory for entity pickers (e.g. choosing a litigation defendant).

    Returns, as JSON in ``message``, a flat list of ``entries`` — realm users
    (principal + best display name) and departments (name + head principal) —
    so any extension can offer name/principal autocomplete via one fast query
    instead of an expensive per-extension update call. Read-only; exposes only
    identities already visible across the realm, never private content.

    The client is expected to fetch this once and filter in the browser. We log
    the instruction count so we can decide whether the simple full-scan needs a
    projection/index later (see ROADMAP perf notes).
    """
    _t0 = ic.performance_counter(0)
    try:
        from ggg import Department, User

        entries = []

        user_count = 0
        for u in User.instances():
            principal = getattr(u, "id", None)
            if not principal:
                continue
            user_count += 1
            human = getattr(u, "human", None)
            human_name = ""
            if human is not None:
                human_name = (
                    getattr(human, "name", None)
                    or getattr(human, "full_name", None)
                    or ""
                )
            entries.append(
                {
                    "kind": "user",
                    "principal": str(principal),
                    "label": human_name or (getattr(u, "nickname", "") or "") or str(principal),
                }
            )

        dept_count = 0
        for d in Department.instances():
            name = getattr(d, "name", "") or ""
            if not name:
                continue
            dept_count += 1
            head = getattr(d, "head", None)
            head_principal = str(getattr(head, "id", "")) if head is not None else ""
            entries.append(
                {
                    "kind": "department",
                    "principal": head_principal,
                    "label": name,
                    # Stable department identifier so callers can record the
                    # department itself as a target (e.g. litigation defendant),
                    # independent of whoever currently heads it.
                    "id": str(getattr(d, "_id", "") or ""),
                }
            )

        instructions = ic.performance_counter(0) - _t0
        logger.info(
            f"directory_list: {user_count} users + {dept_count} depts "
            f"({len(entries)} entries) in {instructions} instructions"
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(message=json.dumps({"entries": entries})),
        )
    except Exception as e:
        logger.error(f"Error in directory_list: {e}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
@require(Operations.REALM_ADMIN)
def crypto_get_envelopes(scope: text) -> CryptoResponse:
    """List all envelopes for a scope (admin only)."""
    try:
        result = crypto_list_envelopes(scope)
        envelopes = Vec["EnvelopeRecord"]()
        for e in result["envelopes"]:
            envelopes.append(
                EnvelopeRecord(
                    scope=e["scope"],
                    principal_id=e["principal"],
                    wrapped_dek=e["wrapped_dek"],
                )
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                envelopeList=EnvelopeListRecord(envelopes=envelopes)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing envelopes: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def crypto_share(
    scope: text, target_principal: text, wrapped_dek: text
) -> CryptoResponse:
    """Share access to a scope with another principal (admin only)."""
    try:
        result = crypto_share_principal(scope, target_principal, wrapped_dek)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                message=f"Shared scope {scope} with {target_principal}"
            ),
        )
    except Exception as e:
        logger.error(f"Error sharing: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def crypto_revoke(scope: text, target_principal: text) -> CryptoResponse:
    """Revoke a principal's access to a scope (admin only)."""
    try:
        result = crypto_revoke_principal(scope, target_principal)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                message=f"Revoked {target_principal} from scope {scope}"
            ),
        )
    except Exception as e:
        logger.error(f"Error revoking: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def crypto_create_group(name: text, description: text) -> CryptoResponse:
    """Create a new crypto group (admin only)."""
    try:
        result = crypto_group_create(name, description)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                group=GroupRecord(
                    name=result["name"], description=result["description"]
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error creating group: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def crypto_delete_group(name: text) -> CryptoResponse:
    """Delete a crypto group (admin only)."""
    try:
        result = crypto_group_delete(name)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(message=f"Deleted group {name}"),
        )
    except Exception as e:
        logger.error(f"Error deleting group: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def crypto_add_group_member(
    group_name: text, principal: text, role: text
) -> CryptoResponse:
    """Add a principal to a crypto group (admin only)."""
    try:
        result = crypto_group_add(group_name, principal, role or "member")
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(message=f"Added {principal} to group {group_name}"),
        )
    except Exception as e:
        logger.error(f"Error adding group member: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def crypto_remove_group_member(group_name: text, principal: text) -> CryptoResponse:
    """Remove a principal from a crypto group (admin only)."""
    try:
        result = crypto_group_remove(group_name, principal)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                message=f"Removed {principal} from group {group_name}"
            ),
        )
    except Exception as e:
        logger.error(f"Error removing group member: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@query
def crypto_list_groups() -> CryptoResponse:
    """List all crypto groups."""
    try:
        result = crypto_group_list()
        groups = Vec["GroupRecord"]()
        for g in result["groups"]:
            groups.append(GroupRecord(name=g["name"], description=g["description"]))
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(groupList=GroupListRecord(groups=groups)),
        )
    except Exception as e:
        logger.error(f"Error listing groups: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@query
def crypto_get_group_members(group_name: text) -> CryptoResponse:
    """List members of a crypto group."""
    try:
        result = crypto_group_members(group_name)
        members = Vec["GroupMemberRecord"]()
        for m in result["members"]:
            members.append(
                GroupMemberRecord(principal_id=m["principal"], role=m["role"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(groupMembers=GroupMembersRecord(members=members)),
        )
    except Exception as e:
        logger.error(f"Error listing group members: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def crypto_share_with_group(scope: text, group_name: text) -> CryptoResponse:
    """Share access to a scope with all members of a group (admin only)."""
    try:
        result = crypto_share_group(scope, group_name)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                message=f"Shared scope {scope} with group {group_name} ({result['envelopes_created']} envelopes)"
            ),
        )
    except Exception as e:
        logger.error(f"Error sharing with group: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


@update
@require(Operations.REALM_ADMIN)
def crypto_revoke_from_group(scope: text, group_name: text) -> CryptoResponse:
    """Revoke all group members' access to a scope (admin only)."""
    try:
        result = crypto_revoke_group(scope, group_name)
        if not result["success"]:
            return CryptoResponse(
                success=False, data=CryptoResponseData(error=result["error"])
            )
        return CryptoResponse(
            success=True,
            data=CryptoResponseData(
                message=f"Revoked group {group_name} from scope {scope} ({result['envelopes_deleted']} envelopes)"
            ),
        )
    except Exception as e:
        logger.error(f"Error revoking group: {e}\n{traceback.format_exc()}")
        return CryptoResponse(success=False, data=CryptoResponseData(error=str(e)))


# New GGG API endpoints


@query
def get_objects_paginated(
    class_name: str, page_num: nat, page_size: nat, order: str = "asc"
) -> RealmResponse:
    """
    Get paginated list of objects with optional ordering.

    Args:
        class_name: Name of the entity class (e.g., "User", "Transfer", "Mandate")
        page_num: Page number (0-indexed)
        page_size: Number of items per page
        order: Sort order - "asc" for ascending (oldest first) or "desc" for descending (newest first)

    Example (ascending):
    $ dfx canister call --output json canister_id get_objects_paginated '("User", 0, 3, "asc")'

    Example (descending):
    $ dfx canister call --output json canister_id get_objects_paginated '("User", 0, 3, "desc")'

    Response:
    {
      "data": {
        "objectsListPaginated": {
          "objects": [
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"User\", \"_id\": \"1\", \"id\": \"system\", \"profile_picture_url\": \"\"}",
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"User\", \"_id\": \"2\", \"id\": \"fiona_rodriguez_000\", \"profile_picture_url\": \"https://api.dicebear.com/7.x/personas/svg?seed=FionaRodriguez\"}",
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"User\", \"_id\": \"3\", \"id\": \"george_brown_001\", \"profile_picture_url\": \"https://api.dicebear.com/7.x/personas/svg?seed=GeorgeBrown\"}"
          ],
          "pagination": {
            "page_num": "0",
            "page_size": "3",
            "total_items_count": "51",
            "total_pages": "17"
          }
        }
      },
      "success": true
    }
    """

    try:
        logger.info(
            f"Listing {class_name} objects for page {page_num} with page size {page_size}, order: {order}"
        )
        result = list_objects_paginated(
            class_name, page_num=page_num, page_size=page_size, order=order
        )
        objects = result["items"]
        objects_json = [json.dumps(obj.serialize()) for obj in objects]
        logger.info(f"Objects JSON: {objects_json}")
        pagination = PaginationInfo(
            page_num=result["page_num"],
            page_size=result["page_size"],
            total_items_count=result["total_items_count"],
            total_pages=result["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                objectsListPaginated=ObjectsListRecordPaginated(
                    objects=objects_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def get_objects(params: Vec[Tuple[str, str]]) -> RealmResponse:
    """Example:

    $ dfx canister call --output json ulvla-h7777-77774-qaacq-cai get_objects '(
      vec { record { 0 = "User"; 1 = "1" };  record { 0 = "Realm"; 1 = "1" }; }
    )'
    {
      "data": {
        "objectsList": {
          "objects": [
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"User\", \"_id\": \"1\", \"id\": \"system\", \"profile_picture_url\": \"\"}",
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"Realm\", \"_id\": \"1\", \"name\": \"Generated Demo Realm\", \"manifesto\": \"Generated demo realm with 51 citizens and 5 organizations\", \"id\": \"0\", \"created_at\": \"2025-09-10T13:23:57.099332\", \"status\": \"active\", \"governance_type\": \"democratic\", \"population\": 51, \"organization_count\": 5, \"settings\": {\"voting_period_days\": 7, \"proposal_threshold\": 0.1, \"quorum_percentage\": 0.3, \"tax_rate\": 0.15, \"ubi_amount\": 1000}, \"relations\": {\"treasury\": [{\"_type\": \"Treasury\", \"_id\": \"2\"}]}}"
          ]
        }
      },
      "success": true
    }
    """

    try:
        logger.info("Listing objects")
        result = list_objects(params)
        objects = result
        objects_json = [json.dumps(obj.serialize()) for obj in objects]
        logger.info(f"Objects JSON: {objects_json}")
        return RealmResponse(
            success=True,
            data=RealmResponseData(objectsList=ObjectsListRecord(objects=objects_json)),
        )
    except Exception as e:
        logger.error(f"Error listing objects: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def find_objects(class_name: str, params: Vec[Tuple[str, str]]) -> RealmResponse:
    """
    Search for objects matching the given field criteria.

    Args:
        class_name: Name of the entity class (e.g., "User", "Transfer", "Mandate")
        params: List of (field_name, field_value) tuples to match

    Example:
    $ dfx canister call --output json canister_id find_objects '("User", vec { record { 0 = "id"; 1 = "system" }; })'

    Response:
    {
      "data": {
        "objectsList": {
          "objects": [
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", ...}"
          ]
        }
      },
      "success": true
    }
    """
    try:
        logger.info(f"Searching {class_name} objects with params: {params}")
        results = search_objects(class_name, list(params))
        objects_json = [json.dumps(obj.serialize()) for obj in results]
        logger.info(f"Found {len(objects_json)} matching objects")
        return RealmResponse(
            success=True,
            data=RealmResponseData(objectsList=ObjectsListRecord(objects=objects_json)),
        )
    except Exception as e:
        logger.error(f"Error searching objects: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def get_my_invoices() -> RealmResponse:
    """
    Get all invoices belonging to the calling user.

    Filters Invoice entities where invoice.user.id == ic.caller().
    Returns invoices sorted by most recent first.

    Example:
    $ dfx canister call --output json canister_id get_my_invoices '()'

    Response:
    {
      "data": {
        "objectsList": {
          "objects": [
            "{\"id\": \"inv_001\", \"amount\": 0.001, \"status\": \"Pending\", ...}"
          ]
        }
      },
      "success": true
    }
    """
    try:
        caller = ic.caller().to_str()
        logger.info(f"Getting invoices for caller: {caller}")
        from ggg import Invoice

        all_invoices = Invoice.instances()
        user_invoices = [
            inv for inv in all_invoices if inv.user and inv.user.id == caller
        ]
        objects_json = [json.dumps(inv.serialize()) for inv in user_invoices]
        logger.info(f"Found {len(objects_json)} invoices for {caller}")
        return RealmResponse(
            success=True,
            data=RealmResponseData(objectsList=ObjectsListRecord(objects=objects_json)),
        )
    except Exception as e:
        logger.error(f"Error getting invoices: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
@require(Operations.SELF_INVOICE_REFRESH)
def refresh_invoice(args: text) -> Async[text]:
    """
    Refresh payment status for an invoice.

    Delegates to the invoice's refresh() method, which uses either:
    • Subaccount mode  (SUBACCOUNT_PAYMENTS_ENABLED = True)  — checks the
      token balance on the invoice's dedicated 32-byte subaccount.
    • Nonce-suffix mode (SUBACCOUNT_PAYMENTS_ENABLED = False) — scans the
      token's ICRC-1 indexer for an incoming transfer whose amount matches
      the invoice's nonce-adjusted exact amount.

    Args (JSON): {"invoice_id": "inv_xxx"}
    Returns (JSON): {"success": true, "data": {...}} or {"success": false, "error": "..."}
    """
    try:
        params = json.loads(args)
        invoice_id = params.get("invoice_id")
        if not invoice_id:
            return json.dumps({"success": False, "error": "invoice_id is required"})

        from ggg import Invoice

        invoice = Invoice[invoice_id]
        if invoice is None:
            return json.dumps(
                {"success": False, "error": f"Invoice '{invoice_id}' not found"}
            )

        result = yield invoice.refresh()

        return json.dumps({"success": True, "data": result})

    except Exception as e:
        logger.error(f"Error in refresh_invoice: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


def create_foundational_objects() -> void:
    """Create the foundational objects required for every realm to operate."""
    from ggg import Calendar, Identity, Profiles, Realm, Treasury, User, UserProfile
    from ggg.governance.calendar import DEFAULTS as CALENDAR_DEFAULTS

    logger.info("Creating foundational objects...")

    # Check if foundational objects already exist (for upgrades)
    if len(Realm.instances()) > 0:
        logger.info("Foundational objects already exist, skipping creation")
        return

    try:
        # 1. Create user profiles (all default profiles from Profiles.ALL_PROFILES)
        created_profiles = {}
        for profile_def in Profiles.ALL_PROFILES:
            p = UserProfile(
                name=profile_def["name"],
                allowed_to=",".join(profile_def["allowed_to"]),
                description=f"{profile_def['name'].capitalize()} user profile",
            )
            created_profiles[profile_def["name"]] = p

        profile_names = list(created_profiles.keys())
        logger.info(
            f"Created {len(profile_names)} user profiles: {', '.join(profile_names)}"
        )

        admin_profile = created_profiles["admin"]

        # 2. Create system user
        system_user = User(
            id="system",
        )
        # Link system user to admin profile
        system_user.profiles.add(admin_profile)

        logger.info("Created system user")

        # 3. Create identity for system user
        import uuid

        system_identity = Identity(
            type="system",
            metadata=f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:8]}",
        )

        logger.info("Created system identity")

        # 4. Create realm - try to load data from manifest.json if available
        realm_name = "Default Realm"
        realm_manifesto = "A realm for digital governance and coordination"
        realm_welcome_message = ""
        realm_open_registration = False

        import json
        import os

        manifest_json_str = "{}"  # default if no manifest.json found
        try:
            manifest_paths = [
                "manifest.json",
                "../manifest.json",
                "/manifest.json",
            ]
            for manifest_path in manifest_paths:
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                    realm_name = manifest.get("name", realm_name)
                    realm_manifesto = manifest.get("manifesto", realm_manifesto)
                    realm_welcome_message = manifest.get("welcome_message", "")
                    realm_open_registration = manifest.get("open_registration", False)
                    calendar_config = manifest.get("calendar", {})
                    acct_currency_config = manifest.get("accounting_currency", {})
                    manifest_json_str = json.dumps(manifest)
                    logger.info(
                        f"Loaded realm config from {manifest_path}: name={realm_name}"
                    )
                    break
            calendar_config = locals().get("calendar_config", {})
            acct_currency_config = locals().get("acct_currency_config", {})
        except Exception as e:
            logger.warning(f"Could not load manifest.json: {e}, using defaults")
            calendar_config = {}
            acct_currency_config = {}

        realm = Realm(
            name=realm_name,
            manifesto=realm_manifesto,
            welcome_message=realm_welcome_message,
            accounting_currency=acct_currency_config.get("symbol", "ckBTC"),
            accounting_currency_decimals=acct_currency_config.get("decimals", 8),
            principal_id="",
            manifest_data=manifest_json_str,
            open_registration=bool(realm_open_registration),
        )

        logger.info(f"Created realm: {realm_name}")

        # 5. Create calendar linked to realm
        calendar_epoch = int(ic.time() / 1_000_000_000)
        calendar = Calendar(
            name=f"{realm.name} Calendar",
            realm=realm,
            epoch=calendar_config.get("epoch", calendar_epoch),
            fiscal_period=calendar_config.get(
                "fiscal_period", CALENDAR_DEFAULTS["fiscal_period"]
            ),
            voting_window=calendar_config.get(
                "voting_window", CALENDAR_DEFAULTS["voting_window"]
            ),
            codex_release_cycle=calendar_config.get(
                "codex_release_cycle", CALENDAR_DEFAULTS["codex_release_cycle"]
            ),
            benefit_cycle=calendar_config.get(
                "benefit_cycle", CALENDAR_DEFAULTS["benefit_cycle"]
            ),
            service_payment_cycle=calendar_config.get(
                "service_payment_cycle", CALENDAR_DEFAULTS["service_payment_cycle"]
            ),
            license_review_cycle=calendar_config.get(
                "license_review_cycle", CALENDAR_DEFAULTS["license_review_cycle"]
            ),
            custom_cycles=json.dumps(calendar_config.get("custom_cycles", {})),
        )

        logger.info(
            f"Created calendar: epoch={calendar_epoch}, fiscal_period={calendar.fiscal_period}s, benefit_cycle={calendar.benefit_cycle}s"
        )

        # 6. Create treasury linked to realm
        treasury = Treasury(
            name=f"{realm.name} Treasury",
            vault_principal_id=None,  # Will be set during vault deployment
            realm=realm,
        )

        logger.info("Created treasury")

        # 7. Register well-known IC mainnet tokens so the invoice system can
        #    look up ledger/indexer canister IDs for payment detection.
        try:
            from ic_basilisk_toolkit.wallet import Wallet
            wallet = Wallet()
            wallet.register_well_known_tokens()
            logger.info("Registered well-known ICRC-1 tokens (ckBTC, ckUSDC, …)")
        except Exception as tok_err:
            logger.warning(f"Could not register well-known tokens: {tok_err}")

        logger.info("✅ All foundational objects created successfully")

    except Exception as e:
        logger.error(
            f"❌ Error creating foundational objects: {str(e)}\n{traceback.format_exc()}"
        )
        raise


def _register_wallet_transfer_hook():
    """Register the GGG permission check as the Basilisk OS Wallet pre-transfer hook."""
    try:
        from ic_basilisk_toolkit.wallet import Wallet
        from core.access import _check_access

        def realm_transfer_hook(
            token_name, to_principal, amount, from_subaccount=None, to_subaccount=None
        ):
            caller = ic.caller().to_str()
            canister_id = ic.id().to_str()
            if caller == canister_id:
                return None
            if not _check_access(caller, Operations.TRANSFER_CREATE):
                logger.warning(
                    f"Transfer blocked: {caller} lacks {Operations.TRANSFER_CREATE}"
                )
                return f"Access denied: principal {caller} lacks transfer.create permission"
            return None

        Wallet._pre_transfer_hook = realm_transfer_hook
        logger.info("Registered realm transfer hook on Basilisk OS Wallet")
    except Exception as e:
        logger.error(f"Failed to register wallet transfer hook: {e}")


def initialize() -> void:
    # Register all entity types from ggg
    import ggg
    from ggg import __all__ as entity_names

    for name in entity_names:
        try:
            entity_class = getattr(ggg, name)
            logger.info(f"Registering entity type {name}")
            Database.get_instance().register_entity_type(entity_class)
        except Exception as e:
            logger.error(
                f"Error registering entity type {name}: {str(e)}\n{traceback.format_exc()}"
            )

    # Register ic-basilisk-toolkit crypto entities
    from ic_basilisk_toolkit.crypto import CryptoGroup, CryptoGroupMember, KeyEnvelope

    for crypto_entity in (KeyEnvelope, CryptoGroup, CryptoGroupMember):
        try:
            Database.get_instance().register_entity_type(crypto_entity)
            logger.info(f"Registered crypto entity type {crypto_entity.__name__}")
        except Exception as e:
            logger.error(
                f"Error registering crypto entity {crypto_entity.__name__}: {e}"
            )

    # Create foundational objects after entity registration
    create_foundational_objects()

    # Ensure well-known IC mainnet tokens are in the registry.
    # register_token() is an upsert, so this is safe on every startup.
    try:
        from ic_basilisk_toolkit.wallet import Wallet
        Wallet().register_well_known_tokens()
        logger.info("Ensured well-known ICRC-1 tokens are registered")
    except Exception as e:
        logger.warning(f"Could not register well-known tokens: {e}")

    # Register OS-level wallet transfer hook for permission enforcement
    _register_wallet_transfer_hook()

    # Initialize all installed extensions
    logger.info("Discovering and initializing extensions...")

    try:
        # Get all installed extension manifests
        extension_manifests = api.extensions.get_all_extension_manifests()
        extension_ids = list(extension_manifests.keys())
        logger.info(f"Found {len(extension_ids)} installed extensions: {extension_ids}")

        # Track status for each extension
        extension_status = {}

        # Initialize each extension
        for extension_id in extension_ids:

            extension_manifest = extension_manifests.get(extension_id, {})
            entity_method_overrides = extension_manifest.get(
                "entity_method_overrides", []
            )

            if not entity_method_overrides:
                logger.info(f"No method overrides found for {extension_id}")
            else:
                logger.info(
                    f"Loading {len(entity_method_overrides)} method override(s) for {extension_id}"
                )
                for override in entity_method_overrides:
                    try:
                        entity_name = override.get("entity")
                        method_name = override.get("method")
                        impl_path = override.get("implementation")
                        method_type = override.get(
                            "type", "method"
                        )  # default to instance method

                        # Validate manifest data
                        if not all([entity_name, method_name, impl_path]):
                            logger.warning(
                                f"Invalid override in {extension_id}: missing entity/method/implementation"
                            )
                            continue

                        # Get entity class
                        entity_class = getattr(ggg, entity_name, None)
                        if not entity_class:
                            logger.warning(
                                f"Entity '{entity_name}' not found in ggg module"
                            )
                            continue

                        parts = impl_path.split(".")
                        func_name = parts[-1]

                        from core.runtime_extensions import _load_module
                        impl_module = _load_module(extension_id)
                        if impl_module is None:
                            logger.warning(f"Extension '{extension_id}' not installed (runtime)")
                            continue
                        impl_func = getattr(impl_module, func_name, None)

                        if not impl_func:
                            logger.warning(
                                f"Function '{func_name}' not found in {module_path}"
                            )
                            continue

                        # Bind method to entity (wrap as classmethod if specified)
                        if method_type == "classmethod":
                            setattr(entity_class, method_name, classmethod(impl_func))
                            logger.info(
                                f"  ✓ {entity_name}.{method_name}() [classmethod] -> {extension_id}.{impl_path}"
                            )
                        elif method_type == "staticmethod":
                            setattr(entity_class, method_name, staticmethod(impl_func))
                            logger.info(
                                f"  ✓ {entity_name}.{method_name}() [staticmethod] -> {extension_id}.{impl_path}"
                            )
                        else:
                            setattr(entity_class, method_name, impl_func)
                            logger.info(
                                f"  ✓ {entity_name}.{method_name}() -> {extension_id}.{impl_path}"
                            )

                    except Exception as e:
                        logger.error(
                            f"Error binding method override in {extension_id}: {str(e)}"
                        )
                        logger.error(traceback.format_exc())

            status = {
                "has_entities": False,
                "has_initialize": False,
                "entity_error": False,
                "init_error": False,
            }

            # Step 1: Try to register extension entity types
            try:
                from core.runtime_extensions import _load_module
                extension_module = _load_module(extension_id)

                if extension_module and hasattr(extension_module, "register_entities"):
                    extension_module.register_entities()
                    status["has_entities"] = True
            except Exception as e:
                logger.warning(
                    f"Error registering entity types for {extension_id}: {str(e)}"
                )
                status["entity_error"] = True

            # Step 2: Try to call extension initialize function
            try:
                result = api.extensions.extension_sync_call(
                    extension_id, "initialize", "{}"
                )
                status["has_initialize"] = True
            except Exception as e:
                # Log the actual error message to help debug
                error_msg = str(e)
                logger.info(
                    f"  [DEBUG] Extension {extension_id} initialize exception: {error_msg}"
                )

                # Check if it's a real error or just missing function
                # Common indicators that the function simply doesn't exist:
                missing_function_indicators = [
                    "not found",
                    "no function",
                    "has no",
                    "does not have",
                    "no attribute",
                    "'initialize'",
                    "attributeerror",
                ]

                is_missing_function = any(
                    indicator in error_msg.lower()
                    for indicator in missing_function_indicators
                )

                if not is_missing_function:
                    # This seems like a real error, not just a missing function
                    logger.warning(f"Error initializing {extension_id}: {error_msg}")
                    status["init_error"] = True
                # Otherwise it's just a missing function (optional), status stays False

            extension_status[extension_id] = status

        # Load entity method overrides from Realm manifest
        logger.info(
            "\n🔧 Checking for Codex entity method overrides from Realm manifest..."
        )
        try:
            import json

            from ggg import Codex, Realm

            realm = list(Realm.instances())[0] if Realm.instances() else None
            logger.info(f"Realm found: {realm.name if realm else 'None'}")

            if realm:
                logger.info(f"Has manifest_data: {bool(realm.manifest_data)}")
                if realm.manifest_data:
                    logger.info(
                        f"manifest_data length: {len(str(realm.manifest_data))}"
                    )
                    manifest = json.loads(str(realm.manifest_data))
                    logger.info(f"Parsed manifest keys: {list(manifest.keys())}")

                    overrides = manifest.get("entity_method_overrides", [])
                    logger.info(f"Found {len(overrides)} entity method overrides")

                    for o in overrides:
                        try:
                            if not all(
                                [
                                    o.get("entity"),
                                    o.get("method"),
                                    o.get("implementation"),
                                ]
                            ):
                                logger.warning(f"Skipping incomplete override: {o}")
                                continue
                            entity_class = getattr(ggg, o["entity"], None)
                            parts = o["implementation"].split(".")
                            if (
                                not entity_class
                                or len(parts) != 3
                                or parts[0] != "Codex"
                            ):
                                logger.warning(
                                    f"Invalid override config: entity_class={entity_class}, parts={parts}"
                                )
                                continue
                            target_codex = Codex[parts[1]]
                            if not target_codex:
                                logger.warning(f"Codex not found: {parts[1]}")
                                continue
                            method_type = o.get("type", "method")
                            proxy = _make_codex_proxy(parts[1], parts[2], method_type)
                            wrapper = (
                                classmethod(proxy)
                                if method_type == "classmethod"
                                else (
                                    staticmethod(proxy)
                                    if method_type == "staticmethod"
                                    else proxy
                                )
                            )
                            setattr(entity_class, o["method"], wrapper)
                            logger.info(
                                f"  ✓ {o['entity']}.{o['method']}() [{method_type}] -> {o['implementation']} [dynamic proxy]"
                            )
                        except Exception as e:
                            logger.error(f"Codex override error for {o}: {e}")
                else:
                    logger.warning("Realm.manifest_data is empty")
        except Exception as e:
            logger.error(
                f"Failed to load entity method overrides from Realm manifest: {e}"
            )

        # Print summary as a table
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 EXTENSION INITIALIZATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total extensions: {len(extension_ids)}")
        logger.info("")
        logger.info(
            f"{'Extension Name':<30} {'Entity Registration':<25} {'Initialize'}"
        )
        logger.info("-" * 70)

        for ext_id in sorted(extension_ids):
            status = extension_status[ext_id]

            # Format entity registration status
            if status["entity_error"]:
                entity_status = "❌ Error"
            elif status["has_entities"]:
                entity_status = "✅ Yes"
            else:
                entity_status = "➖ No"

            # Format initialize status
            if status["init_error"]:
                init_status = "❌ Error"
            elif status["has_initialize"]:
                init_status = "✅ Yes"
            else:
                init_status = "➖ No"

            logger.info(f"{ext_id:<30} {entity_status:<25} {init_status}")

        logger.info("=" * 70)
        logger.info("✅ Extension initialization complete.")
        logger.info("")

    except Exception as e:
        logger.error(
            f"❌ Critical error during extension initialization: {str(e)}\n{traceback.format_exc()}"
        )

    # Start TaskManager to schedule pending tasks with enabled schedules.
    # Timer callbacks MUST be created in init/post_upgrade context — closures
    # created from __shell__ do not survive IC call boundaries.
    # TaskManager.run() handles everything: loads all tasks from storage,
    # resets RUNNING->PENDING (timers lost on upgrade), re-registers timers.
    try:
        TaskManager().run()
        logger.info("✅ TaskManager started")
    except Exception as e:
        logger.error(
            f"❌ Error starting TaskManager: {str(e)}\n{traceback.format_exc()}"
        )

    # Seed the recurring population-sync task for federations that already have
    # sub-quarters (issue #156). New quarters seed it via register_quarter /
    # auto-scale, but a capital that gained its quarters before this code existed
    # (e.g. staging Agora) would otherwise never refresh their counts.
    #
    # Only seed when the task is ABSENT: the TaskManager().run() above already
    # recovers an *existing* recurring task (RUNNING->PENDING + reschedule), so
    # re-seeding it here would call run() a second time and leave the schedule
    # un-armed (the just-set last_run_at makes the interval check fail). Gated on
    # a sub-quarter existing so a lone capital doesn't schedule a no-op task.
    try:
        from ggg import Quarter, Task
        from core.quarter_bootstrap import POP_SYNC_TASK_NAME

        self_id = ic.id().to_str()
        has_quarters = any(
            (q.canister_id or "") and q.canister_id != self_id
            for q in Quarter.instances()
        )
        has_task = any(t.name == POP_SYNC_TASK_NAME for t in Task.instances())
        if has_quarters and not has_task:
            ensure_population_sync_task()
            logger.info("✅ Population-sync task seeded (sub-quarters present)")
    except Exception as e:
        logger.error(f"❌ Error ensuring population-sync task: {str(e)}")


@init
def init_() -> void:
    logger.info("Initializing Realm canister")
    set_controller(ic.caller().to_str())
    initialize()
    logger.info("Realm canister initialized")


@post_upgrade
def post_upgrade_() -> void:
    logger.info("Post-upgrade initializing Realm canister")
    set_controller(ic.caller().to_str())
    initialize()
    logger.info("Realm canister initialized")


@update
@require(Operations.REALM_ADMIN)
def test_timer() -> text:
    """Diagnostic: create entity now, set timer to modify it.

    1. Creates a TaskExecution with result='waiting' (verifiable immediately)
    2. Sets a 5s timer that changes result to 'timer_fired'
    3. Check later: if result is 'timer_fired', timers persist state
    """
    from _cdk import ic
    from ggg import TaskExecution

    te = TaskExecution(name="timer_diag", status="idle", result="waiting")
    te_id = str(te._id)

    def _test_cb():
        try:
            _te = TaskExecution.load(te_id)
            if _te:
                _te.result = "timer_fired"
                _te.status = "completed"
                ic.print(f"TIMER DIAG OK: updated {te_id}")
            else:
                ic.print(f"TIMER DIAG: could not load {te_id}")
        except Exception as e:
            ic.print(f"TIMER DIAG ERROR: {e}")

    tid = ic.set_timer(5, _test_cb)
    return (
        f"Created TaskExecution id={te_id} result=waiting, timer id={tid} fires in 5s"
    )


@update
@require(Operations.REALM_ADMIN)
def start_task_manager() -> text:
    """Start TaskManager to schedule pending tasks.

    Call this after data import to set up IC timers in the proper
    canister update context.  Timer callbacks created from
    __shell__ do NOT survive IC call boundaries.
    """
    try:
        # Relationships resolve via persisted reverse indexes (ic-python-db >= 0.9)
        # — no need to eagerly load child entity types.
        all_tasks = Task.load_some(1, Task.max_id()) if Task.max_id() > 0 else []

        manager = TaskManager()
        count = 0
        for t in all_tasks:
            if t.status and t.status != "completed":
                t.status = "pending"
                t.step_to_execute = 0
                for step in t.steps:
                    step.status = "pending"
                    step.timer_id = None
            manager.add_task(t)
            count += 1
        manager.run()
        msg = f"TaskManager started with {count} task(s)"
        logger.info(msg)
        return msg
    except Exception as e:
        err = f"Error starting TaskManager: {str(e)}\n{traceback.format_exc()}"
        logger.error(err)
        return err


@query
def extension_call(extension_name: text, function_name: text, args: text) -> ExtensionCallResponse:
    """Query version of extension call for read-only operations like get_entity_types."""
    try:
        logger.debug(
            f"Query calling extension '{extension_name}' function '{function_name}' with args {args}"
        )

        extension_result = api.extensions.extension_sync_call(
            extension_name, function_name, args
        )

        logger.debug(
            f"Got extension result from {extension_name} function {function_name}: {extension_result}"
        )

        response = (
            extension_result
            if isinstance(extension_result, str)
            else json.dumps(extension_result)
        )
        return ExtensionCallResponse(success=True, response=response)

    except Exception as e:
        logger.error(f"Error in extension_call: {str(e)}\n{traceback.format_exc()}")
        return ExtensionCallResponse(success=False, response=str(e))


@update
def extension_sync_call(extension_name: text, function_name: text, args: text) -> ExtensionCallResponse:
    try:
        caller = ic.caller().to_str()
        if not _check_access(caller, Operations.EXTENSION_SYNC_CALL):
            return ExtensionCallResponse(
                success=False,
                response=json.dumps({
                    "error": f"Access denied: you lack permission '{Operations.EXTENSION_SYNC_CALL}'",
                    "denied_operation": Operations.EXTENSION_SYNC_CALL,
                }),
            )
        logger.debug(
            f"Sync calling extension '{extension_name}' entry point '{function_name}' with args {args}"
        )

        extension_result = api.extensions.extension_sync_call(
            extension_name, function_name, args
        )

        logger.debug(
            f"Got extension result from {extension_name} function {function_name}: {extension_result}, type: {type(extension_result)}"
        )

        response = (
            extension_result
            if isinstance(extension_result, str)
            else json.dumps(extension_result)
        )
        return ExtensionCallResponse(success=True, response=response)

    except Exception as e:
        logger.error(f"Error calling extension: {str(e)}\n{traceback.format_exc()}")
        return ExtensionCallResponse(success=False, response=str(e))


@update
def extension_async_call(extension_name: text, function_name: text, args: text) -> Async[ExtensionCallResponse]:
    try:
        caller = ic.caller().to_str()
        if not _check_access(caller, Operations.EXTENSION_ASYNC_CALL):
            return ExtensionCallResponse(
                success=False,
                response=json.dumps({
                    "error": f"Access denied: you lack permission '{Operations.EXTENSION_ASYNC_CALL}'",
                    "denied_operation": Operations.EXTENSION_ASYNC_CALL,
                }),
            )
        logger.debug(
            f"Async calling extension '{extension_name}' entry point '{function_name}' with args {args}"
        )

        extension_coroutine = api.extensions.extension_async_call(
            extension_name, function_name, args
        )
        extension_result = yield extension_coroutine

        logger.debug(
            f"Got extension result from {extension_name} function {function_name}: {extension_result}, type: {type(extension_result)}"
        )

        response = (
            extension_result
            if isinstance(extension_result, str)
            else json.dumps(extension_result)
        )
        return ExtensionCallResponse(success=True, response=response)

    except Exception as e:
        logger.error(f"Error calling extension: {str(e)}\n{traceback.format_exc()}")
        return ExtensionCallResponse(success=False, response=str(e))


def http_request_core(data):
    d = json.dumps(data)
    return {
        "status_code": 200,
        "headers": [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
        ],
        "body": bytes(d + "\n", "ascii"),
        "streaming_strategy": None,
        "upgrade": False,
    }


def http_request_404():
    return {
        "status_code": 404,
        "headers": [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
        ],
        "body": b'{"error": "Not found"}\n',
        "streaming_strategy": None,
        "upgrade": False,
    }


@query
def http_request(req: HttpRequest) -> HttpResponseIncoming:
    """Handle HTTP requests to the canister. Only for unauthenticated read operations."""
    try:
        method = req["method"]
        url = req["url"]

        logger.info(f"HTTP {method} request to {url}")

        not_found = HttpResponseIncoming(
            status_code=404,
            headers=[],
            body=bytes("Not found", "ascii"),
            streaming_strategy=None,
            upgrade=False,
        )

        if method == "GET":
            # Strip leading slash and query params
            path = url.lstrip("/").split("?")[0]

            # Handle /status
            if path == "status" or path == "":
                return http_request_core(get_status())
            # Handle /extensions
            elif path == "extensions":
                return http_request_core({"extensions": list_extensions()})

        return not_found
    except Exception as e:
        logger.error(f"Error handling HTTP request: {str(e)}\n{traceback.format_exc()}")
        return {
            "status_code": 500,
            "headers": [],
            "body": bytes(traceback.format_exc(), "ascii"),
            "streaming_strategy": None,
            "upgrade": False,
        }


@query
def http_transform(args: HttpTransformArgs) -> HttpResponse:
    """Transform function for HTTP requests - removes headers for consensus"""
    http_response = args["response"]
    http_response["headers"] = []
    return http_response


_shell_ns_by_principal = {}


@update
@require(Operations.SHELL_EXECUTE)
def __shell__(code: str) -> str:
    """Executes Python code in a persistent namespace and returns the output.

    This is the core function needed for the Basilisk Simple Shell to work.
    It captures stdout and stderr from the executed code.  The namespace
    persists across calls per caller principal, so variables defined in one
    command are available in subsequent commands (like a normal interactive
    Python session).  Each principal gets its own isolated session.
    """
    import io
    import sys
    import traceback

    from core.execution import _ensure_codex_lazy_loading

    _ensure_codex_lazy_loading()

    global _shell_ns_by_principal
    caller = str(ic.caller())
    if caller not in _shell_ns_by_principal:
        import _cdk as basilisk
        import ggg

        _shell_ns_by_principal[caller] = {"__builtins__": __builtins__}
        _shell_ns_by_principal[caller].update(
            {
                "ggg": ggg,
                "basilisk": basilisk,
                "ic": ic,
            }
        )
        for _name in ggg.__all__:
            _shell_ns_by_principal[caller][_name] = getattr(ggg, _name)
    ns = _shell_ns_by_principal[caller]

    stdout = io.StringIO()
    stderr = io.StringIO()
    sys.stdout = stdout
    sys.stderr = stderr

    try:
        exec(code, ns, ns)
    except Exception:
        traceback.print_exc()

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    return stdout.getvalue() + stderr.getvalue()


# Removed endpoints (use __shell__ + basilisk shell commands instead):
#   execute_code, download_to_file, download_file, get_task_status,
#   list_scheduled_tasks, stop_task, start_task, get_task_logs,
#   get_task_logs_by_name, create_scheduled_task


@update
@require(Operations.TASK_CREATE)
def create_multi_step_scheduled_task(
    name: str,
    steps_config: str,
    repeat_every: nat,
    run_after: nat = 5,
) -> str:
    """
    Create a multi-step scheduled task from multiple code snippets.

    Args:
        name: Task name
        steps_config: JSON array of step configurations:
            [
                {
                    "code": "<base64-encoded-code>",
                    "run_next_after": seconds (optional, default 0)
                },
                ...
            ]
        repeat_every: Interval in seconds (0 for one-time execution)
        run_after: Delay before first execution in seconds (default: 5)

    Returns JSON with:
    - success: Boolean indicating success
    - task_id: The created task ID
    - task_name: The task name
    - schedule_id: The schedule ID
    - steps_count: Number of steps in the task
    - run_at: Scheduled execution time
    - repeat_every: Repeat interval
    - error: Error message if failed

    Note: is_async is automatically detected based on code content
          (presence of 'yield' or 'async_task')
    """
    try:
        # Parse steps configuration
        steps_data = json.loads(steps_config)

        if not steps_data or len(steps_data) == 0:
            raise ValueError("At least one step is required")

        # Create TaskStep objects
        task_steps = []
        for idx, step_config in enumerate(steps_data):
            # Decode base64 code
            try:
                decoded_code = base64.b64decode(step_config["code"]).decode("utf-8")
            except Exception as e:
                raise ValueError(f"Invalid base64 code in step {idx}: {e}")

            # Create codex for this step
            codex_name = f"_{name}_step_{idx}_{int(ic.time())}"
            codex = Codex(name=codex_name, code=decoded_code)

            # Create call
            call = Call(codex=codex)

            # Get run_next_after delay (default to 0)
            run_next_after = step_config.get("run_next_after", 0)

            # Create step (task assigned after Task creation below)
            step = TaskStep(call=call, run_next_after=run_next_after)
            task_steps.append(step)

            logger.info(
                f"Created step {idx}: codex={codex_name}, "
                f"run_next_after={run_next_after}s"
            )

        # Create task, then link steps via ManyToOne
        task = Task(name=name)
        for step in task_steps:
            step.task = task

        # Create schedule
        schedule = TaskSchedule(
            name=f"schedule_{name}",
            task=task,
            run_at=0,
            repeat_every=repeat_every,
            last_run_at=0,
            disabled=False,
        )

        # Register with TaskManager
        manager = TaskManager()
        manager.add_task(task)

        logger.info(
            f"Created multi-step task: {name} (ID: {task._id}) "
            f"with {len(task_steps)} steps"
        )

        # Trigger task manager to process the schedule
        manager.run()

        return json.dumps(
            {
                "success": True,
                "task_id": str(task._id),
                "task_name": str(task.name),
                "schedule_id": str(schedule._id),
                "steps_count": len(task_steps),
                "run_at": int(schedule.run_at),
                "repeat_every": int(schedule.repeat_every),
            },
            indent=2,
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in steps_config: {e}")
        return json.dumps({"success": False, "error": f"Invalid JSON: {str(e)}"})
    except Exception as e:
        logger.error(f"Error creating multi-step task: {e}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@update
@require(Operations.REALM_REGISTER)
def register_realm_with_registry(
    registry_canister_id: text,
    realm_name: text,
    frontend_url: text = "",
    canister_ids_json: text = "{}",
) -> Async[text]:
    """
    Register this realm with the central registry.

    Makes an inter-canister call to the realm_registry_backend to register
    this realm. The registry uses ic.caller() (this backend's canister ID)
    as the unique realm ID, preventing duplicates via upsert logic.

    Args:
        registry_canister_id: Canister ID of the realm registry backend
        realm_name: Display name for this realm
        frontend_url: Frontend canister URL (optional)
        canister_ids_json: Pipe-delimited string: frontend_id|token_id|nft_id

    Returns:
        JSON string with success status and message
    """
    try:
        canister_ids = {}
        if canister_ids_json and "|" in canister_ids_json:
            parts = canister_ids_json.split("|")
            canister_ids = {
                "frontend_canister_id": parts[0] if len(parts) > 0 else "",
                "token_canister_id": parts[1] if len(parts) > 1 else "",
                "nft_canister_id": parts[2] if len(parts) > 2 else "",
            }

        result = yield register_realm(
            registry_canister_id, realm_name, frontend_url, "", canister_ids
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in register_realm_with_registry: {e}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@query
def get_realm_registry_info() -> text:
    """
    Get information about registries this realm is registered with.

    Returns:
        JSON string with list of registries
    """
    try:
        result = get_registry_info()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_realm_registry_info: {e}")
        return json.dumps(
            {"success": False, "error": str(e), "registries": []}, indent=2
        )


# ── Inter-realm messaging ──────────────────────────────────────────────

@update
@require(Operations.REALM_ADMIN)
def send_realm_message(
    target_canister_id: text,
    title: text,
    message: text,
    topic: text = "",
) -> Async[text]:
    """Send a public message from this realm to another realm.

    Admin-only. Cross-realm messages are always public on the receiving end.

    Args:
        target_canister_id: Canister ID of the target realm's backend.
        title: Message title.
        message: Message body.
        topic: Optional topic label.
    """
    try:
        from ggg import Realm

        realm = Realm.load("1")
        origin_name = getattr(realm, "name", "") if realm else ""

        result = yield _send_realm_message(
            target_canister_id, title, message, topic, origin_name
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in send_realm_message: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@update
@require_controller
def receive_realm_message(
    title: text,
    message: text,
    topic: text,
    origin_name: text,
) -> text:
    """Receive a public message from another realm (inter-canister entry point).

    Restricted to controllers / trusted principals (the sending realm canister
    must be trusted by this realm). Stored as a public, realm-wide notification
    so every user can read it; cross-realm messages can never be private.
    """
    try:
        from ggg import Notification

        sender_canister = ic.caller().to_str()
        notification = Notification(
            topic=topic or "inter-realm",
            title=title,
            message=message,
            sender=origin_name or sender_canister,
            origin_realm=sender_canister,
            visibility="public",
            audience_type="realm",
            read=False,
            read_by="",
            icon="mail",
            href="/messages",
            color="purple",
            metadata="{}",
        )
        logger.info(
            f"Received inter-realm message from {sender_canister} "
            f"({origin_name!r}): {title!r} -> notification {notification._id}"
        )
        return json.dumps({"success": True, "id": notification._id})
    except Exception as e:
        logger.error(f"Error in receive_realm_message: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


# ── Realm self-upgrade endpoints ───────────────────────────────────────

@update
@require(Operations.REALM_UPGRADE)
def request_upgrade(registry_canister_id: text = "") -> Async[text]:
    """Request an upgrade to the latest realm version.

    Calls the registry to validate credits and cycles, then enqueues
    the upgrade via the installer/deployer pipeline.

    Args:
        registry_canister_id: Optional override for registry canister ID.
            If empty, uses the first registered registry.
    """
    from api.upgrade import request_upgrade as _do_upgrade, _get_registry_canister_id

    try:
        reg_id = registry_canister_id.strip() if registry_canister_id else ""
        if not reg_id:
            reg_id = _get_registry_canister_id()
        if not reg_id:
            return json.dumps({"success": False,
                "error": "No registry canister configured. Set via set_canister_config or register first."})

        result = yield _do_upgrade(reg_id)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in request_upgrade: {e}")
        return json.dumps({"success": False, "error": str(e)})


@query
def get_upgrade_status() -> text:
    """Get the status of the last upgrade request.

    Returns the job_id of the most recent upgrade and its current version.
    """
    from api.upgrade import get_last_upgrade_job_id
    from api.status import get_status

    try:
        job_id = get_last_upgrade_job_id()
        status = get_status()
        current_version = status.get("version", "")
        return json.dumps({
            "success": True,
            "job_id": job_id,
            "current_version": current_version,
            "has_pending_upgrade": bool(job_id),
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.REALM_UPGRADE)
def get_realm_credits(registry_canister_id: text = "") -> Async[text]:
    """Get this realm's credit balance from the registry.

    Args:
        registry_canister_id: Optional override for registry canister ID.
    """
    from api.upgrade import get_realm_credits as _get_credits, _get_registry_canister_id

    try:
        reg_id = registry_canister_id.strip() if registry_canister_id else ""
        if not reg_id:
            reg_id = _get_registry_canister_id()
        if not reg_id:
            return json.dumps({"success": False,
                "error": "No registry canister configured"})

        result = yield _get_credits(reg_id)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.REALM_UPGRADE)
def get_available_upgrade(registry_canister_id: text = "") -> Async[text]:
    """Check if a newer version is available for upgrade.

    Args:
        registry_canister_id: Optional override for registry canister ID.
    """
    from api.upgrade import get_available_version, _get_registry_canister_id
    from api.status import get_status

    try:
        reg_id = registry_canister_id.strip() if registry_canister_id else ""
        if not reg_id:
            reg_id = _get_registry_canister_id()
        if not reg_id:
            return json.dumps({"success": False,
                "error": "No registry canister configured"})

        result = yield get_available_version(reg_id)
        if not result.get("success"):
            return json.dumps(result)

        status = get_status()
        current_version = status.get("version", "")
        latest = result.get("version", {})
        latest_version = latest.get("version", "")

        return json.dumps({
            "success": True,
            "current_version": current_version,
            "latest_version": latest_version,
            "upgrade_available": bool(latest_version and latest_version != current_version),
            "latest": latest,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.NFT_MINT)
def mint_land_nft_for_parcel(
    land_id: text,
    owner_principal: text,
    token_id: nat,
    nft_canister_id: text = "",
) -> Async[text]:
    """
    Mint a LAND NFT for a registered land parcel.

    Makes an inter-canister call to the realm's NFT canister to mint
    an NFT representing ownership of the land parcel.

    Args:
        land_id: ID of the land parcel
        owner_principal: Principal ID of the land owner
        token_id: Unique token ID for the NFT
        nft_canister_id: Optional NFT canister ID (uses config if not provided)

    Returns:
        JSON string with success status and token_id
    """
    try:
        from ggg import Land

        # Get the land parcel
        land = Land[land_id]
        if not land:
            return json.dumps({"success": False, "error": f"Land {land_id} not found"})

        # Get NFT canister ID from config if not provided
        canister_id = nft_canister_id or get_nft_canister_id()
        if not canister_id:
            return json.dumps(
                {"success": False, "error": "NFT canister ID not configured"}
            )

        # Mint the NFT
        result = yield mint_land_nft(
            nft_canister_id=canister_id,
            token_id=int(token_id),
            owner_principal=owner_principal,
            land_id=land_id,
            x_coordinate=land.x_coordinate,
            y_coordinate=land.y_coordinate,
            land_type=land.land_type,
        )

        # Update land with NFT token ID if successful
        if result.get("success"):
            land.nft_token_id = result.get("token_id", "")
            logger.info(f"Updated land {land_id} with nft_token_id={land.nft_token_id}")

        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in mint_land_nft_for_parcel: {e}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@query
def get_nft_config() -> text:
    """
    Get the NFT canister configuration for this realm.

    Returns:
        JSON string with NFT canister ID
    """
    try:
        canister_id = get_nft_canister_id()
        return json.dumps(
            {
                "success": True,
                "nft_canister_id": canister_id or "",
                "configured": bool(canister_id),
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Error in get_nft_config: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@update
def update_realm_config(config_json: str) -> str:
    """
    Update the realm configuration (name, manifesto, welcome_message,
    branding, registration, and infrastructure settings).

    Infrastructure fields (file_registry_canister_id, marketplace_canister_id)
    require the stronger ``realm.configure.infrastructure`` permission.

    Args:
        config_json: JSON string containing realm configuration fields
    """
    logger.info("🔧 update_realm_config() called")
    try:
        import json

        caller = ic.caller().to_str()
        if not _check_access(caller, Operations.REALM_CONFIGURE):
            return json.dumps({
                "success": False,
                "error": f"Access denied: you lack permission '{Operations.REALM_CONFIGURE}'",
                "denied_operation": Operations.REALM_CONFIGURE,
            })

        from ggg import Realm

        config = json.loads(config_json)
        logger.info(f"📋 Config received: {list(config.keys())}")

        infra_keys = {"file_registry_canister_id", "marketplace_canister_id"}
        has_infra_change = bool(infra_keys & set(config.keys()))
        if has_infra_change and not _check_access(caller, Operations.REALM_CONFIGURE_INFRASTRUCTURE):
            return json.dumps({
                "success": False,
                "error": f"Access denied: you lack permission '{Operations.REALM_CONFIGURE_INFRASTRUCTURE}'",
                "denied_operation": Operations.REALM_CONFIGURE_INFRASTRUCTURE,
            })

        realms = list(Realm.instances())
        if not realms:
            logger.error("❌ No realm found")
            return json.dumps({"success": False, "error": "No realm found"})

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
            realm.open_registration = bool(config["open_registration"])
            updated_fields.append(f"open_registration={realm.open_registration}")

        if "quarter_join_mode" in config:
            mode = str(config["quarter_join_mode"] or "auto").strip().lower()
            if mode not in ("auto", "choice"):
                return json.dumps({
                    "success": False,
                    "error": "quarter_join_mode must be 'auto' or 'choice'",
                })
            realm.quarter_join_mode = mode
            updated_fields.append(f"quarter_join_mode={realm.quarter_join_mode}")

        if "ai_assistant_enabled" in config:
            realm.ai_assistant_enabled = bool(config["ai_assistant_enabled"])
            updated_fields.append(f"ai_assistant_enabled={realm.ai_assistant_enabled}")

        if "logo_url" in config:
            realm.logo_url = config["logo_url"] or ""
            updated_fields.append(f"logo_url={realm.logo_url[:50]}...")

        if "background_image_url" in config:
            realm.background_image_url = config["background_image_url"] or ""
            updated_fields.append(f"background_image_url={realm.background_image_url[:50]}...")

        if "file_registry_canister_id" in config:
            realm.file_registry_canister_id = config["file_registry_canister_id"] or ""
            updated_fields.append(f"file_registry_canister_id={realm.file_registry_canister_id}")

        if "marketplace_canister_id" in config:
            realm.marketplace_canister_id = config["marketplace_canister_id"] or ""
            updated_fields.append(f"marketplace_canister_id={realm.marketplace_canister_id}")

        logger.info(f"✅ Realm config updated: {', '.join(updated_fields)}")
        return json.dumps({"success": True, "updated_fields": updated_fields})
    except Exception as e:
        logger.error(f"❌ update_realm_config failed: {e}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.REALM_CONFIGURE_CODEX)
def reload_entity_method_overrides() -> str:
    """
    Admin function to reload entity method overrides from Realm manifest.
    This should be called after importing realm data that includes codexes and manifest_data.
    """
    logger.info("🔄 reload_entity_method_overrides() called")
    try:
        import json

        import ggg
        from ggg import Codex, Realm

        logger.info("📜 Looking for Codex['manifest']...")
        realm_manifest = Codex["manifest"]
        if not realm_manifest:
            logger.error("❌ No Codex['manifest'] found")
            return json.dumps({"success": False, "error": "No realm manifest found"})

        logger.info(
            f"✅ Found manifest codex (code length: {len(str(realm_manifest.code))} chars)"
        )
        manifest = json.loads(str(realm_manifest.code))
        overrides = manifest.get("entity_method_overrides", [])
        logger.info(f"📋 Found {len(overrides)} override(s) in manifest")

        loaded_overrides = []
        for i, o in enumerate(overrides):
            logger.info(
                f"  [{i+1}/{len(overrides)}] Processing: {o.get('entity', '?')}.{o.get('method', '?')}()"
            )
            try:
                if not all([o.get("entity"), o.get("method"), o.get("implementation")]):
                    logger.warning(
                        f"    ⚠️ Skipping - missing required fields (entity/method/implementation)"
                    )
                    continue

                entity_class = getattr(ggg, o["entity"], None)
                if not entity_class:
                    logger.warning(
                        f"    ⚠️ Skipping - entity class '{o['entity']}' not found in ggg"
                    )
                    continue

                parts = o["implementation"].split(".")
                if len(parts) != 3 or parts[0] != "Codex":
                    logger.warning(
                        f"    ⚠️ Skipping - invalid implementation format: {o['implementation']} (expected Codex.name.function)"
                    )
                    continue

                codex_name = parts[1]
                func_name = parts[2]
                logger.info(f"    🔍 Looking for Codex['{codex_name}']...")
                target_codex = Codex[codex_name]
                if not target_codex:
                    logger.warning(f"    ⚠️ Skipping - Codex['{codex_name}'] not found")
                    continue

                logger.info(
                    f"    ✅ Found codex '{codex_name}' (code length: {len(str(target_codex.code))} chars)"
                )

                method_type = o.get("type", "method")
                proxy = _make_codex_proxy(codex_name, func_name, method_type)
                wrapper = (
                    classmethod(proxy)
                    if method_type == "classmethod"
                    else staticmethod(proxy) if method_type == "staticmethod" else proxy
                )
                setattr(entity_class, o["method"], wrapper)
                loaded_overrides.append(
                    f"{o['entity']}.{o['method']}() -> {o['implementation']}"
                )
                logger.info(
                    f"    ✅ Successfully loaded {o['entity']}.{o['method']}() [{method_type}] -> {o['implementation']} [dynamic proxy]"
                )
            except Exception as e:
                logger.error(f"    ❌ Failed to reload override: {e}")

        logger.info(
            f"🏁 Completed: {len(loaded_overrides)}/{len(overrides)} overrides loaded successfully"
        )
        return json.dumps(
            {"success": True, "loaded_overrides": loaded_overrides}, indent=2
        )
    except Exception as e:
        logger.error(f"❌ reload_entity_method_overrides failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


# ---------------------------------------------------------------------------
# Runtime Extension Management (Layer 2)
# See: https://github.com/smart-social-contracts/realms/issues/168
# ---------------------------------------------------------------------------


@update
@require(Operations.EXTENSION_INSTALL)
def install_extension(args: text) -> text:
    """Install a runtime extension from uploaded files.

    Args (JSON): {
        "extension_id": str,
        "files": {"filename": "content", ...}
    }

    At minimum, files must include "entry.py" and "manifest.json".
    Files are written to /extensions/{extension_id}/ on the persistent filesystem.
    """
    try:
        params = json.loads(args)
        ext_id = params.get("extension_id")
        files = params.get("files", {})

        if not ext_id:
            return json.dumps({"success": False, "error": "extension_id is required"})
        if not files:
            return json.dumps({"success": False, "error": "files dict is required"})

        from core.runtime_extensions import install_extension as _install

        ok = _install(ext_id, files)
        if ok:
            return json.dumps({"success": True, "extension_id": ext_id, "files_count": len(files)})
        else:
            return json.dumps({"success": False, "error": f"Failed to load extension '{ext_id}' after install"})
    except Exception as e:
        logger.error(f"install_extension error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.EXTENSION_UNINSTALL)
def uninstall_extension(args: text) -> text:
    """Uninstall a runtime extension.

    Args (JSON): {"extension_id": str}
    """
    try:
        params = json.loads(args)
        ext_id = params.get("extension_id")

        if not ext_id:
            return json.dumps({"success": False, "error": "extension_id is required"})

        from core.core_extensions import is_core_extension
        if is_core_extension(ext_id):
            return json.dumps({
                "success": False,
                "error": (
                    f"Extension '{ext_id}' is a core extension and cannot be uninstalled. "
                    "Disable the AI assistant in Realm Settings instead of removing llm_chat."
                    if ext_id == "llm_chat"
                    else f"Extension '{ext_id}' is a core extension and cannot be uninstalled."
                ),
            })

        from core.runtime_extensions import uninstall_extension as _uninstall

        ok = _uninstall(ext_id)
        if ok:
            return json.dumps({"success": True, "extension_id": ext_id})
        else:
            return json.dumps({"success": False, "error": f"Extension '{ext_id}' not found"})
    except Exception as e:
        logger.error(f"uninstall_extension error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@query
def list_runtime_extensions() -> text:
    """List all runtime-installed extensions with their manifests."""
    try:
        from core.runtime_extensions import (
            get_all_extension_manifests,
            get_extension_source,
            list_installed,
        )

        installed = list_installed()
        manifests = get_all_extension_manifests()
        sources = {ext_id: get_extension_source(ext_id) for ext_id in installed}
        return json.dumps({
            "success": True,
            "runtime_extensions": installed,
            "all_manifests": manifests,
            "sources": sources,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@query
def get_sidebar_manifests() -> text:
    """Return the slim sidebar-relevant slice of every installed extension's
    manifest, intended to be the single source of truth for the sidebar
    (Issue #168 — Layered Realm).

    Combines runtime-installed extensions and any still-bundled extensions
    so the realm_frontend Sidebar.svelte can call exactly one backend
    method regardless of how an extension was installed. The "kind" field
    reflects how it got there:

      - ``runtime``: installed via install_extension / install_extension_from_registry,
                     loaded as ESM at runtime via /extensions/<id>.
      - ``bundled``: shipped inside this realm_backend WASM (legacy path).

    Response (JSON):
      {
        "success": True,
        "manifests": [
          {
            "id":               "voting",
            "name":             "voting",
            "version":          "1.0.3",
            "icon":             "ClipboardListSolid",   # name in iconMap
            "categories":       ["public_services"],
            "profiles":         ["admin", "member"],
            "show_in_sidebar":  true,
            "sidebar_label":    {"en": "Voting", "de": "Abstimmung"},
            "kind":             "runtime"               # or "bundled"
          },
          ...
        ]
      }
    """
    try:
        from core.runtime_extensions import (
            get_all_extension_manifests,
            list_installed as _list_runtime_installed,
        )

        runtime_ids = set(_list_runtime_installed())
        manifests = get_all_extension_manifests()  # merged: runtime + bundled

        out = []
        for ext_id, m in manifests.items():
            if not isinstance(m, dict):
                continue
            label_obj = m.get("sidebar_label")
            if isinstance(label_obj, str):
                label_obj = {"en": label_obj}
            out.append({
                "id": ext_id,
                "name": m.get("name") or ext_id,
                "version": m.get("version"),
                "icon": m.get("icon"),
                "categories": m.get("categories") or ["other"],
                "profiles": m.get("profiles") or [],
                "show_in_sidebar": m.get("show_in_sidebar", True) is not False,
                "sidebar_label": label_obj,
                "kind": "runtime" if ext_id in runtime_ids else "bundled",
            })

        out.sort(key=lambda e: (e["categories"][0] if e["categories"] else "z", e["id"]))

        categories_meta = [
            {"id": "public_services", "name": "Public Services", "order": 1, "show_header": True, "collapsible": False},
            {"id": "governance", "name": "Governance", "order": 2, "show_header": True, "collapsible": False},
            {"id": "administration", "name": "Administration", "order": 3, "show_header": True, "collapsible": False},
            {"id": "land_territory", "name": "Territory", "order": 4, "show_header": True, "collapsible": False},
            {"id": "finances", "name": "Finances", "order": 5, "show_header": True, "collapsible": False},
            {"id": "settings", "name": "Settings", "order": 6, "show_header": True, "collapsible": False},
            {"id": "other", "name": "Other", "order": 99, "show_header": True, "collapsible": True},
        ]

        return json.dumps({"success": True, "manifests": out, "categories": categories_meta})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


DEFAULT_CATEGORY_ORDER = [
    ("public_services", "Public Services", 1),
    ("governance", "Governance", 2),
    ("administration", "Administration", 3),
    ("land_territory", "Territory", 4),
    ("finances", "Finances", 5),
    ("settings", "Settings", 6),
    ("other", "Other", 99),
]

DEFAULT_ITEM_ORDER = {
    "governance": ["voting", "codex_viewer"],
    "finances": ["vault", "metrics"],
    "settings": ["extensions_manager", "package_manager", "managed_services"],
}


@query
def get_sidebar(args: text) -> text:
    """Return the fully resolved sidebar structure for the calling user.

    Merges extension manifests, hardcoded default category order,
    database overrides (MenuCategoryConfig, MenuItemConfig), and
    department visibility (MenuDepartmentVisibility).

    Response (JSON): {
        "success": true,
        "welcome_items": [...],       # is_default extensions (top, no category)
        "categories": [               # ordered categories with ordered items
            {"id": "public_services", "label": "Public Services", "items": [...]},
            ...
        ],
        "default_path": "/extensions/member_dashboard"
    }
    """
    try:
        from core.runtime_extensions import (
            get_all_extension_manifests,
            list_installed as _list_runtime_installed,
        )
        from ggg import Extension, MenuCategoryConfig, MenuDepartmentVisibility, MenuItemConfig, User

        caller = ic.caller().to_str()
        params = json.loads(args) if args else {}
        locale = params.get("locale", "en")

        user = User[caller]
        user_profiles = []
        user_departments = []
        if user:
            user_profiles = [p.name for p in user.profiles] if user.profiles else []
            user_departments = [d.name for d in user.departments] if user.departments else []

        manifests = get_all_extension_manifests()

        # Determine which extensions are visible to this user.
        #
        # Strict DB-based whitelist filtering is applied ONLY to extensions
        # that have actually been seeded with access grants in the database.
        # Extensions with no DB grants fall back to manifest-level profile
        # matching. This per-extension fallback means a partial seed (e.g.
        # installing a single extension, which links only that one to its
        # profiles) never hides every other extension that has not yet been
        # seeded, while still honoring explicit DB grants where they exist.
        user_granted = _user_granted_extension_names(user)
        seeded_extensions = _seeded_extension_names()

        # Apply department visibility rules
        hidden_by_dept = set()
        for rule in MenuDepartmentVisibility.instances():
            if not rule.visible and rule.department:
                if rule.department.name in user_departments:
                    hidden_by_dept.add(rule.extension_name)

        # Load category order overrides from DB
        db_category_configs = {c.category_id: c for c in MenuCategoryConfig.instances()}

        # Load item placement overrides from DB
        db_item_configs = {i.extension_name: i for i in MenuItemConfig.instances()}

        # Resolve category ordering: DB overrides > defaults
        category_order = {}
        category_labels = {}
        for cat_id, label, order in DEFAULT_CATEGORY_ORDER:
            category_order[cat_id] = order
            category_labels[cat_id] = label
        for cat_id, config in db_category_configs.items():
            category_order[cat_id] = config.position
            if config.label:
                category_labels[cat_id] = config.label

        # Filter and group extensions
        welcome_items = []
        mundus_items = []
        grouped = {}

        for ext_id, m in manifests.items():
            if not isinstance(m, dict):
                continue
            if m.get("show_in_sidebar", True) is False:
                continue
            if ext_id in hidden_by_dept:
                continue

            # Profile-based filtering (per-extension: strict whitelist only for
            # seeded extensions, manifest fallback for the rest).
            ext_profiles = m.get("profiles") or []
            if ext_id in seeded_extensions:
                if ext_id not in user_granted:
                    continue
            elif ext_profiles:
                if not any(p in user_profiles for p in ext_profiles):
                    continue

            label_obj = m.get("sidebar_label") or {}
            if isinstance(label_obj, str):
                label_obj = {"en": label_obj}
            item_label = label_obj.get(locale) or label_obj.get("en") or ext_id.replace("_", " ").title()

            _raw_desc = (m.get("short_description") or m.get("description") or "").strip()
            if _raw_desc:
                _tooltip = _raw_desc
                for _sep in [". ", " — ", " - "]:
                    _idx = _raw_desc.find(_sep)
                    if 0 < _idx <= 75:
                        _tooltip = _raw_desc[:_idx].rstrip(".")
                        break
                else:
                    if len(_raw_desc) > 70:
                        _t = _raw_desc[:70]
                        _sp = _t.rfind(" ")
                        _tooltip = (_t[:_sp] if _sp > 40 else _t) + "\u2026"
            else:
                _tooltip = ""

            item = {
                "label": item_label,
                "icon": f"ti-{m.get('icon') or 'layout-dashboard'}",
                "extension_id": ext_id,
                "href": f"/extensions/{ext_id}",
                "tooltip": _tooltip,
            }

            # Welcome pages (is_default) go at top without category
            if m.get("is_default"):
                welcome_items.append(item)
                continue

            # Determine category: DB override > manifest
            if ext_id in db_item_configs:
                cat_id = db_item_configs[ext_id].category_id
            else:
                cats = m.get("categories") or ["other"]
                cat_id = cats[0]

            # Mundus items go into their own super-category section
            if cat_id == "mundus":
                mundus_items.append(item)
                continue

            grouped.setdefault(cat_id, []).append((ext_id, item))

        # Sort items within each category: DB position > hardcoded default > alphabetical
        categories_out = []
        all_cat_ids = set(grouped.keys()) | set(category_order.keys())
        for cat_id in sorted(all_cat_ids, key=lambda c: category_order.get(c, 50)):
            if cat_id not in grouped:
                continue
            items = grouped[cat_id]
            default_order = DEFAULT_ITEM_ORDER.get(cat_id, [])

            def sort_key(entry, _cat_defaults=default_order):
                eid, itm = entry
                if eid in db_item_configs and db_item_configs[eid].position:
                    return (0, db_item_configs[eid].position, "")
                if eid in _cat_defaults:
                    return (1, _cat_defaults.index(eid), "")
                return (2, 0, itm["label"])

            items.sort(key=sort_key)
            cat_label = category_labels.get(cat_id, cat_id.replace("_", " ").title())
            categories_out.append({
                "id": cat_id,
                "label": cat_label,
                "items": [itm for _, itm in items],
            })

        # Determine default path
        default_path = "/extensions/member_dashboard"
        if welcome_items:
            default_path = welcome_items[0]["href"]

        return json.dumps({
            "success": True,
            "welcome_items": welcome_items,
            "mundus_items": mundus_items,
            "categories": categories_out,
            "default_path": default_path,
        })
    except Exception as e:
        logger.error(f"Error building sidebar: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@query
def get_menu_config() -> text:
    """Return raw menu configuration for the Menus extension admin UI.

    Response (JSON): {
        "success": true,
        "category_order": [{"category_id": "...", "label": "...", "position": N}, ...],
        "item_overrides": [{"extension_name": "...", "category_id": "...", "position": N}, ...],
        "visibility_rules": [{"extension_name": "...", "department": "...", "visible": bool}, ...]
    }
    """
    try:
        from ggg import MenuCategoryConfig, MenuDepartmentVisibility, MenuItemConfig

        category_order = [
            {"category_id": c.category_id, "label": c.label, "position": c.position}
            for c in MenuCategoryConfig.instances()
        ]
        item_overrides = [
            {"extension_name": i.extension_name, "category_id": i.category_id, "position": i.position}
            for i in MenuItemConfig.instances()
        ]
        visibility_rules = [
            {
                "extension_name": v.extension_name,
                "department": v.department.name if v.department else None,
                "visible": v.visible,
            }
            for v in MenuDepartmentVisibility.instances()
        ]

        return json.dumps({
            "success": True,
            "category_order": category_order,
            "item_overrides": item_overrides,
            "visibility_rules": visibility_rules,
            "defaults": [{"id": c[0], "label": c[1], "position": c[2]} for c in DEFAULT_CATEGORY_ORDER],
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.REALM_ADMIN)
def set_menu_category_order(args: text) -> text:
    """Save custom category ordering. Replaces all existing MenuCategoryConfig records.

    Args (JSON): {"categories": [{"category_id": "...", "label": "...", "position": N}, ...]}
    """
    try:
        from ggg import MenuCategoryConfig

        params = json.loads(args)
        categories = params.get("categories", [])

        # Clear existing
        for existing in list(MenuCategoryConfig.instances()):
            existing.delete()

        # Create new
        for cat in categories:
            MenuCategoryConfig.create(
                category_id=cat["category_id"],
                label=cat.get("label", ""),
                position=cat.get("position", 0),
            )

        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.REALM_ADMIN)
def set_menu_item_config(args: text) -> text:
    """Save custom extension placement. Creates or updates a MenuItemConfig.

    Args (JSON): {"extension_name": "...", "category_id": "...", "position": N}
    """
    try:
        from ggg import MenuItemConfig

        params = json.loads(args)
        ext_name = params["extension_name"]
        category_id = params["category_id"]
        position = params.get("position", 0)

        existing = None
        for item in MenuItemConfig.instances():
            if item.extension_name == ext_name:
                existing = item
                break

        if existing:
            existing.category_id = category_id
            existing.position = position
            existing.save()
        else:
            MenuItemConfig.create(
                extension_name=ext_name,
                category_id=category_id,
                position=position,
            )

        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.REALM_ADMIN)
def set_menu_visibility(args: text) -> text:
    """Save per-department extension visibility rule.

    Args (JSON): {"extension_name": "...", "department": "...", "visible": bool}
    """
    try:
        from ggg import Department, MenuDepartmentVisibility

        params = json.loads(args)
        ext_name = params["extension_name"]
        dept_name = params["department"]
        visible = params.get("visible", True)

        dept = Department[dept_name]
        if not dept:
            return json.dumps({"success": False, "error": f"Department '{dept_name}' not found"})

        existing = None
        for rule in MenuDepartmentVisibility.instances():
            if rule.extension_name == ext_name and rule.department and rule.department.name == dept_name:
                existing = rule
                break

        if existing:
            existing.visible = visible
            existing.save()
        else:
            MenuDepartmentVisibility.create(
                extension_name=ext_name,
                department=dept,
                visible=visible,
            )

        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@query
def get_extension_frontend_info(args: text) -> text:
    """Return file_registry coordinates for an extension's frontend assets.

    Args (JSON): {"extension_id": str}
    Response (JSON): {
        "success": bool,
        "extension_id": str,
        "version": str,
        "registry_canister_id": str,        # canister id hosting the assets
        "namespace": str,                   # "ext/<id>/<version>"
        "frontend_path": "frontend/dist/index.js"
    }

    realm_frontend uses this to dynamic-import an extension's compiled UI
    bundle from file_registry without baking the registry id into its WASM
    (Issue #168 Layer 2).
    """
    try:
        from core.runtime_extensions import get_extension_source

        params = json.loads(args) if args else {}
        ext_id = params.get("extension_id")
        if not ext_id:
            return json.dumps({"success": False, "error": "extension_id is required"})

        src = get_extension_source(ext_id)
        if not src or not src.get("registry_canister_id"):
            return json.dumps({
                "success": False,
                "error": f"No registry source recorded for extension '{ext_id}'",
            })

        version = src.get("version") or ""
        return json.dumps({
            "success": True,
            "extension_id": ext_id,
            "version": version,
            "registry_canister_id": src["registry_canister_id"],
            "namespace": f"ext/{ext_id}/{version}" if version else f"ext/{ext_id}",
            "frontend_path": "frontend/dist/index.js",
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Codex package management endpoints
# ---------------------------------------------------------------------------


@update
@require(Operations.CODEX_INSTALL)
def install_codex(args: text) -> text:
    """Install a codex package from uploaded files.

    Args (JSON): {
        "codex_id": str,
        "files": {"filename": "content", ...},
        "run_init": bool  (optional, default true)
    }

    Files should include manifest.json and *.py codex modules.
    Each .py file (except init.py) creates/updates a Codex entity.
    If run_init is true and init.py is present, it is executed after install.
    """
    try:
        params = json.loads(args)
        codex_id = params.get("codex_id")
        files = params.get("files", {})
        run_init = params.get("run_init", True)

        if not codex_id:
            return json.dumps({"success": False, "error": "codex_id is required"})
        if not files:
            return json.dumps({"success": False, "error": "files dict is required"})

        from core.runtime_codex import install_codex_package, run_codex_init

        ok = install_codex_package(codex_id, files)
        if not ok:
            return json.dumps({"success": False, "error": f"Failed to install codex package '{codex_id}'"})

        init_error = None
        if run_init:
            init_error = run_codex_init(codex_id)

        result = {"success": True, "codex_id": codex_id, "files_count": len(files)}
        if init_error:
            result["init_warning"] = init_error
        return json.dumps(result)
    except Exception as e:
        logger.error(f"install_codex error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.CODEX_UNINSTALL)
def uninstall_codex(args: text) -> text:
    """Uninstall a codex package and its Codex entities.

    Args (JSON): {"codex_id": str}
    """
    try:
        params = json.loads(args)
        codex_id = params.get("codex_id")

        if not codex_id:
            return json.dumps({"success": False, "error": "codex_id is required"})

        from core.runtime_codex import uninstall_codex_package

        ok = uninstall_codex_package(codex_id)
        if ok:
            return json.dumps({"success": True, "codex_id": codex_id})
        else:
            return json.dumps({"success": False, "error": f"Codex package '{codex_id}' not found"})
    except Exception as e:
        logger.error(f"uninstall_codex error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.CODEX_INSTALL)
def reload_codex(args: text) -> text:
    """Reload all Codex entities from a codex package's files on disk.

    Args (JSON): {"codex_id": str, "run_init": bool (optional, default false)}
    """
    try:
        params = json.loads(args)
        codex_id = params.get("codex_id")
        run_init = params.get("run_init", False)

        if not codex_id:
            return json.dumps({"success": False, "error": "codex_id is required"})

        from core.runtime_codex import reload_codex_package, run_codex_init

        ok = reload_codex_package(codex_id)
        if not ok:
            return json.dumps({"success": False, "error": f"Codex package '{codex_id}' not found"})

        init_error = None
        if run_init:
            init_error = run_codex_init(codex_id)

        result = {"success": True, "codex_id": codex_id}
        if init_error:
            result["init_warning"] = init_error
        return json.dumps(result)
    except Exception as e:
        logger.error(f"reload_codex error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@query
def list_codex_packages() -> text:
    """List all installed codex packages with their manifests."""
    try:
        from core.runtime_codex import list_installed, get_all_codex_manifests

        installed = list_installed()
        manifests = get_all_codex_manifests()
        return json.dumps({
            "success": True,
            "codex_packages": installed,
            "manifests": manifests,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Registry-based install endpoints (inter-canister pull from file registry)
# ---------------------------------------------------------------------------


@update
@require(Operations.EXTENSION_INSTALL)
def install_extension_from_registry(args: text) -> Async[text]:
    """Install an extension by pulling backend files from the file registry.
    Also copies frontend bundles to the realm's frontend asset canister
    for same-origin loading.

    Args (JSON): {
        "registry_canister_id": str,
        "ext_id": str,
        "version": str|null  (null = latest),
        "frontend_canister_id": str|null  (overrides Realm entity value)
    }
    """
    try:
        params = json.loads(args)
        registry_id = params.get("registry_canister_id")
        ext_id = params.get("ext_id")
        version = params.get("version")

        if not registry_id:
            return json.dumps({"success": False, "error": "registry_canister_id is required"})
        if not ext_id:
            return json.dumps({"success": False, "error": "ext_id is required"})

        frontend_id = params.get("frontend_canister_id") or _get_frontend_canister_id()

        from api.file_registry import install_extension_from_registry as _install

        result = yield from _install(registry_id, ext_id, version, frontend_canister_id=frontend_id)

        # After a canister reinstall, init_() runs before extensions are
        # installed so extension initialize() hooks never fire.  Call it
        # here so schedules/timers created by the hook get registered in
        # this @update context (IC timers require init/post_upgrade/update).
        try:
            result_data = json.loads(result) if isinstance(result, str) else result
            if result_data.get("success"):
                try:
                    init_result = api.extensions.extension_sync_call(ext_id, "initialize", "{}")
                    logger.info(f"Extension {ext_id} post-install initialize: {init_result}")
                except Exception as init_err:
                    logger.info(f"Extension {ext_id} has no initialize hook (ok): {init_err}")
        except Exception as e:
            logger.warning(f"Extension {ext_id} post-install init check failed: {e}")

        return result
    except Exception as e:
        logger.error(f"install_extension_from_registry error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.CODEX_INSTALL)
def install_codex_from_registry(args: text) -> Async[text]:
    """Install a codex package by pulling files from the file registry.

    Args (JSON): {
        "registry_canister_id": str,
        "codex_id": str,           ("realm_type/codex_id" e.g. "syntropia/membership")
        "version": str|null,       (null = latest)
        "run_init": bool           (optional, default true)
    }
    """
    try:
        params = json.loads(args)
        registry_id = params.get("registry_canister_id")
        codex_id = params.get("codex_id")
        version = params.get("version")
        run_init = params.get("run_init", True)

        if not registry_id:
            return json.dumps({"success": False, "error": "registry_canister_id is required"})
        if not codex_id:
            return json.dumps({"success": False, "error": "codex_id is required"})

        from api.file_registry import install_codex_from_registry as _install

        result = yield from _install(registry_id, codex_id, version, run_init)
        return result
    except Exception as e:
        logger.error(f"install_codex_from_registry error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.REALM_ADMIN)
def install_branding_from_registry(args: text) -> Async[text]:
    """Pull per-realm branding images (logo, background) from the file registry
    and upload them to the realm's frontend asset canister so they are served
    same-origin (e.g. /custom/logo.png) after a reinstall.

    Args (JSON): {
        "registry_canister_id": str,
        "namespace": str,                       (default "branding")
        "files": { "<asset_key>": "<registry_path>" },
            e.g. {"/custom/logo.png": "dominion/logo.png",
                  "/custom/background.png": "dominion/background.png"}
        "frontend_canister_id": str|null        (overrides Realm entity value)
    }
    """
    try:
        params = json.loads(args)
        registry_id = params.get("registry_canister_id")
        namespace = params.get("namespace") or "branding"
        files_map = params.get("files") or {}
        frontend_id = params.get("frontend_canister_id") or _get_frontend_canister_id()

        if not registry_id:
            return json.dumps({"success": False, "error": "registry_canister_id is required"})
        if not files_map:
            return json.dumps({"success": False, "error": "files is required"})

        from api.file_registry import install_branding_from_registry as _install

        result = yield from _install(registry_id, namespace, files_map, frontend_id)
        return result
    except Exception as e:
        logger.error(f"install_branding_from_registry error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})


@update
@require(Operations.REALM_ADMIN)
def register_realm_from_registry(args: text) -> Async[text]:
    """Register this realm with the realm registry from a single JSON arg.

    A `(text) -> (text)` wrapper around `api.registry.register_realm` so a Casals
    arrangement step can drive registration declaratively (arrangement steps are
    always single-text-in / text-out). The registry keys the realm on
    `ic.caller()` (== this backend's canister id), so re-applying upserts the
    same record (idempotent).

    Args (JSON): {
        "registry_canister_id": str,            (required)
        "realm_name": str,                      (required)
        "frontend_url": str,                    (optional)
        "canister_ids": {                       (optional)
            "frontend_canister_id": str,
            "token_canister_id": str,
            "nft_canister_id": str
        }
    }
    """
    try:
        params = json.loads(args)
        registry_id = params.get("registry_canister_id")
        realm_name = params.get("realm_name")
        frontend_url = params.get("frontend_url") or ""
        canister_ids = params.get("canister_ids") or {}

        if not registry_id:
            return json.dumps({"success": False, "error": "registry_canister_id is required"})
        if not realm_name:
            return json.dumps({"success": False, "error": "realm_name is required"})

        # Default the frontend id to this realm's own asset canister so the
        # registry can construct the logo/frontend URL client-side.
        if not canister_ids.get("frontend_canister_id"):
            fid = _get_frontend_canister_id()
            if fid:
                canister_ids["frontend_canister_id"] = fid

        result = yield from register_realm(
            registry_id, realm_name, frontend_url, "", canister_ids
        )
        return json.dumps(result)
    except Exception as e:
        logger.error(f"register_realm_from_registry error: {e}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})
