import traceback
from datetime import datetime
from typing import Dict, List, Optional

import api
from ggg.base import initialize, universe
from kybra import (Async, CallResult, Func, Opt, Principal, Query, Record,
                   Tuple, Variant, Vec, blob, heartbeat, ic, init, match, nat,
                   nat16, nat64, query, update, void)


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
    callback: "Callback"
    token: "Token"


Callback = Func(Query[["Token"], "StreamingCallbackHttpResponse"])


class StreamingCallbackHttpResponse(Record):
    body: blob
    token: Opt["Token"]


class Token(Record):
    key: str




@init
def init_() -> void:
    pass

@query
def http_request(req: HttpRequest) -> HttpResponse:
    url = req["url"]
    if url == "/api/v1/get_universe":
        return http_request_core(universe())
    elif url == "/api/v1/tokens":
        return http_request_core(get_token_list())
    elif url.startswith("/api/v1/tokens/"):
        token_id = url.split("/")[-1]
        data = get_token_data(token_id)
        if data is None:
            return {
                "status_code": 404,
                "headers": [],
                "body": bytes(json_dumps({"error": "Token not found"}), "ascii"),
                "streaming_strategy": None,
                "upgrade": False,
            }
        return http_request_core(data)
    return {
        "status_code": 404,
        "headers": [],
        "body": bytes("Not found", "ascii"),
        "streaming_strategy": None,
        "upgrade": False,
    }


def http_request_core(data):
    try:
        d = json_dumps(data)
        return {
            "status_code": 200,
            "headers": [],
            "body": bytes(d + "\n", "ascii"),
            "streaming_strategy": None,
            "upgrade": False,
        }
    except Exception as e:
        return {
            "status_code": 500,
            "headers": [],
            "body": bytes(traceback.format_exc(), "ascii"),
            "streaming_strategy": None,
            "upgrade": False,
        }

