import json
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import core.candid_types_realm as candid
from api.status import get_status
from api.user import user_get, user_register
from kybra import (Async, CallResult, Func, Opt, Principal, Query, Record,
                   StableBTreeMap, Tuple, Variant, Vec, blob, heartbeat, ic,
                   init, match, nat, nat16, nat64, query, update, void)
from kybra_simple_db import Database
from kybra_simple_logging import get_logger

storage = StableBTreeMap[str, str](
    memory_id=1, max_key_size=100000, max_value_size=1000
)
Database.init(db_storage=storage)

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
def status() -> candid.Response:
    """
    Get the current status of the realm canister

    Returns:
        Status: Current status information including version, online status, and entity counts
    """
    logger.info("Status query executed")
    return candid.Response(success=True, data=candid.StatusRecord(**get_status()))


@update
def register_user(principal: Principal) -> candid.Response:
    return candid.Response(
        success=True, data=candid.UserRegisterRecord(**user_register(principal))
    )


@query
def get_user(principal: Principal) -> candid.Response:
    return candid.Response(
        success=True, data=candid.UserRegisterRecord(**user_get(principal))
    )


@init
def init_() -> void:
    """Initialize the canister with a default realm"""
    # Initialize the API with a default realm name
    # In production, this would be configured via parameters
    # logger.info("Initializing realm canister")
    # api.initialize("DefaultRealm", str(ic.caller()))
    pass


def http_request_core(data):
    try:
        d = json.dumps(data)
        return {
            "status_code": 200,
            "headers": [],
            "body": bytes(d + "\n", "ascii"),
            "streaming_strategy": None,
            "upgrade": False,
        }
    except Exception:
        return {
            "status_code": 500,
            "headers": [],
            "body": bytes(traceback.format_exc(), "ascii"),
            "streaming_strategy": None,
            "upgrade": False,
        }


@query
def http_request(req: HttpRequest) -> HttpResponse:
    """Handle HTTP requests to the canister. Only for unauthenticated read operations."""

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

    return not_found
