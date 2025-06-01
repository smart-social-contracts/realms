from kybra import Record, ic, text, Principal, Vec, Opt, blob, nat64
import json
import traceback

# Import functions from api.ggg_entities instead of main
from api.ggg_entities import (
    list_users, list_mandates, list_tasks, 
    list_transfers, list_instruments, list_organizations
)

class LLMChatResponse(Record):
    response: text

# Container for relevant realm data to be sent to the LLM.
# This provides context about the current state of the realm.
class RealmData(Record):
    users: text
    mandates: text
    tasks: text
    transfers: text
    instruments: text
    organizations: text
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
        return RealmData(
            users=users_data,
            mandates=mandates_data,
            tasks=tasks_data,
            transfers=transfers_data,
            instruments=instruments_data,
            organizations=organizations_data,
            principal_id=principal_id,
            timestamp=current_time
        )
    except Exception as e:
        ic.print(f"Error collecting realm data: {str(e)}")
        ic.print(traceback.format_exc())
        
        # Return empty data on error
        return RealmData(
            users="[]",
            mandates="[]",
            tasks="[]",
            transfers="[]",
            instruments="[]",
            organizations="[]",
            principal_id=principal_id,
            timestamp=current_time
        ) 