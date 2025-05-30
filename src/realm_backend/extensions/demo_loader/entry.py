from kybra import Async, ic, Record
from kybra_simple_db import Entity, String, TimestampedMixin
from kybra_simple_logging import get_logger

from ggg.user import User

logger = get_logger("entity.user")

"""

dfx canister call realm_backend extension_async_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = null;
    kwargs = null
  }
)'
"""

class ResponseDemoLoader(Record):
    data: str

def load(args: str):
    """Get test data from this extension.

    The core module will handle the async wrapping for us.
    """
    logger.info("load_demo_data called with args: {args}")

    user = User(
        _id="user_22",
        metadata="{}"
    )

    logger.info(f"User created: {user.to_dict()}")
    
    return "OK111"

