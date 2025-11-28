from kybra import Record, ic, text

"""

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "test_bench";
    function_name = "get_data";
    args = opt vec {
      variant { String = "hello world" }
    };
    kwargs = null
  }
)'

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "test_bench";
    function_name = "get_data";
    args = null;
    kwargs = opt vec {
      record { key = "some_param"; value = variant { Boolean = false } }
    }
  }
)'
"""


class TestBenchResponse(Record):
    data: text


def get_data(args: str) -> TestBenchResponse:
    """Get test data from this extension.

    The core module will handle the async wrapping for us.
    """
    ic.print("get_data starting")
    ic.print(f"Parameter type: {type(args)}, Value: {args}")

    # Simple, non-async function that returns a regular value
    # The core/extensions.py module will handle wrapping this in an async function
    return TestBenchResponse(data=f"some data {args}")
