import json
import traceback

# Import functions from api.ggg_entities instead of main
from api.ggg_entities import (
    list_instruments,
    list_mandates,
    list_organizations,
    list_tasks,
    list_transfers,
    list_users,
)
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
    """Get configuration for the LLM chat extension.

    Returns:
        LLMChatResponse: A simple acknowledgment
    """
    return LLMChatResponse(response="LLM Chat extension is ready")


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
        # Get users data directly from api.ggg_entities
        try:
            users_result = list_users()
            if users_result and "users" in users_result:
                users_data = json.dumps(users_result["users"])
            ic.print(f"Retrieved users data: {len(users_data)} bytes")
        except Exception as e:
            ic.print(f"Error getting users data: {str(e)}")
            ic.print(traceback.format_exc())

        # Get mandates data
        try:
            mandates_result = list_mandates()
            if mandates_result and "mandates" in mandates_result:
                mandates_data = json.dumps(mandates_result["mandates"])
            ic.print(f"Retrieved mandates data: {len(mandates_data)} bytes")
        except Exception as e:
            ic.print(f"Error getting mandates data: {str(e)}")

        # Get tasks data
        try:
            tasks_result = list_tasks()
            if tasks_result and "tasks" in tasks_result:
                tasks_data = json.dumps(tasks_result["tasks"])
            ic.print(f"Retrieved tasks data: {len(tasks_data)} bytes")
        except Exception as e:
            ic.print(f"Error getting tasks data: {str(e)}")

        # Get transfers data
        try:
            transfers_result = list_transfers()
            if transfers_result and "transfers" in transfers_result:
                transfers_data = json.dumps(transfers_result["transfers"])
            ic.print(f"Retrieved transfers data: {len(transfers_data)} bytes")
        except Exception as e:
            ic.print(f"Error getting transfers data: {str(e)}")

        # Get instruments data
        try:
            instruments_result = list_instruments()
            if instruments_result and "instruments" in instruments_result:
                instruments_data = json.dumps(instruments_result["instruments"])
            ic.print(f"Retrieved instruments data: {len(instruments_data)} bytes")
        except Exception as e:
            ic.print(f"Error getting instruments data: {str(e)}")

        # Get organizations data
        try:
            organizations_result = list_organizations()
            if organizations_result and "organizations" in organizations_result:
                organizations_data = json.dumps(organizations_result["organizations"])
            ic.print(f"Retrieved organizations data: {len(organizations_data)} bytes")
        except Exception as e:
            ic.print(f"Error getting organizations data: {str(e)}")

        # Return the collected data
        combined_data = {
            "users": json.loads(users_data),
            "mandates": json.loads(mandates_data),
            "tasks": json.loads(tasks_data),
            "transfers": json.loads(transfers_data),
            "instruments": json.loads(instruments_data),
            "organizations": json.loads(organizations_data),
        }

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
