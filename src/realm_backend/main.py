import base64
import importlib
import json
import sys
import traceback

import api
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
from api.crypto import group_remove_member as crypto_group_remove
from api.crypto import list_envelopes as crypto_list_envelopes
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
from api.nft import get_nft_canister_id, mint_land_nft
from api.registry import get_registry_info, register_realm
from api.status import get_status
from api.user import (
    user_get,
    user_register,
    user_update_private_data,
    user_update_public_profile,
)
from api.vetkeys import derive_vetkey, get_vetkey_public_key
from api.zones import get_zone_aggregation
from core.access import _check_access, require, set_controller
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
    realm_name: text
    realm_logo: text
    realm_description: text
    realm_welcome_image: text
    realm_welcome_message: text
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
            # Include the capital (self) as quarter 0
            # Compute population dynamically from User.home_quarter
            from ggg import User
            own_id = ic.id().to_str()
            all_users = list(User.instances())
            quarter_entities = list(Quarter.instances())
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
def join_realm(profile: str, preferred_quarter: text) -> RealmResponse:
    try:
        user = user_register(ic.caller().to_str(), profile)
        profiles = Vec[text]()
        if "profiles" in user and user["profiles"]:
            for p in user["profiles"]:
                profiles.append(p)

        # Quarter assignment (no-op for single-quarter realms)
        assigned_quarter_canister_id = ""
        from ggg import Quarter, Realm, User

        realm = Realm.load("1")
        quarters = list(Quarter.instances()) if realm else []
        if realm and quarters:
            assigned_quarter_canister_id = _assign_quarter(
                ic.caller().to_str(), realm, quarters, preferred_quarter
            )
            # Persist the assignment on the User entity
            u = User[ic.caller().to_str()]
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


@update
@require(Operations.REALM_ADMIN)
def set_canister_config(
    frontend_canister_id: Opt[text],
    token_canister_id: Opt[text],
    nft_canister_id: Opt[text],
) -> RealmResponse:
    """
    Set canister IDs for this realm (admin only).
    Called post-deployment to enable canister discovery via status().

    Args:
        frontend_canister_id: The realm_frontend canister ID
        token_canister_id: Optional token_backend canister ID
        nft_canister_id: Optional nft_backend canister ID
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

        realm.save()
        logger.info(
            f"Updated canister config: frontend={frontend_canister_id}, token={token_canister_id}, nft={nft_canister_id}"
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

        quarter = Quarter(
            name=quarter_name,
            canister_id=quarter_canister_id,
        )
        quarter.federation = realm

        logger.info(
            f"Registered quarter '{quarter_name}' (canister: {quarter_canister_id})"
        )

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                message=f"Quarter '{quarter_name}' registered with ID {quarter._id}"
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
        realm.save()

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
        realm.save()

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
        realm.save()

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


# ---------------------------------------------------------------------------
# Crypto envelope & group endpoints
# ---------------------------------------------------------------------------


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
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"Realm\", \"_id\": \"1\", \"name\": \"Generated Demo Realm\", \"description\": \"Generated demo realm with 51 citizens and 5 organizations\", \"id\": \"0\", \"created_at\": \"2025-09-10T13:23:57.099332\", \"status\": \"active\", \"governance_type\": \"democratic\", \"population\": 51, \"organization_count\": 5, \"settings\": {\"voting_period_days\": 7, \"proposal_threshold\": 0.1, \"quorum_percentage\": 0.3, \"tax_rate\": 0.15, \"ubi_amount\": 1000}, \"relations\": {\"treasury\": [{\"_type\": \"Treasury\", \"_id\": \"2\"}]}}"
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
    Refresh payment status for an invoice by querying token balances
    on the invoice's subaccount via basilisk OS Wallet.

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
        realm_description = "A realm for digital governance and coordination"
        realm_logo = ""
        realm_welcome_image = ""
        realm_welcome_message = ""

        import json
        import os

        manifest_json_str = "{}"  # default if no manifest.json found
        try:
            # Look for manifest.json in common locations
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
                    realm_description = manifest.get("description", realm_description)
                    realm_logo = manifest.get("logo", "")
                    realm_welcome_image = manifest.get("welcome_image", "")
                    realm_welcome_message = manifest.get("welcome_message", "")
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
            description=realm_description,
            logo=realm_logo,
            welcome_image=realm_welcome_image,
            welcome_message=realm_welcome_message,
            accounting_currency=acct_currency_config.get("symbol", "ckBTC"),
            accounting_currency_decimals=acct_currency_config.get("decimals", 8),
            principal_id="",
            manifest_data=manifest_json_str,
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
        logger.info("✅ All foundational objects created successfully")

    except Exception as e:
        logger.error(
            f"❌ Error creating foundational objects: {str(e)}\n{traceback.format_exc()}"
        )
        raise


def _register_wallet_transfer_hook():
    """Register the GGG permission check as the Basilisk OS Wallet pre-transfer hook."""
    try:
        from basilisk.os.wallet import Wallet
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

    # Register basilisk OS crypto entities
    from basilisk.os.crypto import CryptoGroup, CryptoGroupMember, KeyEnvelope

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

                        # Import implementation
                        parts = impl_path.split(".")
                        module_path = (
                            f"extension_packages.{extension_id}.{'.'.join(parts[:-1])}"
                        )
                        func_name = parts[-1]

                        impl_module = __import__(module_path, fromlist=[func_name])
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
                extension_module = __import__(
                    f"extension_packages.{extension_id}.entry",
                    fromlist=["register_entities"],
                )

                if hasattr(extension_module, "register_entities"):
                    extension_module.register_entities()
                    status["has_entities"] = True
            except ImportError:
                # No entry module - that's fine
                pass
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
    # created from execute_code_shell do not survive IC call boundaries.
    # After an upgrade, any in-progress tasks lost their timers, so reset
    # non-completed tasks back to pending before scheduling.
    try:
        # Eagerly load related entities so ManyToOne descriptors resolve and
        # populate bidirectional _relations on Task (steps, schedules) before
        # any property modifications trigger _save() which would otherwise
        # serialize entities with empty _relations, losing relationship data.
        list(Task.instances())
        list(Call.instances())
        list(TaskStep.instances())
        list(TaskSchedule.instances())

        manager = TaskManager()
        for t in Task.instances():
            if t.status and t.status != "completed":
                t.status = "pending"
                t.step_to_execute = 0
                for step in t.steps:
                    step.status = "pending"
                    step.timer_id = None
            manager.add_task(t)
        manager.run()
        logger.info(f"✅ TaskManager started with {len(manager.tasks)} task(s)")
    except Exception as e:
        logger.error(
            f"❌ Error starting TaskManager: {str(e)}\n{traceback.format_exc()}"
        )


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
    execute_code_shell do NOT survive IC call boundaries.
    """
    try:
        # Eagerly load related entities so ManyToOne descriptors resolve and
        # populate bidirectional _relations on Task (steps, schedules) before
        # any property modifications trigger _save().
        list(Task.instances())
        list(Call.instances())
        list(TaskStep.instances())
        list(TaskSchedule.instances())

        manager = TaskManager()
        count = 0
        for t in Task.instances():
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
def extension_call(args: ExtensionCallArgs) -> ExtensionCallResponse:
    """Query version of extension call for read-only operations like get_entity_types."""
    try:
        logger.debug(
            f"Query calling extension '{args['extension_name']}' function '{args['function_name']}' with args {args['args']}"
        )

        extension_result = api.extensions.extension_sync_call(
            args["extension_name"], args["function_name"], args["args"]
        )

        logger.debug(
            f"Got extension result from {args['extension_name']} function {args['function_name']}: {extension_result}"
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
def extension_sync_call(args: ExtensionCallArgs) -> ExtensionCallResponse:
    try:
        caller = ic.caller().to_str()
        if not _check_access(caller, Operations.EXTENSION_SYNC_CALL):
            return ExtensionCallResponse(
                success=False,
                response=f"Access denied: user {caller} lacks permission '{Operations.EXTENSION_SYNC_CALL}'",
            )
        logger.debug(
            f"Sync calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        extension_result = api.extensions.extension_sync_call(
            args["extension_name"], args["function_name"], args["args"]
        )

        logger.debug(
            f"Got extension result from {args['extension_name']} function {args['function_name']}: {extension_result}, type: {type(extension_result)}"
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
def extension_async_call(args: ExtensionCallArgs) -> Async[ExtensionCallResponse]:
    try:
        caller = ic.caller().to_str()
        if not _check_access(caller, Operations.EXTENSION_ASYNC_CALL):
            return ExtensionCallResponse(
                success=False,
                response=f"Access denied: user {caller} lacks permission '{Operations.EXTENSION_ASYNC_CALL}'",
            )
        logger.debug(
            f"Async calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        extension_coroutine = api.extensions.extension_async_call(
            args["extension_name"], args["function_name"], args["args"]
        )
        extension_result = yield extension_coroutine

        logger.debug(
            f"Got extension result from {args['extension_name']} function {args['function_name']}: {extension_result}, type: {type(extension_result)}"
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
def execute_code_shell(code: str) -> str:
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


# Removed endpoints (use execute_code_shell + basilisk shell commands instead):
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

            # Create step
            step = TaskStep(call=call, run_next_after=run_next_after)
            task_steps.append(step)

            logger.info(
                f"Created step {idx}: codex={codex_name}, "
                f"run_next_after={run_next_after}s"
            )

        # Create task with multiple steps
        task = Task(name=name, steps=task_steps)

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
    logo_url: text = "",
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
        logo_url: Logo URL (optional)
        canister_ids_json: JSON string with frontend_canister_id, token_canister_id, nft_canister_id

    Returns:
        JSON string with success status and message
    """
    try:
        # canister_ids_json is pipe-delimited: frontend_id|token_id|nft_id
        # (JSON triggers basilisk Candid encoder bug)
        canister_ids = {}
        if canister_ids_json and "|" in canister_ids_json:
            parts = canister_ids_json.split("|")
            canister_ids = {
                "frontend_canister_id": parts[0] if len(parts) > 0 else "",
                "token_canister_id": parts[1] if len(parts) > 1 else "",
                "nft_canister_id": parts[2] if len(parts) > 2 else "",
            }

        result = yield register_realm(
            registry_canister_id, realm_name, frontend_url, logo_url, "", canister_ids
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
@require(Operations.REALM_CONFIGURE)
def update_realm_config(config_json: str) -> str:
    """
    Update the realm configuration (name, description, logo, welcome_image, welcome_message).
    This should be called after deployment with the manifest.json data.

    Args:
        config_json: JSON string containing realm configuration fields
    """
    logger.info("🔧 update_realm_config() called")
    try:
        import json

        from ggg import Realm

        config = json.loads(config_json)
        logger.info(f"📋 Config received: {list(config.keys())}")

        # Get the first realm
        realms = list(Realm.instances())
        if not realms:
            logger.error("❌ No realm found")
            return json.dumps({"success": False, "error": "No realm found"})

        realm = realms[0]
        updated_fields = []

        if "name" in config and config["name"]:
            realm.name = config["name"]
            updated_fields.append(f"name={config['name']}")

        if "description" in config and config["description"]:
            realm.description = config["description"]
            updated_fields.append(f"description={config['description'][:50]}...")

        if "logo" in config:
            realm.logo = config["logo"] or ""
            updated_fields.append(f"logo={config['logo']}")

        if "welcome_image" in config:
            realm.welcome_image = config["welcome_image"] or ""
            updated_fields.append(f"welcome_image={config['welcome_image']}")

        if "welcome_message" in config:
            realm.welcome_message = config["welcome_message"] or ""
            updated_fields.append(
                f"welcome_message={config['welcome_message'][:50] if config['welcome_message'] else ''}..."
            )

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
