import json
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.status import get_status
from core.candid_types_realm import Status
from kybra import (Async, CallResult, Func, Opt, Principal, Query, Record,
                   Tuple, Variant, Vec, blob, heartbeat, ic, init, match, nat,
                   nat16, nat64, query, update, void)
from kybra_simple_logging import get_logger

# Initialize logger
logger = get_logger("canister_main")


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
def status() -> Status:
    """
    Get the current status of the realm canister

    Returns:
        Status: Current status information including version, online status, and entity counts
    """
    logger.info("Status query executed")
    return Status(**get_status())


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
    """Handle HTTP requests to the canister"""
    method = req["method"]
    url = req["url"]

    logger.info(f"HTTP {method} request to {url}")

    if method == "GET":
        # Status endpoint
        if url == "/api/v1/status":
            return http_request_core(get_status())
        # Other endpoints can be added here

    # Not found
    return HttpResponse(
        status_code=404,
        headers=[],
        body=bytes("Not found", "ascii"),
        streaming_strategy=None,
        upgrade=False,
    )
