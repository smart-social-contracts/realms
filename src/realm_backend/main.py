import json
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.extensions import list_extensions
from api.status import get_status
from api.user import user_get, user_register
from core.candid_types_realm import (RealmResponse, RealmResponseData,
                                     StatusRecord, UserGetRecord,
                                     UserRegisterRecord)
from kybra import (Async, CallResult, Func, Opt, Principal, Query, Record,
                   StableBTreeMap, Tuple, Variant, Vec, blob, heartbeat, ic,
                   init, match, nat, nat16, nat64, query, update, void)
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
    status_code: nat16
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

    # Initialize extensions
    try:
        # Only import the init_extensions function here to avoid circular imports
        # during Kybra's compile-time type checking
        from extensions import init_extensions

        # Get realm data to pass to extensions
        realm_data = {
            "vault_principal_id": ic.id().to_str()  # For demo purposes, using self as vault
            # In real deployment, you'd get this from a configuration or parameter
        }

        # Initialize all extensions
        init_extensions(realm_data)
        logger.info("Extensions initialized successfully")
    except Exception as e:
        logger.error(
            f"Failed to initialize extensions: {str(e)}\n{traceback.format_exc()}"
        )


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

            if url_path[2] == "extensions":
                if len(url_path) < 4:
                    # List all extensions
                    extensions_list = list_extensions()
                    return http_request_core({"extensions": extensions_list})

                # For specific extension endpoints, we'll implement them
                # after fixing the core extension system

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
