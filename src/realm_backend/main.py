import json
import traceback

import api
from api.ggg_entities import (
    list_codexes,
    list_disputes,
    list_instruments,
    list_licenses,
    list_mandates,
    list_organizations,
    list_proposals,
    list_realms,
    list_tasks,
    list_trades,
    list_transfers,
    list_users,
    list_votes,
)

# from api.extensions import list_extensions
from api.status import get_status
from api.user import user_get, user_register
from core.candid_types_realm import (
    CodexesListRecord,
    DisputesListRecord,
    ExtensionCallArgs,
    ExtensionCallResponse,
    InstrumentsListRecord,
    LicensesListRecord,
    MandatesListRecord,
    OrganizationsListRecord,
    PaginationInfo,
    ProposalsListRecord,
    RealmResponse,
    RealmResponseData,
    RealmsListRecord,
    StatusRecord,
    TasksListRecord,
    TradesListRecord,
    TransfersListRecord,
    UserGetRecord,
    UsersListRecord,
    VotesListRecord,
)
from kybra import (
    Async,
    CallResult,
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
    post_upgrade,
    query,
    text,
    update,
    void,
)
from kybra_simple_db import Database
from kybra_simple_logging import get_logger

storage = StableBTreeMap[str, str](memory_id=1, max_key_size=100, max_value_size=2000)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("main")


class HttpRequest(Record):
    method: str
    url: str
    headers: Vec["Header"]
    body: blob


from kybra.canisters.management import HttpResponse, HttpTransformArgs

Header = Tuple[str, str]


class StreamingStrategy(Variant):
    Callback: "CallbackStrategy"


class CallbackStrategy(Record):
    callback: "Callback"  # type: ignore
    token: "Token"


Callback = Func(Query[["Token"], "StreamingCallbackHttpResponse"])


class StreamingCallbackHttpResponse(Record):
    body: blob
    token: Opt["Token"]


class Token(Record):
    key: str


@query
def status() -> RealmResponse:
    try:
        logger.info("Status query executed")
        return RealmResponse(
            success=True, data=RealmResponseData(Status=StatusRecord(**get_status()))
        )
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@update
def join_realm(profile: str) -> RealmResponse:
    try:
        user = user_register(ic.caller().to_str(), profile)
        profiles = Vec[text]()
        for p in user["profiles"]:
            profiles.append(p)

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UserGet=UserGetRecord(
                    principal=Principal.from_str(user["principal"]),
                    profiles=profiles,
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_my_principal() -> text:
    return ic.caller().to_str()


@query
def get_my_user_status() -> RealmResponse:
    try:
        user = user_get(ic.caller().to_str())
        logger.info(f"User: {user}")
        profiles = Vec[text]()
        for p in user["profiles"]:
            profiles.append(p)
        logger.info(f"Profiles: {profiles}")
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UserGet=UserGetRecord(
                    principal=Principal.from_str(user["principal"]),
                    profiles=profiles,
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


# New GGG API endpoints


def _generic_paginated_list(
    entity_name: str,
    list_function,
    page_num: nat,
    page_size: nat,
    record_class,
    data_key: str,
) -> RealmResponse:
    try:
        logger.info(
            f"Listing {entity_name.lower()} for page {page_num} with page size {page_size}"
        )
        result = list_function(page_num=page_num, page_size=page_size)
        items = result["items"]
        items_json = [json.dumps(item.to_dict()) for item in items]
        pagination = PaginationInfo(
            page_num=result["page_num"],
            page_size=result["page_size"],
            total_items_count=result["total_items_count"],
            total_pages=result["total_pages"],
        )

        record_kwargs = {data_key: items_json, "pagination": pagination}
        response_data_kwargs = {f"{entity_name}List": record_class(**record_kwargs)}

        return RealmResponse(
            success=True, data=RealmResponseData(**response_data_kwargs)
        )
    except Exception as e:
        logger.error(
            f"Error listing {entity_name.lower()}: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_users(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Users", list_users, page_num, page_size, UsersListRecord, "users"
    )


@query
def get_mandates(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Mandates", list_mandates, page_num, page_size, MandatesListRecord, "mandates"
    )


@query
def get_tasks(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Tasks", list_tasks, page_num, page_size, TasksListRecord, "tasks"
    )


@query
def get_transfers(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Transfers",
        list_transfers,
        page_num,
        page_size,
        TransfersListRecord,
        "transfers",
    )


@query
def get_instruments(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Instruments",
        list_instruments,
        page_num,
        page_size,
        InstrumentsListRecord,
        "instruments",
    )


@query
def get_codexes(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Codexes", list_codexes, page_num, page_size, CodexesListRecord, "codexes"
    )


@query
def get_organizations(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Organizations",
        list_organizations,
        page_num,
        page_size,
        OrganizationsListRecord,
        "organizations",
    )


@query
def get_disputes(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Disputes", list_disputes, page_num, page_size, DisputesListRecord, "disputes"
    )


@query
def get_licenses(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Licenses", list_licenses, page_num, page_size, LicensesListRecord, "licenses"
    )


@query
def get_realms(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Realms", list_realms, page_num, page_size, RealmsListRecord, "realms"
    )


@query
def get_trades(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Trades", list_trades, page_num, page_size, TradesListRecord, "trades"
    )


@query
def get_proposals(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Proposals",
        list_proposals,
        page_num,
        page_size,
        ProposalsListRecord,
        "proposals",
    )


@query
def get_votes(page_num: nat, page_size: nat) -> RealmResponse:
    return _generic_paginated_list(
        "Votes", list_votes, page_num, page_size, VotesListRecord, "votes"
    )


@update
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


@init
def init_() -> void:
    logger.info("Initializing Realm canister")
    initialize()
    logger.info("Realm canister initialized")


@post_upgrade
def post_upgrade_() -> void:
    logger.info("Post-upgrade initializing Realm canister")
    initialize()
    logger.info("Realm canister initialized")


@update
def extension_sync_call(args: ExtensionCallArgs) -> ExtensionCallResponse:
    try:
        logger.info(
            f"Sync calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        extension_result = api.extensions.extension_sync_call(
            args["extension_name"], args["function_name"], args["args"]
        )

        logger.info(
            f"Got extension result from {args['extension_name']} function {args['function_name']}: {extension_result}, type: {type(extension_result)}"
        )

        return ExtensionCallResponse(success=True, response=str(extension_result))

    except Exception as e:
        logger.error(f"Error calling extension: {str(e)}\n{traceback.format_exc()}")
        return ExtensionCallResponse(success=False, response=str(e))


@update
def extension_async_call(args: ExtensionCallArgs) -> Async[ExtensionCallResponse]:
    try:
        logger.info(
            f"Async calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        extension_coroutine = api.extensions.extension_async_call(
            args["extension_name"], args["function_name"], args["args"]
        )
        extension_result = yield extension_coroutine

        logger.info(
            f"Got extension result from {args['extension_name']} function {args['function_name']}: {extension_result}, type: {type(extension_result)}"
        )

        return ExtensionCallResponse(success=True, response=str(extension_result))

    except Exception as e:
        logger.error(f"Error calling extension: {str(e)}\n{traceback.format_exc()}")
        return ExtensionCallResponse(success=False, response=str(e))


def http_request_core(data):
    d = json.dumps(data)
    return {
        "status_code": 200,
        "headers": [],
        "body": bytes(d + "\n", "ascii"),
        "streaming_strategy": None,
        "upgrade": False,
    }


@query
def transform_response(args: HttpTransformArgs) -> HttpResponse:
    """Transform function for HTTP responses from extensions"""
    logger.info("🔄 Transforming HTTP response")
    http_response = args["response"]
    logger.info(f"📊 Original response status: {http_response['status']}")
    logger.info(f"📄 Response body size: {len(http_response['body'])} bytes")
    logger.info("🧹 Clearing response headers for security")
    http_response["headers"] = []
    return http_response


@query
def http_request(req: HttpRequest) -> HttpResponse:
    """Handle HTTP requests to the canister. Only for unauthenticated read operations."""

    try:
        method = req["method"]
        url = req["url"]

        logger.info(f"HTTP {method} request to {url}")

        not_found = HttpResponse(
            status_code=404,
            headers=[],
            body=bytes("Not found", "ascii"),
            streaming_strategy=None,
            upgrade=False,
        )

        if method == "GET":
            url_path = url.split("/")

            if url_path[0] != "api":
                return not_found

            if url_path[1] != "v1":
                return not_found

            if url_path[2] == "status":
                return http_request_core(get_status())

            # if url_path[2] == "extensions":
            #     if len(url_path) < 4:
            #         # List all extensions
            #         extensions_list = list_extensions()
            #         return http_request_core({"extensions": extensions_list})

            # Note: We no longer need to handle extension-specific HTTP endpoints here
            # as we have proper canister methods now

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


@update
def execute_code(code: str) -> str:
    """Executes Python code and returns the output.

    This is the core function needed for the Kybra Simple Shell to work.
    It captures stdout, stderr, and return values from the executed code.
    """
    import io
    import sys
    import traceback

    stdout = io.StringIO()
    stderr = io.StringIO()
    sys.stdout = stdout
    sys.stderr = stderr

    try:
        # Try to evaluate as an expression
        result = eval(code, globals())
        if result is not None:
            ic.print(repr(result))
    except SyntaxError:
        try:
            # If it's not an expression, execute it as a statement
            # Use the built-in exec function but with a different name to avoid conflict
            exec_builtin = exec
            exec_builtin(code, globals())
        except Exception:
            traceback.print_exc()
    except Exception:
        traceback.print_exc()

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    return stdout.getvalue() + stderr.getvalue()
