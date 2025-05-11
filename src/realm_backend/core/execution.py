import ast
import os
import traceback

"""
Any user: calling `run_code`
Any organization: when a hook is triggered, such as:
    proposal is approved
    a new user/organizaiton requests to join
    when a token operation happens and the token hooks inform the organization hook
Any token:
    Root: during initialization
"""


ROOT_USER_NAME = "root"  # TODO: by default, and for security reasons, this should be set to None or something with no authority
caller_id: str = (
    None  # TODO: figure out what to do when None... it should never be... probably the best is to use the canister address, which is a DAO by itself
)


def _set_caller(name: str):
    global caller_id
    caller_id = name


def caller() -> str:
    try:
        from kybra import ic

        _set_caller(str(ic.caller()))
    except:
        _set_caller(str(os.environ.get("IC_CALLER", ROOT_USER_NAME)))
    return caller_id


def run_code(source_code: str, locals={}):
    # from ggg.world import World
    # from ggg.state import State
    from core.system_time import DAY, get_system_time, timestamp_to_date
    from ggg.organization import Organization
    from ggg.proposal import Proposal
    from ggg.token import Token
    from ggg.user import User
    from ggg.wallet import Wallet
    # from ggg.base import set_caller
    from stats.snapshot import take_snapshot

    safe_globals = globals()
    # safe_globals['caller'] = ic.caller()
    # safe_globals.update(
    #     {
    #         "World": World,
    #         "State": State,
    #         "Organization": Organization,
    #         "Wallet": Wallet,
    #         "Token": Token,
    #         "User": User,
    #         "Citizen": Citizen,
    #         "Proposal": Proposal,
    #         "get_system_time": get_system_time,
    #         "timestamp_to_date": timestamp_to_date,
    #         "DAY": DAY,
    #         "set_caller": set_caller,
    #         "take_snapshot": take_snapshot,
    #     }
    # )

    import ggg
    import stats

    safe_globals.update({"ggg": ggg, "stats": stats})
    safe_locals = {}
    # safe_locals = {
    #     "class_model": sys.modules[__name__]
    # }  # export the classes and functions independently to save the dev to type "class_model"
    safe_locals.update(locals)

    try:
        exec(source_code, safe_globals, safe_locals)
        result = {"status": "success", "output": safe_locals.get("result")}
    except Exception as e:
        stack_trace = traceback.format_exc()
        result = {"status": "error", "stack_trace": stack_trace}

    # from pprint import pprint
    # print('ggg.base.universe()')
    # pprint(ggg.base.universe())

    return result


def contains_function(source_code: str, function_name: str) -> bool:
    # Parse the source code into an AST
    tree = ast.parse(source_code)
    # Walk through each node in the AST and check for function definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return True
    return False


def execute_heartbeat():
    """Common function to execute heartbeat hooks for all organizations.
    This is used by both the Flask and ICP versions of the application.
    """
    try:
        # Get all organizations using instances method
        from ggg import Organization

        organizations = Organization.instances()

        # Execute heartbeat hook for each organization that has an extension
        for org in organizations:
            if org.extension:
                try:
                    # Run the heartbeat_hook function from the extension code
                    org.extension.run("heartbeat_hook")
                except Exception as e:
                    print(
                        f"Error executing heartbeat_hook for organization {org.id}: {str(e)}"
                    )

        return True
    except Exception as e:
        print(f"Error in heartbeat execution: {str(e)}")
        return False


# # Example usage
# source_code = """
# def my_function():
#     pass

# def another_function():
#     pass
# """

# print(contains_function(source_code, "my_function"))  # Output: True
# print(contains_function(source_code, "non_existent_function"))  # Output: False
