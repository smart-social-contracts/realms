import json
import traceback
from typing import Optional, Tuple

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
    match,
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


@query
def greet(name: str) -> str:
    return f"Hello, {name}!"
