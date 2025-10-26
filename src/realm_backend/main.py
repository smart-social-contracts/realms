import json
import traceback

import api
from api.extensions import list_extensions
from api.ggg_entities import (
    list_objects,
    list_objects_paginated,
)
from api.status import get_status
from api.user import user_get, user_register, user_update_profile_picture
from core.candid_types_realm import (
    ExtensionCallArgs,
    ExtensionCallResponse,
    ObjectsListRecord,
    ObjectsListRecordPaginated,
    PaginationInfo,
    RealmResponse,
    RealmResponseData,
    StatusRecord,
    UserGetRecord,
)
from ggg import Codex
from kybra import (
    Async,
    CallResult,
    Duration,
    Func,
    Opt,
    Principal,
    Query,
    Record,
    StableBTreeMap,
    TimerId,
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

storage = StableBTreeMap[str, str](memory_id=1, max_key_size=100, max_value_size=10000)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("main")


class HttpRequest(Record):
    method: str
    url: str
    headers: Vec["Header"]
    body: blob


# Temporarily commented out to resolve compilation issues
# from kybra.canisters.management import (
#     HttpResponse,
#     HttpTransformArgs,
#     management_canister,
# )

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
def status() -> RealmResponse:
    try:
        logger.info("Status query executed")
        return RealmResponse(
            success=True, data=RealmResponseData(status=StatusRecord(**get_status()))
        )
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def get_extensions() -> RealmResponse:
    """Get all available extensions with their metadata"""
    return list_extensions(ic.caller().to_str())


@update
def join_realm(profile: str) -> RealmResponse:
    try:
        user = user_register(ic.caller().to_str(), profile)
        profiles = Vec[text]()
        if "profiles" in user and user["profiles"]:
            for p in user["profiles"]:
                profiles.append(p)

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                userGet=UserGetRecord(  # TODO: fix this
                    principal=Principal.from_str(user["principal"]),
                    profiles=profiles,
                    profile_picture_url=user.get("profile_picture_url", ""),
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def get_my_principal() -> text:
    return ic.caller().to_str()


@query
def get_my_user_status() -> RealmResponse:
    try:
        user = user_get(ic.caller().to_str())
        logger.info(f"User: {user}")
        if not user["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=user["error"])
            )

        profiles = Vec[text]()
        if "profiles" in user and user["profiles"]:
            for p in user["profiles"]:
                profiles.append(p)
        logger.info(f"Profiles: {profiles}")
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                userGet=UserGetRecord(
                    principal=Principal.from_str(user["principal"]),
                    profiles=profiles,
                    profile_picture_url=user["profile_picture_url"],
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@update
def update_my_profile_picture(profile_picture_url: str) -> RealmResponse:
    try:
        result = user_update_profile_picture(ic.caller().to_str(), profile_picture_url)
        if not result["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(error=result["error"])
            )

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                userGet=UserGetRecord(
                    principal=ic.caller(),
                    profiles=Vec[text](),
                    profile_picture_url=result["profile_picture_url"],
                )
            ),
        )
    except Exception as e:
        logger.error(
            f"Error updating profile picture: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


# New GGG API endpoints


@query
def get_objects_paginated(
    class_name: str, page_num: nat, page_size: nat
) -> RealmResponse:
    """
        Example:
    $ dfx canister call --output json ulvla-h7777-77774-qaacq-cai get_objects_paginated '("User", 0, 3)'
    {
      "data": {
        "objectsListPaginated": {
          "objects": [
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"User\", \"_id\": \"1\", \"id\": \"system\", \"profile_picture_url\": \"\"}",
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"User\", \"_id\": \"2\", \"id\": \"fiona_rodriguez_000\", \"profile_picture_url\": \"https://api.dicebear.com/7.x/personas/svg?seed=FionaRodriguez\"}",
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"User\", \"_id\": \"3\", \"id\": \"george_brown_001\", \"profile_picture_url\": \"https://api.dicebear.com/7.x/personas/svg?seed=GeorgeBrown\"}"
          ],
          "pagination": {
            "page_num": "0",
            "page_size": "3",
            "total_items_count": "51",
            "total_pages": "17"
          }
        }
      },
      "success": true
    }
    """

    try:
        logger.info(
            f"Listing {class_name} objects for page {page_num} with page size {page_size}"
        )
        result = list_objects_paginated(
            class_name, page_num=page_num, page_size=page_size
        )
        objects = result["items"]
        objects_json = [json.dumps(obj.serialize()) for obj in objects]
        logger.info(f"Objects JSON: {objects_json}")
        pagination = PaginationInfo(
            page_num=result["page_num"],
            page_size=result["page_size"],
            total_items_count=result["total_items_count"],
            total_pages=result["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                objectsListPaginated=ObjectsListRecordPaginated(
                    objects=objects_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


@query
def get_objects(params: Vec[Tuple[str, str]]) -> RealmResponse:
    """Example:

    $ dfx canister call --output json ulvla-h7777-77774-qaacq-cai get_objects '(
      vec { record { 0 = "User"; 1 = "1" };  record { 0 = "Realm"; 1 = "1" }; }
    )'
    {
      "data": {
        "objectsList": {
          "objects": [
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"User\", \"_id\": \"1\", \"id\": \"system\", \"profile_picture_url\": \"\"}",
            "{\"timestamp_created\": \"2025-09-10 11:28:41.147\", \"timestamp_updated\": \"2025-09-10 11:28:41.147\", \"creator\": \"system\", \"updater\": \"system\", \"owner\": \"system\", \"_type\": \"Realm\", \"_id\": \"1\", \"name\": \"Generated Demo Realm\", \"description\": \"Generated demo realm with 51 citizens and 5 organizations\", \"id\": \"0\", \"created_at\": \"2025-09-10T13:23:57.099332\", \"status\": \"active\", \"governance_type\": \"democratic\", \"population\": 51, \"organization_count\": 5, \"settings\": {\"voting_period_days\": 7, \"proposal_threshold\": 0.1, \"quorum_percentage\": 0.3, \"tax_rate\": 0.15, \"ubi_amount\": 1000}, \"relations\": {\"treasury\": [{\"_type\": \"Treasury\", \"_id\": \"2\"}]}}"
          ]
        }
      },
      "success": true
    }
    """

    try:
        logger.info("Listing objects")
        result = list_objects(params)
        objects = result
        objects_json = [json.dumps(obj.serialize()) for obj in objects]
        logger.info(f"Objects JSON: {objects_json}")
        return RealmResponse(
            success=True,
            data=RealmResponseData(objectsList=ObjectsListRecord(objects=objects_json)),
        )
    except Exception as e:
        logger.error(f"Error listing objects: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(error=str(e)))


def create_foundational_objects() -> void:
    """Create the foundational objects required for every realm to operate."""
    from ggg import Identity, Profiles, Realm, Treasury, User, UserProfile
    
    logger.info("Creating foundational objects...")
    
    # Check if foundational objects already exist (for upgrades)
    if len(Realm.instances()) > 0:
        logger.info("Foundational objects already exist, skipping creation")
        return
    
    try:
        # 1. Create user profiles
        admin_profile = UserProfile(
            name=Profiles.ADMIN["name"],
            allowed_to=",".join(Profiles.ADMIN["allowed_to"]),
            description="Admin user profile",
        )
        
        member_profile = UserProfile(
            name=Profiles.MEMBER["name"],
            allowed_to=",".join(Profiles.MEMBER["allowed_to"]),
            description="Member user profile",
        )
        
        logger.info("Created user profiles: admin, member")
        
        # 2. Create system user
        system_user = User(
            id="system",
            profile_picture_url="",
        )
        # Link system user to admin profile
        system_user.profiles.add(admin_profile)
        
        logger.info("Created system user")
        
        # 3. Create identity for system user
        import uuid
        system_identity = Identity(
            type="system",
            metadata=f"{uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:8]}",
        )
        
        logger.info("Created system identity")
        
        # 4. Create realm
        realm = Realm(
            name="Default Realm",
            description="A realm for digital governance and coordination",
            principal_id="",
        )
        
        logger.info("Created realm")
        
        # 5. Create treasury linked to realm
        treasury = Treasury(
            name=f"{realm.name} Treasury",
            vault_principal_id=None,  # Will be set during vault deployment
            realm=realm,
        )
        
        logger.info("Created treasury")
        logger.info("✅ All foundational objects created successfully")
        
    except Exception as e:
        logger.error(f"❌ Error creating foundational objects: {str(e)}\n{traceback.format_exc()}")
        raise


@update
def initialize() -> void:
    # Register all entity types from ggg
    import ggg
    from ggg import __all__ as entity_names

    for name in entity_names:
        try:
            entity_class = getattr(ggg, name)
            logger.info(f"Registering entity type {name}")
            Database.get_instance().register_entity_type(entity_class)
        except Exception as e:
            logger.error(
                f"Error registering entity type {name}: {str(e)}\n{traceback.format_exc()}"
            )
    
    # Create foundational objects after entity registration
    create_foundational_objects()

    # Initialize vault extension
    # First register vault entity types
    logger.info("Registering vault entity types...")
    from extension_packages.vault.entry import register_entities as register_vault_entities
    try:
        register_vault_entities()
    except Exception as e:
        logger.error(f"❌ Error registering vault entities: {str(e)}\n{traceback.format_exc()}")
    
    # Then initialize vault via extension call
    logger.info("Initializing vault extension...")
    try:
        result = api.extensions.extension_sync_call("vault", "initialize", "{}")
        logger.info(f"✅ Vault extension initialized: {result}")
    except Exception as e:
        logger.error(f"❌ Error initializing vault extension: {str(e)}\n{traceback.format_exc()}")


@init
def init_() -> void:
    logger.info("Initializing Realm canister")
    initialize()
    logger.info("Realm canister initialized")


@post_upgrade
def post_upgrade_() -> void:
    logger.info("Post-upgrade initializing Realm canister")
    initialize()
    logger.info("Realm canister initialized")


@update
def extension_sync_call(args: ExtensionCallArgs) -> ExtensionCallResponse:
    try:
        logger.debug(
            f"Sync calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        extension_result = api.extensions.extension_sync_call(
            args["extension_name"], args["function_name"], args["args"]
        )

        logger.debug(
            f"Got extension result from {args['extension_name']} function {args['function_name']}: {extension_result}, type: {type(extension_result)}"
        )

        return ExtensionCallResponse(success=True, response=str(extension_result))

    except Exception as e:
        logger.error(f"Error calling extension: {str(e)}\n{traceback.format_exc()}")
        return ExtensionCallResponse(success=False, response=str(e))


@update
def extension_async_call(args: ExtensionCallArgs) -> Async[ExtensionCallResponse]:
    try:
        logger.debug(
            f"Async calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        extension_coroutine = api.extensions.extension_async_call(
            args["extension_name"], args["function_name"], args["args"]
        )
        extension_result = yield extension_coroutine

        logger.debug(
            f"Got extension result from {args['extension_name']} function {args['function_name']}: {extension_result}, type: {type(extension_result)}"
        )

        return ExtensionCallResponse(success=True, response=str(extension_result))

    except Exception as e:
        logger.error(f"Error calling extension: {str(e)}\n{traceback.format_exc()}")
        return ExtensionCallResponse(success=False, response=str(e))


def http_request_core(data):
    d = json.dumps(data)
    return {
        "status_code": 200,
        "headers": [],
        "body": bytes(d + "\n", "ascii"),
        "streaming_strategy": None,
        "upgrade": False,
    }


# @query
# def transform_response(args: HttpTransformArgs) -> HttpResponse:
#     """Transform function for HTTP responses from extensions"""
#     logger.info("🔄 Transforming HTTP response")
#     http_response = args["response"]
#     logger.info(f"📊 Original response status: {http_response['status']}")
#     logger.info(f"📄 Response body size: {len(http_response['body'])} bytes")
#     logger.info("🧹 Clearing response headers for security")
#     http_response["headers"] = []
#     return http_response


# @query
# def http_transform(args: HttpTransformArgs) -> HttpResponse:
#     """Transform function for HTTP requests - removes headers for consensus"""
#     http_response = args["response"]
#     http_response["headers"] = []
#     return http_response


# @update
# def set_timer(delay: Duration) -> TimerId:
#     ic.call_self("timer_callback")
#     return ic.set_timer(delay, timer_callback)


def timer_callback():
    ic.print("timer_callback")


# @update
# def fire_download(codex_id: str) -> str:
#     logger.info("Firing download for codex: " + codex_id)
#     ic.set_timer(1, lambda: run_download)


# @update
# async def run_download() -> Async[None]:
#     codex_id = "test"
#     logger.info("Downloading code for codex: " + codex_id)
#     c = Codex[codex_id]
#     success, message = yield download_file_from_url(c.url)
#     logger.info("Success: " + str(success))
#     logger.info("Downloaded code: " + message)


# @update
# def download_file_from_url(url: str) -> Async[Tuple[bool, str]]:
#     """
#     Download file from a URL.
#
#     Returns:
#         Tuple of (success: bool, result: str)
#         - If success=True, result contains the downloaded file content
#         - If success=False, result contains the error message
#     """
#
#     try:
#         ic.print(f"Downloading code from URL: {url}")
#
#         # Make HTTP request to download the code
#         http_result: CallResult[HttpResponse] = yield management_canister.http_request(
#             {
#                 "url": url,
#                 "max_response_bytes": 1024 * 1024,  # 1MB limit for security
#                 "method": {"get": None},
#                 "headers": [
#                     {"name": "User-Agent", "value": "Realms-Codex-Downloader/1.0"}
#                 ],
#                 "body": None,
#                 "transform": {
#                     "function": (ic.id(), "http_transform"),
#                     "context": bytes(),
#                 },
#             }
#         ).with_cycles(15_000_000_000)
#
#         def handle_response(response: HttpResponse) -> Tuple[bool, str]:
#             try:
#                 # Decode the response body
#                 code_content = response["body"].decode("utf-8")
#                 ic.print(f"Successfully downloaded {len(code_content)} bytes")
#
#                 downloaded_content[url] = code_content
#                 return True, code_content
#
#             except UnicodeDecodeError as e:
#                 error_msg = f"Failed to decode response as UTF-8: {str(e)}"
#                 ic.print(error_msg)
#                 return False, error_msg
#             except Exception as e:
#                 error_msg = f"Error processing response: {str(e)}"
#                 ic.print(error_msg)
#                 return False, error_msg
#
#         def handle_error(err: str) -> Tuple[bool, str]:
#             error_msg = f"HTTP request failed: {err}"
#             ic.print(error_msg)
#             return False, error_msg
#
#         return match(http_result, {"Ok": handle_response, "Err": handle_error})
#
#     except Exception as e:
#         error_msg = f"Unexpected error downloading code: {str(e)}"
#         ic.print(error_msg)
#         return False, error_msg


def verify_checksum(content: str, expected_checksum: str) -> Tuple[bool, str]:
    """
    Verify the SHA-256 checksum of content.

    Args:
        content: The content to verify
        expected_checksum: Expected checksum in format "sha256:hash"

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    try:
        import hashlib

        # Parse the checksum format
        if not expected_checksum.startswith("sha256:"):
            return False, "Checksum must be in format 'sha256:hash'"

        expected_hash = expected_checksum[7:]  # Remove "sha256:" prefix

        # Calculate actual hash
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Compare hashes
        if actual_hash.lower() == expected_hash.lower():
            return True, ""
        else:
            return (
                False,
                f"Checksum mismatch. Expected: {expected_hash}, Got: {actual_hash}",
            )

    except Exception as e:
        return False, f"Error verifying checksum: {str(e)}"


# @query
# def http_request(req: HttpRequest) -> HttpResponse:
#     """Handle HTTP requests to the canister. Only for unauthenticated read operations."""
#
#     try:
#         method = req["method"]
#         url = req["url"]
#
#         logger.info(f"HTTP {method} request to {url}")
#
#         not_found = HttpResponse(
#             status_code=404,
#             headers=[],
#             body=bytes("Not found", "ascii"),
#             streaming_strategy=None,
#             upgrade=False,
#         )
#
#         if method == "GET":
#             url_path = url.split("/")
#
#             if url_path[0] != "api":
#                 return not_found
#
#             if url_path[1] != "v1":
#                 return not_found
#
#             if url_path[2] == "status":
#                 return http_request_core(get_status())
#
#             # if url_path[2] == "extensions":
#             #     if len(url_path) < 4:
#             #         # List all extensions
#             #         extensions_list = list_extensions()
#             #         return http_request_core({"extensions": extensions_list})
#
#             # Note: We no longer need to handle extension-specific HTTP endpoints here
#             # as we have proper canister methods now
#
#         return not_found
#     except Exception as e:
#         logger.error(f"Error handling HTTP request: {str(e)}\n{traceback.format_exc()}")
#         return {
#             "status_code": 500,
#             "headers": [],
#             "body": bytes(traceback.format_exc(), "ascii"),
#             "streaming_strategy": None,
#             "upgrade": False,
#         }


@update
def execute_code(code: str) -> str:
    """
    Executes Python code (sync or async) via TaskManager.

    For sync code: executes inline and returns result immediately
    For async code: schedules task and returns task ID for polling

    Examples:
        # Sync code
        result = 2 + 2

        # Async code
        def async_task():
            result = yield some_async_operation()
            return result
    """
    import json
    import traceback

    from core.task_manager import Call, Task, TaskManager, TaskStep
    from ggg.task_schedule import TaskSchedule

    try:
        # Detect if code is async (contains 'yield' or defines 'async_task')
        is_async = "yield" in code or "async_task" in code

        # Create temporary codex
        temp_name = f"_shell_{int(ic.time())}"
        codex = Codex(name=temp_name, code=code)

        # Create call
        call = Call(is_async=is_async, codex=codex)

        # Create task
        step = TaskStep(call=call)
        task = Task(name=f"Shell Task {temp_name}", steps=[step])

        # Create schedule (immediate execution)
        schedule = TaskSchedule(
            task=task,
            run_at=0,  # Execute immediately
            repeat_every=0,
            last_run_at=0,
            disabled=False,
        )

        # Execute via TaskManager
        manager = TaskManager()
        manager.add_task(task)
        manager.run()

        # Format response
        if is_async:
            # Async task will complete in timer callback
            response = {
                "type": "async",
                "task_id": task._id,
                "status": task.status,
                "message": "Async task scheduled. Check logs for results or use get_task_status() to poll.",
            }
            return json.dumps(response, indent=2)
        else:
            # Sync task should be completed
            # Get result from call if available
            result = getattr(call, "_result", None)

            response = {"type": "sync", "status": task.status, "task_id": task._id}

            if result is not None:
                if isinstance(result, dict):
                    response["result"] = result
                else:
                    response["result"] = str(result)
            else:
                response["message"] = "Code executed successfully (no return value)"

            return json.dumps(response, indent=2)

    except Exception as e:
        ic.print(f"Error in execute_code: {e}")
        ic.print(traceback.format_exc())
        response = {
            "type": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
        return json.dumps(response, indent=2)


@update
def execute_code_shell(code: str) -> str:
    """Executes Python code and returns the output.

    This is the core function needed for the Kybra Simple Shell to work.
    It captures stdout, stderr, and return values from the executed code.
    """
    import io
    import sys
    import traceback

    stdout = io.StringIO()
    stderr = io.StringIO()
    sys.stdout = stdout
    sys.stderr = stderr

    try:
        # Try to evaluate as an expression
        result = eval(code, globals())
        if result is not None:
            ic.print(repr(result))
    except SyntaxError:
        try:
            # If it's not an expression, execute it as a statement
            # Use the built-in exec function but with a different name to avoid conflict
            exec_builtin = exec
            exec_builtin(code, globals())
        except Exception:
            traceback.print_exc()
    except Exception:
        traceback.print_exc()

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    return stdout.getvalue() + stderr.getvalue()


@query
def get_task_status(task_id: str) -> str:
    """
    Poll task status and get results for async tasks.

    Returns JSON with:
    - task_id: The task identifier
    - status: pending, running, completed, or failed
    - result: The task result (if completed)
    - error: Error message (if failed)
    """
    import json

    from core.task_manager import Task

    try:
        task = Task[task_id]

        response = {"task_id": task_id, "status": task.status, "name": task.name}

        # Get the first step's call to check for results
        if task.steps:
            step = list(task.steps)[0]
            result = getattr(step.call, "_result", None)

            if result is not None:
                if isinstance(result, dict):
                    response["result"] = result
                else:
                    response["result"] = str(result)

        return json.dumps(response, indent=2)

    except KeyError:
        response = {"error": f"Task with ID '{task_id}' not found"}
        return json.dumps(response, indent=2)
    except Exception as e:
        response = {"error": str(e)}
        return json.dumps(response, indent=2)


downloaded_content: dict = {}


# @update
# def test_mixed_sync_async_task() -> void:
#     try:
#         """Test function to verify TaskManager can handle mixed sync/async steps in sequence"""
#         ic.print("Setting up mixed sync/async task test")

#         url = "https://raw.githubusercontent.com/smart-social-contracts/realms/refs/heads/main/src/realm_backend/codex.py"

#         async_call = Call()
#         async_call.is_async = True
#         # async_call._function_def = download_file_from_url  # TODO: temporarily disabled
#         async_call._function_params = [url]
#         step1 = TaskStep(call=async_call, run_next_after=10)

#         sync_call = Call()
#         sync_call.is_async = False
#         codex = Codex()
#         codex.code = """
# from main import downloaded_content

# content = downloaded_content['{url}']

# codex = Codex["the_code"]
# if not codex:
#     codex = Codex()
#     codex.name = "the_code"
# codex.code = content

# ic.print("=== VERIFICATION STEP ===")
# ic.print(f"Downloaded content length: len(content)")
# if len(content) > 0:
#     ic.print("✅ SUCCESS: File was downloaded successfully!")
#     if "def " in downloaded_content:
#         ic.print("✅ SUCCESS: Content contains Python code (found 'def')")
#     else:
#         ic.print("❌ WARNING: Content doesn't appear to be Python code")
#     preview = downloaded_content[:100].replace("\\n", " ")
#     ic.print("Content preview: " + preview + "...")
# else:
#     ic.print("❌ FAILURE: No content was downloaded!")
# ic.print("=== VERIFICATION COMPLETE ===")""".strip()
#         sync_call.codex = codex
#         step2 = TaskStep(call=sync_call)

#         task = Task(name="test_mixed_steps", steps=[step1, step2])
#         schedule = TaskSchedule(run_at=0, repeat_every=30)
#         task.schedules = [schedule]

#         task_manager = TaskManager()
#         task_manager.add_task(task)
#         task_manager.run()

#         ic.print("Mixed sync/async task test initiated...")
#     except Exception as e:
#         logger.error(traceback.format_exc())
