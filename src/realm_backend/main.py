import json
import traceback

import api

# from api.extensions import list_extensions
from api.status import get_status
from api.user import user_get, user_register
from core.candid_types_realm import (
    ExtensionCallArgs,
    ExtensionCallResponse,
    RealmResponse,
    RealmResponseData,
    StatusRecord,
    UserGetRecord,
    UserRegisterRecord,
)
from kybra import (
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
    query,
    update,
    void,
    CallResult,
    text
)
from kybra_simple_db import Database
from kybra_simple_logging import get_logger

storage = StableBTreeMap[str, str](
    memory_id=1, max_key_size=100000, max_value_size=1000
)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("main")


class HttpRequest(Record):
    method: str
    url: str
    headers: Vec["Header"]
    body: blob


class HttpResponse(Record):
    status_code: nat
    headers: Vec["Header"]
    body: blob
    streaming_strategy: Opt["StreamingStrategy"]
    upgrade: Opt[bool]


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
def register_user(principal: Principal) -> RealmResponse:
    try:
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UserRegister=UserRegisterRecord(
                    principal=Principal.from_str(
                        user_register(principal.to_str())["principal"]
                    )
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_user(principal: Principal) -> RealmResponse:
    try:
        user_data = user_get(principal.to_str())
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UserGet=UserGetRecord(
                    principal=Principal.from_str(user_data["principal"])
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@init
def init_() -> void:
    logger.info("Realm canister initialized")


@update
def extension_call(args: ExtensionCallArgs) -> Async[ExtensionCallResponse]:
    try:
        logger.info(
            f"Calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        # Get the async function through the call chain
        extension_coroutine = api.extensions.call_extension(
            args["extension_name"], args["function_name"], args["args"]
        )
        
        # In Kybra for IC, we need to yield the coroutine to get the actual result
        extension_result = yield extension_coroutine
        
        logger.info(f"Coroutine yielded: {extension_coroutine}")
        logger.info(f"Result type: {type(extension_result)}")
        
        logger.info(f"Got extension result: {extension_result}, type: {type(extension_result)}")
        
        # For test_bench extension, handle the TestBenchResponse object
        if args["extension_name"] == "test_bench" and args["function_name"] == "get_data":
            # According to Kybra IC pattern, use dictionary access for Record fields
            # rather than attribute access
            if isinstance(extension_result, dict) and "data" in extension_result:
                return ExtensionCallResponse(success=True, response=str(extension_result["data"]))
            elif hasattr(extension_result, "data"):
                return ExtensionCallResponse(success=True, response=str(extension_result.data))
            else:
                # Fallback to string representation
                return ExtensionCallResponse(success=True, response=str(extension_result))
        
        # Generic response for other extensions
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
