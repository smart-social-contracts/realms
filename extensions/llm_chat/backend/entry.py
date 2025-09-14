import json
import traceback

from kybra import Opt, Principal, Record, Vec, blob, ic, nat64, text


class LLMChatResponse(Record):
    response: text


# Container for relevant realm data to be sent to the LLM.
# This provides context about the current state of the realm.
class RealmData(Record):
    json: text
    principal_id: text
    timestamp: nat64


def get_config() -> LLMChatResponse:
    """Get configuration for the AI assistance extension.

    Returns:
        LLMChatResponse: A simple acknowledgment
    """
    return LLMChatResponse(response="AI assistance extension is ready")


def get_realm_data(args) -> RealmData:
    """Collect relevant data from the realm for the LLM to use.

        This function aggregates various pieces of information from the realm
        that might be useful context for the LLM when answering user queries.
        The remote LLM service can call this endpoint to fetch the current state
        of the realm to provide more contextually aware responses.

        Returns:
            RealmData: A record containing structured data from the realm

        Parse output of this command to get the realm data:
        '''
    dfx canister call realm_backend extension_sync_call '(
      record {
        extension_name = "llm_chat";
        function_name = "get_realm_data";
        args = "none";
      }
    )' --output=json | jq -r '.response' | python3 -c "
    import sys, json, ast
    response = ast.literal_eval(sys.stdin.read())
    print(json.dumps(json.loads(response['json']), indent=2))
    "
        '''
    """
    ic.print("Collecting realm data for LLM")

    # Access the current context
    context = ic.caller()
    principal_id = str(context)

    # Get the current timestamp
    current_time = ic.time()

    # Initialize default empty data
    users_data = "[]"
    mandates_data = "[]"
    tasks_data = "[]"
    transfers_data = "[]"
    instruments_data = "[]"
    organizations_data = "[]"

    try:
        # TODO: implement this

        combined_data = {}

        return RealmData(
            json=json.dumps(combined_data),
            principal_id=principal_id,
            timestamp=current_time,
        )
    except Exception as e:
        ic.print(f"Error collecting realm data: {str(e)}")
        ic.print(traceback.format_exc())

        # Return empty data on error
        return RealmData(json="{}", principal_id=principal_id, timestamp=current_time)
