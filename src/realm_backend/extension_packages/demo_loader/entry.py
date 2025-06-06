import traceback

from kybra import Record
from kybra_simple_logging import get_logger

logger = get_logger("demo_loader.entry")

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

    try:
        logger.info("Loading demo data")

        from .demo1 import run

        return run()

    except Exception as e:
        logger.error(f"Error loading demo data: {e}\n{traceback.format_exc()}")
        return str(e)
