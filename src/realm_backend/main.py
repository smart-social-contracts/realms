import base64
import importlib
import json
import traceback

import api
from api.extensions import list_extensions
from api.ggg_entities import (
    list_objects,
    list_objects_paginated,
)
from api.registry import get_registry_info, register_realm
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
from core.task_manager import TaskManager
from ggg import Call, Codex, Task, TaskStep
from ggg.task_schedule import TaskSchedule
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
    heartbeat,
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
from kybra_simple_logging import get_logger, get_logs
from core.http_utils import download_file_from_url, downloaded_content

storage = StableBTreeMap[str, str](memory_id=1, max_key_size=100, max_value_size=10000)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("main")


class HttpRequest(Record):
    method: str
    url: str
    headers: Vec["Header"]
    body: blob


# Import management canister for HTTP requests
from kybra.canisters.management import (
    HttpResponse,
    HttpTransformArgs,
    management_canister,
)

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
def get_canister_id() -> text:
    """Return this canister's principal ID"""
    return ic.id().to_str()


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
    class_name: str, page_num: nat, page_size: nat, order: str = "asc"
) -> RealmResponse:
    """
    Get paginated list of objects with optional ordering.

    Args:
        class_name: Name of the entity class (e.g., "User", "Transfer", "Mandate")
        page_num: Page number (0-indexed)
        page_size: Number of items per page
        order: Sort order - "asc" for ascending (oldest first) or "desc" for descending (newest first)

    Example (ascending):
    $ dfx canister call --output json canister_id get_objects_paginated '("User", 0, 3, "asc")'

    Example (descending):
    $ dfx canister call --output json canister_id get_objects_paginated '("User", 0, 3, "desc")'

    Response:
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
            f"Listing {class_name} objects for page {page_num} with page size {page_size}, order: {order}"
        )
        result = list_objects_paginated(
            class_name, page_num=page_num, page_size=page_size, order=order
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
        logger.error(
            f"❌ Error creating foundational objects: {str(e)}\n{traceback.format_exc()}"
        )
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

    # Initialize all installed extensions
    logger.info("Discovering and initializing extensions...")

    try:
        # Get all installed extension manifests
        extension_manifests = api.extensions.get_all_extension_manifests()
        extension_ids = list(extension_manifests.keys())
        logger.info(f"Found {len(extension_ids)} installed extensions: {extension_ids}")

        # Track status for each extension
        extension_status = {}

        # Initialize each extension
        for extension_id in extension_ids:

            extension_manifest = extension_manifests.get(extension_id, {})
            entity_method_overrides = extension_manifest.get(
                "entity_method_overrides", []
            )

            if not entity_method_overrides:
                logger.info(f"No method overrides found for {extension_id}")
            else:
                logger.info(
                    f"Loading {len(entity_method_overrides)} method override(s) for {extension_id}"
                )
                for override in entity_method_overrides:
                    try:
                        entity_name = override.get("entity")
                        method_name = override.get("method")
                        impl_path = override.get("implementation")
                        method_type = override.get(
                            "type", "method"
                        )  # default to instance method

                        # Validate manifest data
                        if not all([entity_name, method_name, impl_path]):
                            logger.warning(
                                f"Invalid override in {extension_id}: missing entity/method/implementation"
                            )
                            continue

                        # Get entity class
                        entity_class = getattr(ggg, entity_name, None)
                        if not entity_class:
                            logger.warning(
                                f"Entity '{entity_name}' not found in ggg module"
                            )
                            continue

                        # Import implementation
                        parts = impl_path.split(".")
                        module_path = (
                            f"extension_packages.{extension_id}.{'.'.join(parts[:-1])}"
                        )
                        func_name = parts[-1]

                        impl_module = importlib.import_module(module_path)
                        impl_func = getattr(impl_module, func_name, None)

                        if not impl_func:
                            logger.warning(
                                f"Function '{func_name}' not found in {module_path}"
                            )
                            continue

                        # Bind method to entity (wrap as classmethod if specified)
                        if method_type == "classmethod":
                            setattr(entity_class, method_name, classmethod(impl_func))
                            logger.info(
                                f"  ✓ {entity_name}.{method_name}() [classmethod] -> {extension_id}.{impl_path}"
                            )
                        elif method_type == "staticmethod":
                            setattr(entity_class, method_name, staticmethod(impl_func))
                            logger.info(
                                f"  ✓ {entity_name}.{method_name}() [staticmethod] -> {extension_id}.{impl_path}"
                            )
                        else:
                            setattr(entity_class, method_name, impl_func)
                            logger.info(
                                f"  ✓ {entity_name}.{method_name}() -> {extension_id}.{impl_path}"
                            )

                    except Exception as e:
                        logger.error(
                            f"Error binding method override in {extension_id}: {str(e)}"
                        )
                        logger.error(traceback.format_exc())

            status = {
                "has_entities": False,
                "has_initialize": False,
                "entity_error": False,
                "init_error": False,
            }

            # Step 1: Try to register extension entity types
            try:
                extension_module = __import__(
                    f"extension_packages.{extension_id}.entry",
                    fromlist=["register_entities"],
                )

                if hasattr(extension_module, "register_entities"):
                    extension_module.register_entities()
                    status["has_entities"] = True
            except ImportError:
                # No entry module - that's fine
                pass
            except Exception as e:
                logger.warning(
                    f"Error registering entity types for {extension_id}: {str(e)}"
                )
                status["entity_error"] = True

            # Step 2: Try to call extension initialize function
            try:
                result = api.extensions.extension_sync_call(
                    extension_id, "initialize", "{}"
                )
                status["has_initialize"] = True
            except Exception as e:
                # Log the actual error message to help debug
                error_msg = str(e)
                logger.info(
                    f"  [DEBUG] Extension {extension_id} initialize exception: {error_msg}"
                )

                # Check if it's a real error or just missing function
                # Common indicators that the function simply doesn't exist:
                missing_function_indicators = [
                    "not found",
                    "no function",
                    "has no",
                    "does not have",
                    "no attribute",
                    "'initialize'",
                    "attributeerror",
                ]

                is_missing_function = any(
                    indicator in error_msg.lower()
                    for indicator in missing_function_indicators
                )

                if not is_missing_function:
                    # This seems like a real error, not just a missing function
                    logger.warning(f"Error initializing {extension_id}: {error_msg}")
                    status["init_error"] = True
                # Otherwise it's just a missing function (optional), status stays False

            extension_status[extension_id] = status

        # Load entity method overrides from Realm manifest
        logger.info("\n🔧 Checking for Codex entity method overrides from Realm manifest...")
        try:
            from ggg import Codex, Realm
            import json
            
            realm = list(Realm.instances())[0] if Realm.instances() else None
            logger.info(f"Realm found: {realm.name if realm else 'None'}")
            
            if realm:
                logger.info(f"Has manifest_data: {bool(realm.manifest_data)}")
                if realm.manifest_data:
                    logger.info(f"manifest_data length: {len(str(realm.manifest_data))}")
                    manifest = json.loads(str(realm.manifest_data))
                    logger.info(f"Parsed manifest keys: {list(manifest.keys())}")
                    
                    overrides = manifest.get("entity_method_overrides", [])
                    logger.info(f"Found {len(overrides)} entity method overrides")
                    
                    for o in overrides:
                        try:
                            if not all([o.get("entity"), o.get("method"), o.get("implementation")]):
                                logger.warning(f"Skipping incomplete override: {o}")
                                continue
                            entity_class = getattr(ggg, o["entity"], None)
                            parts = o["implementation"].split(".")
                            if not entity_class or len(parts) != 3 or parts[0] != "Codex":
                                logger.warning(f"Invalid override config: entity_class={entity_class}, parts={parts}")
                                continue
                            target_codex = Codex[parts[1]]
                            if not target_codex:
                                logger.warning(f"Codex not found: {parts[1]}")
                                continue
                            ns = {}
                            exec(str(target_codex.code), ns)
                            func = ns.get(parts[2])
                            if not func:
                                logger.warning(f"Function not found in codex: {parts[2]}")
                                continue
                            method_type = o.get("type", "method")
                            wrapper = classmethod(func) if method_type == "classmethod" else staticmethod(func) if method_type == "staticmethod" else func
                            setattr(entity_class, o["method"], wrapper)
                            logger.info(f"  ✓ {o['entity']}.{o['method']}() [{method_type}] -> {o['implementation']}")
                        except Exception as e:
                            logger.error(f"Codex override error for {o}: {e}")
                else:
                    logger.warning("Realm.manifest_data is empty")
        except Exception as e:
            logger.error(f"Failed to load entity method overrides from Realm manifest: {e}")

        # Print summary as a table
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 EXTENSION INITIALIZATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total extensions: {len(extension_ids)}")
        logger.info("")
        logger.info(
            f"{'Extension Name':<30} {'Entity Registration':<25} {'Initialize'}"
        )
        logger.info("-" * 70)

        for ext_id in sorted(extension_ids):
            status = extension_status[ext_id]

            # Format entity registration status
            if status["entity_error"]:
                entity_status = "❌ Error"
            elif status["has_entities"]:
                entity_status = "✅ Yes"
            else:
                entity_status = "➖ No"

            # Format initialize status
            if status["init_error"]:
                init_status = "❌ Error"
            elif status["has_initialize"]:
                init_status = "✅ Yes"
            else:
                init_status = "➖ No"

            logger.info(f"{ext_id:<30} {entity_status:<25} {init_status}")

        logger.info("=" * 70)
        logger.info("✅ Extension initialization complete.")
        logger.info("")

    except Exception as e:
        logger.error(
            f"❌ Critical error during extension initialization: {str(e)}\n{traceback.format_exc()}"
        )


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


@query
def http_transform(args: HttpTransformArgs) -> HttpResponse:
    """Transform function for HTTP requests - removes headers for consensus"""
    http_response = args["response"]
    http_response["headers"] = []
    return http_response


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


@update
def download_file(
    url: str,
    codex_name: str,
    callback_code: Opt[str] = None,
    checksum: Opt[str] = None,
) -> str:
    """
        Convenient wrapper to download a file from a URL and save it to a Codex.

        This function creates a two-step task:
        1. Step 1 (async): Download the file from the URL
        2. Step 2 (sync): Verify checksum (if provided) and save content to a Codex

        The downloaded content is stored in `downloaded_content[url]` dictionary
        and can be accessed by the callback code.

        Args:
            url: The URL to download from
            codex_name: Name for the Codex where the downloaded content will be saved
            callback_code: Optional Python code to process the downloaded content.
                          The code can access the downloaded content via:
                          `from main import downloaded_content; content = downloaded_content['<url>']`
                          If None, a default callback saves content to the specified Codex.
            checksum: Optional checksum in format "sha256:hash" to verify downloaded content.
                     If verification fails, the content will not be saved to the Codex.

        Returns:
            JSON string with task information:
            - success: Boolean
            - task_id: The created task ID
            - task_name: The task name
            - url: The URL being downloaded
            - codex_name: The name of the Codex where content will be saved
            - checksum: The checksum used for verification (if provided)
            - error: Error message if failed

        Example usage from a Codex:
            from main import download_file

            # Download and save to a Codex
            download_file(
                "https://example.com/data.json",
                "my_downloaded_data"
            )

            # Download with checksum verification
            download_file(
                "https://example.com/code.py",
                "verified_code",
                checksum="sha256:abc123..."
            )

            # Download with custom processing
            callback = '''
    from main import downloaded_content
    from ggg import Codex
    import json

    content = downloaded_content['https://example.com/data.json']
    data = json.loads(content)
    ic.print(f"Processing {len(data)} items...")
    # ... custom processing logic ...
    codex = Codex(name="processed_data", code=str(data))
    ic.print(f"Saved to codex {codex._id}")
    '''
            download_file(
                "https://example.com/data.json",
                "raw_data",
                callback
            )
    """
    try:
        task_name = f"download_{codex_name}_{int(ic.time())}"

        # Step 1: Async download
        download_codex = Codex(
            name=f"_{task_name}_download",
            code=f"""
from main import download_file_from_url

def async_task():
    ic.print("[Step 1/2] Downloading file from URL: {url}")
    url = "{url}"
    result = yield download_file_from_url(url)
    success, content = result
    if success:
        ic.print(f"[Step 1/2] ✅ Downloaded {{len(content)}} bytes")
    else:
        ic.print(f"[Step 1/2] ❌ Download failed: {{content}}")
    return result
""".strip(),
        )

        async_call = Call(is_async=True, codex=download_codex)
        step1 = TaskStep(call=async_call, run_next_after=0)

        # Step 2: Sync callback to save to Codex
        if callback_code is None:
            # Default callback: verify checksum (if provided) and save to specified Codex
            checksum_verification = ""
            if checksum:
                checksum_verification = f"""
    # Verify checksum
    from main import verify_checksum
    checksum = "{checksum}"
    is_valid, error_msg = verify_checksum(content, checksum)
    
    if not is_valid:
        ic.print(f"[Step 2/2] ❌ Checksum verification failed: {{error_msg}}")
        ic.print("[Step 2/2] ❌ Content NOT saved due to checksum mismatch")
        raise Exception(f"Checksum verification failed: {{error_msg}}")
    
    ic.print("[Step 2/2] ✅ Checksum verification passed")
"""

            callback_code = f"""
from main import downloaded_content
from ggg import Codex

url = "{url}"
codex_name = "{codex_name}"

if url in downloaded_content:
    content = downloaded_content[url]
    ic.print("[Step 2/2] ✅ Download verification successful")
    ic.print(f"[Step 2/2] Content length: {{len(content)}} bytes")
    {checksum_verification}
    # Save to Codex
    codex = Codex[codex_name]
    if not codex:
        codex = Codex(name=codex_name)
    codex.code = content
    
    ic.print(f"[Step 2/2] ✅ Saved to Codex '{{codex_name}}' (ID: {{codex._id}})")
    
    if len(content) > 0:
        preview = content[:100].replace("\\n", " ")
        ic.print(f"[Step 2/2] Preview: {{preview}}...")
else:
    ic.print("[Step 2/2] ❌ ERROR: Content not found in downloaded_content")
""".strip()

        callback_codex = Codex(name=f"_{task_name}_callback", code=callback_code)

        sync_call = Call(is_async=False, codex=callback_codex)
        step2 = TaskStep(call=sync_call, run_next_after=0)

        # Create task with both steps
        task = Task(name=task_name, steps=[step1, step2])

        # Create schedule for immediate execution
        schedule = TaskSchedule(
            name=f"schedule_{task_name}",
            task=task,
            run_at=0,  # Execute immediately
            repeat_every=0,  # One-time execution
            last_run_at=0,
            disabled=False,
        )

        # Register with TaskManager
        manager = TaskManager()
        manager.add_task(task)

        logger.info(
            f"Created download task: {task_name} (ID: {task._id}) for URL: {url} -> Codex: {codex_name}"
        )

        # Trigger task manager
        TaskManager().run()

        response_data = {
            "success": True,
            "task_id": str(task._id),
            "task_name": str(task.name),
            "url": url,
            "codex_name": codex_name,
            "message": "Download task created and scheduled",
        }

        if checksum:
            response_data["checksum"] = checksum

        return json.dumps(response_data, indent=2)

    except Exception as e:
        logger.error(f"Error creating download task: {e}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)}, indent=2)


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

    from core.task_manager import TaskManager
    from ggg import Call, Task, TaskStep
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
            name=f"Shell Schedule {temp_name}",
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


# get_task_status removed - use get_objects_paginated("Task", ...) instead

# list_scheduled_tasks removed - use get_objects_paginated("Task", ...) and get_objects_paginated("TaskSchedule", ...) instead


@update
def stop_task(task_id: str) -> str:
    """
    Stop a scheduled task by disabling its schedules and marking it as cancelled.

    Args:
        task_id: Full or partial task ID to stop

    Returns JSON with:
    - success: Boolean indicating success
    - task_id: The stopped task ID
    - name: The task name
    - error: Error message if failed
    """
    import json

    from ggg.task import Task

    try:
        # Try to find task by partial or full ID
        found_task = None
        for task in Task.instances():
            if task._id.startswith(task_id) or task._id == task_id:
                found_task = task
                break

        if found_task:
            # Mark task as cancelled
            if hasattr(found_task, "status"):
                found_task.status = "cancelled"

            # Disable all schedules
            for schedule in found_task.schedules:
                schedule.disabled = True

            logger.info(f"Stopped task: {found_task.name} ({found_task._id})")
            return json.dumps(
                {"success": True, "task_id": found_task._id, "name": found_task.name},
                indent=2,
            )
        else:
            return json.dumps(
                {"success": False, "error": f"Task not found: {task_id}"}, indent=2
            )

    except Exception as e:
        logger.error(f"Error stopping task: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@update
def start_task(task_id: str) -> str:
    """
    Start a scheduled task by enabling its schedules and triggering execution.

    Args:
        task_id: Full or partial task ID to start

    Returns JSON with:
    - success: Boolean indicating success
    - task_id: The started task ID
    - name: The task name
    - error: Error message if failed
    """
    import json

    from core.task_manager import TaskManager
    from ggg import Call, Task, TaskStep

    try:
        # Try to find task by partial or full ID
        found_task = None
        for task in Task.instances():
            if str(task._id).startswith(task_id) or str(task._id) == task_id:
                found_task = task
                break

        if not found_task:
            return json.dumps(
                {"success": False, "error": f"Task not found: {task_id}"}, indent=2
            )

        # Check if task has steps - if not, create them from metadata
        # Note: GGG Task entities may not have 'steps' attribute (only TaskManager.Task does)
        has_steps = hasattr(found_task, 'steps') and found_task.steps and len(list(found_task.steps)) > 0
        if not has_steps:
            logger.info(f"Task {found_task.name} has no steps, creating from metadata")
            
            # Parse metadata to get codex_name
            metadata = {}
            if found_task.metadata:
                try:
                    metadata = json.loads(found_task.metadata)
                except:
                    pass
            
            codex_name = metadata.get("codex_name")
            if not codex_name:
                return json.dumps(
                    {"success": False, "error": f"Task has no steps and no codex_name in metadata"}, 
                    indent=2
                )
            
            # Find the codex
            codex = None
            for c in Codex.instances():
                if c.name == codex_name:
                    codex = c
                    break
            
            if not codex:
                return json.dumps(
                    {"success": False, "error": f"Codex '{codex_name}' not found"}, 
                    indent=2
                )
            
            if not codex.code:
                return json.dumps(
                    {"success": False, "error": f"Codex '{codex_name}' has no code"}, 
                    indent=2
                )
            
            # Check if codex is async (contains 'yield')
            is_async = "yield" in codex.code
            
            # Create Call and TaskStep
            call = Call(is_async=is_async, codex=codex)
            step = TaskStep(call=call, run_next_after=0)
            step.task = found_task
            
            logger.info(f"Created step for task {found_task.name} using codex {codex_name} (async={is_async})")

        # Mark task as pending and reset step counter
        found_task.status = "pending"
        if hasattr(found_task, 'step_to_execute'):
            found_task.step_to_execute = 0
        
        # Reset all step statuses (if task has steps)
        if hasattr(found_task, 'steps') and found_task.steps:
            for step in found_task.steps:
                step.status = "pending"

        # Enable all schedules and reset last_run_at for immediate execution
        # Check both the task's schedules relation and find schedules by task reference
        from ggg.task_schedule import TaskSchedule
        schedules_found = False
        
        # Try to get schedules from task relationship
        if hasattr(found_task, 'schedules') and found_task.schedules:
            for schedule in found_task.schedules:
                schedule.disabled = False
                schedule.last_run_at = 0
                schedules_found = True
                logger.info(f"Enabled schedule: {schedule.name}")
        
        # Also search for schedules that reference this task by ID
        if not schedules_found:
            for schedule in TaskSchedule.instances():
                # Check if schedule references this task
                if hasattr(schedule, 'task') and schedule.task and str(schedule.task._id) == str(found_task._id):
                    schedule.disabled = False
                    schedule.last_run_at = 0
                    schedules_found = True
                    logger.info(f"Found and enabled orphan schedule: {schedule.name}")

        logger.info(f"Starting task: {found_task.name} ({found_task._id})")

        # If no schedules found, create a one-time schedule for immediate execution
        if not schedules_found:
            logger.info(f"No schedules found for task {found_task.name}, creating one-time schedule")
            schedule = TaskSchedule(
                name=f"{found_task.name}_schedule",
                disabled=False,
                run_at=0,  # Run immediately
                repeat_every=0,  # One-time execution
                last_run_at=0,
            )
            schedule.task = found_task
            logger.info(f"Created one-time schedule for task {found_task.name}")

        # Trigger task manager to process the schedule
        TaskManager().run()

        return json.dumps(
            {"success": True, "task_id": str(found_task._id), "name": found_task.name},
            indent=2,
        )

    except Exception as e:
        import traceback
        logger.error(f"Error starting task: {e}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@query
def get_task_logs(task_id: str, limit: nat = 20) -> str:
    """
    Get execution logs for a specific task.

    Args:
        task_id: Full or partial task ID
        limit: Maximum number of recent executions to return (default: 20)

    Returns JSON with:
    - success: Boolean indicating success
    - task_id: The task ID
    - task_name: The task name
    - status: Current task status
    - executions: Array of recent execution records with logs
    - error: Error message if failed
    """
    import json

    from ggg.task import Task

    try:
        # Try to find task by partial or full ID
        found_task = None
        for task in Task.instances():
            if task._id.startswith(task_id) or task._id == task_id:
                found_task = task
                break

        if found_task:
            # Get executions
            executions = (
                list(found_task.executions) if hasattr(found_task, "executions") else []
            )

            # Format execution data with logs from kybra_simple_logging
            execution_data = []
            for execution in executions[-limit:]:
                # Compose logger name: task_{task_id}_{exec_id}
                logger_name = f"task_{found_task._id}_{execution._id}"
                exec_logs = get_logs(logger_name=logger_name)
                
                exec_info = {
                    "execution_id": execution._id,
                    "started_at": getattr(execution, "timestamp_created", 0),
                    "status": getattr(execution, "status", "unknown"),
                    "logs": exec_logs if exec_logs else [],
                }
                if hasattr(execution, "result") and execution.result:
                    exec_info["result"] = str(execution.result)
                execution_data.append(exec_info)

            return json.dumps(
                {
                    "success": True,
                    "task_id": found_task._id,
                    "task_name": found_task.name,
                    "status": getattr(found_task, "status", "unknown"),
                    "executions": execution_data,
                    "total_executions": len(executions),
                },
                indent=2,
            )
        else:
            return json.dumps(
                {"success": False, "error": f"Task not found: {task_id}"}, indent=2
            )

    except Exception as e:
        logger.error(f"Error getting task logs: {traceback.format_exc()}")
        return json.dumps({"success": False, "error": traceback.format_exc()}, indent=2)


@query
def get_task_logs_by_name(
    task_name: str,
    from_entry: nat = 0,
    max_entries: nat = 100,
) -> str:
    """
    Get in-memory logs for a specific task by task name.
    
    Fetches logs from all executions of the task using kybra-simple-logging.
    
    Args:
        task_name: Exact task name or partial task ID
        from_entry: Start index for pagination (default: 0)
        max_entries: Maximum number of log entries to return (default: 100, max: 1000)
    
    Returns:
        JSON string with array of log entries from all executions
    """
    from ggg.task import Task
    import json
    
    try:
        # Try to find task by name or partial ID
        found_task = None
        for task in Task.instances():
            if task.name == task_name or str(task._id).startswith(task_name) or str(task._id) == task_name:
                found_task = task
                break
        
        if not found_task:
            return json.dumps([])
        
        # Limit max_entries to prevent too large responses
        safe_max_entries = min(int(max_entries), 1000)
        
        # Collect logs from all executions
        all_logs = []
        executions = list(found_task.executions) if hasattr(found_task, "executions") else []
        
        for execution in executions:
            # Compose logger name: task_{task_id}_{exec_id}
            logger_name = f"task_{found_task._id}_{execution._id}"
            exec_logs = get_logs(logger_name=logger_name)
            if exec_logs:
                all_logs.extend(exec_logs)
        
        # Apply pagination
        start_idx = int(from_entry) if from_entry else 0
        end_idx = start_idx + safe_max_entries
        paginated_logs = all_logs[start_idx:end_idx]
        
        return json.dumps(paginated_logs) if paginated_logs else json.dumps([])
    
    except Exception as e:
        logger.error(f"Error getting task logs by name: {e}")
        return f"Error retrieving logs: {str(e)}"


downloaded_content: dict = {}


@update
def test_mixed_sync_async_task() -> void:
    try:
        """Test function to verify TaskManager can handle mixed sync/async steps in sequence"""
        ic.print("Setting up mixed sync/async task test")

        url = "https://raw.githubusercontent.com/smart-social-contracts/realms/3d863b4d8a7d8c72490537d44a4e05363752ae3c/src/realm_backend/codex.py"

        # Step 1: Async HTTP download with codex
        download_codex = Codex()
        download_codex.code = f"""
from main import download_file_from_url

def async_task():
    ic.print("=== DOWNLOAD STEP ===")
    ic.print("Downloading file from URL: {url}")
    url = "{url}"
    result = yield download_file_from_url(url)
    ic.print(f"Download result for {{url}}: {{result[0]}}")
    return result
""".strip()
        async_call = Call(codex=download_codex)
        step1 = TaskStep(call=async_call, run_next_after=10)

        # Step 2: Sync verification step
        codex = Codex()
        codex.code = f"""
from main import downloaded_content
from ggg import Codex

content = downloaded_content['{url}']

codex = Codex["the_code"]
if not codex:
    codex = Codex()
    codex.name = "the_code"
codex.code = content

ic.print("=== VERIFICATION STEP ===")
ic.print(f"Downloaded content length: {{len(content)}}")
if len(content) > 0:
    ic.print("✅ SUCCESS: File was downloaded successfully!")
    if "def " in content:
        ic.print("✅ SUCCESS: Content contains Python code (found 'def')")
    else:
        ic.print("❌ WARNING: Content doesn't appear to be Python code")
    preview = content[:100].replace("\\n", " ")
    ic.print("Content preview: " + preview + "...")
else:
    ic.print("❌ FAILURE: No content was downloaded!")
ic.print("=== VERIFICATION COMPLETE ===")""".strip()
        sync_call = Call(codex=codex)
        step2 = TaskStep(call=sync_call)

        task = Task(name="test_mixed_steps", steps=[step1, step2])
        schedule = TaskSchedule(
            name=f"test_schedule_{ic.time()}", task=task, run_at=0, repeat_every=30
        )
        task.schedules = [schedule]

        task_manager = TaskManager()
        task_manager.add_task(task)
        task_manager.run()

        ic.print("Mixed sync/async task test initiated...")
    except Exception as e:
        logger.error(traceback.format_exc())


@update
def create_scheduled_task(
    name: str, code: str, repeat_every: nat, run_after: nat = 5
) -> str:
    """
    Create a new scheduled task from Python code.

    Args:
        name: Task name
        code: Python code to execute (base64 encoded)
        repeat_every: Interval in seconds (0 for one-time execution)
        run_after: Delay before first execution in seconds (default: 5)

    Returns JSON with:
    - success: Boolean indicating success
    - task_id: The created task ID
    - schedule_id: The schedule ID
    - error: Error message if failed
    """
    try:

        from core.task_manager import TaskManager
        from ggg import Call, Task, TaskStep
        from ggg.task_schedule import TaskSchedule
        
        # Decode the base64 encoded code
        decoded_code = base64.b64decode(code).decode("utf-8")

        # Create codex
        temp_name = f"_scheduled_{name}_{int(ic.time())}"
        codex = Codex(name=temp_name, code=decoded_code)

        # Auto-detect if code is async
        is_async = "yield" in decoded_code or "async_task" in decoded_code
        logger.info(f"Auto-detected is_async={is_async} for task {name}")

        # Create call and step
        call = Call(codex=codex)
        step = TaskStep(call=call, run_next_after=0)

        # Create task (using TaskManager Task, not GGG Task)
        task = Task(name=name, steps=[step])

        # Create schedule
        current_time = int(ic.time() / 1_000_000_000)
        schedule = TaskSchedule(
            name=f"schedule_{name}",
            task=task,
            # run_at=current_time + run_after,
            run_at=0,
            repeat_every=repeat_every,
            last_run_at=0,
            disabled=False,
        )

        # Register with TaskManager
        manager = TaskManager()
        manager.add_task(task)

        # Extract serializable data
        task_id = str(task._id)
        task_name = str(task.name)
        schedule_id = str(schedule._id)
        run_at = int(schedule.run_at)
        repeat_every = int(schedule.repeat_every)

        logger.info(f"Created scheduled task: {task_name} (ID: {task_id})")

        TaskManager().run()

        return json.dumps(
            {
                "success": True,
                "task_id": task_id,
                "task_name": task_name,
                "schedule_id": schedule_id,
                "run_at": run_at,
                "repeat_every": repeat_every,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error creating scheduled task: {e}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@update
def create_multi_step_scheduled_task(
    name: str,
    steps_config: str,
    repeat_every: nat,
    run_after: nat = 5,
) -> str:
    """
    Create a multi-step scheduled task from multiple code snippets.

    Args:
        name: Task name
        steps_config: JSON array of step configurations:
            [
                {
                    "code": "<base64-encoded-code>",
                    "run_next_after": seconds (optional, default 0)
                },
                ...
            ]
        repeat_every: Interval in seconds (0 for one-time execution)
        run_after: Delay before first execution in seconds (default: 5)

    Returns JSON with:
    - success: Boolean indicating success
    - task_id: The created task ID
    - task_name: The task name
    - schedule_id: The schedule ID
    - steps_count: Number of steps in the task
    - run_at: Scheduled execution time
    - repeat_every: Repeat interval
    - error: Error message if failed

    Note: is_async is automatically detected based on code content
          (presence of 'yield' or 'async_task')
    """
    try:
        # Parse steps configuration
        steps_data = json.loads(steps_config)

        if not steps_data or len(steps_data) == 0:
            raise ValueError("At least one step is required")

        # Create TaskStep objects
        task_steps = []
        for idx, step_config in enumerate(steps_data):
            # Decode base64 code
            try:
                decoded_code = base64.b64decode(step_config["code"]).decode("utf-8")
            except Exception as e:
                raise ValueError(f"Invalid base64 code in step {idx}: {e}")

            # Create codex for this step
            codex_name = f"_{name}_step_{idx}_{int(ic.time())}"
            codex = Codex(name=codex_name, code=decoded_code)

            # Create call
            call = Call(codex=codex)

            # Get run_next_after delay (default to 0)
            run_next_after = step_config.get("run_next_after", 0)

            # Create step
            step = TaskStep(call=call, run_next_after=run_next_after)
            task_steps.append(step)

            logger.info(
                f"Created step {idx}: codex={codex_name}, "
                f"run_next_after={run_next_after}s"
            )

        # Create task with multiple steps
        task = Task(name=name, steps=task_steps)

        # Create schedule
        current_time = int(ic.time() / 1_000_000_000)
        schedule = TaskSchedule(
            name=f"schedule_{name}",
            task=task,
            run_at=0,
            repeat_every=repeat_every,
            last_run_at=0,
            disabled=False,
        )

        # Register with TaskManager
        manager = TaskManager()
        manager.add_task(task)

        logger.info(
            f"Created multi-step task: {name} (ID: {task._id}) "
            f"with {len(task_steps)} steps"
        )

        # Trigger task manager to process the schedule
        TaskManager().run()

        return json.dumps(
            {
                "success": True,
                "task_id": str(task._id),
                "task_name": str(task.name),
                "schedule_id": str(schedule._id),
                "steps_count": len(task_steps),
                "run_at": int(schedule.run_at),
                "repeat_every": int(schedule.repeat_every),
            },
            indent=2,
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in steps_config: {e}")
        return json.dumps({"success": False, "error": f"Invalid JSON: {str(e)}"})
    except Exception as e:
        logger.error(f"Error creating multi-step task: {e}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@update
def register_realm_with_registry(
    registry_canister_id: text,
    realm_name: text,
    frontend_url: text = "",
    logo_url: text = "",
    backend_url: text = "",
) -> Async[text]:
    """
    Register this realm with the central registry.

    Makes an inter-canister call to the realm_registry_backend to register
    this realm. The registry uses ic.caller() (this backend's canister ID)
    as the unique realm ID, preventing duplicates via upsert logic.

    Args:
        registry_canister_id: Canister ID of the realm registry backend
        realm_name: Display name for this realm
        frontend_url: Frontend canister URL (optional)
        logo_url: Logo URL (optional)
        backend_url: Backend canister URL (optional)

    Returns:
        JSON string with success status and message
    """
    try:
        result = yield register_realm(
            registry_canister_id, realm_name, frontend_url, logo_url, backend_url
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in register_realm_with_registry: {e}")
        logger.error(traceback.format_exc())
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@query
def get_realm_registry_info() -> text:
    """
    Get information about registries this realm is registered with.

    Returns:
        JSON string with list of registries
    """
    try:
        result = get_registry_info()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_realm_registry_info: {e}")
        return json.dumps(
            {"success": False, "error": str(e), "registries": []}, indent=2
        )


@update
def reload_entity_method_overrides() -> str:
    """
    Admin function to reload entity method overrides from Realm manifest.
    This should be called after importing realm data that includes codexes and manifest_data.
    """
    logger.info("🔄 reload_entity_method_overrides() called")
    try:
        from ggg import Codex, Realm
        import ggg
        import json
        
        logger.info("📜 Looking for Codex['manifest']...")
        realm_manifest = Codex["manifest"]
        if not realm_manifest:
            logger.error("❌ No Codex['manifest'] found")
            return json.dumps({"success": False, "error": "No realm manifest found"})
        
        logger.info(f"✅ Found manifest codex (code length: {len(str(realm_manifest.code))} chars)")
        manifest = json.loads(str(realm_manifest.code))
        overrides = manifest.get("entity_method_overrides", [])
        logger.info(f"📋 Found {len(overrides)} override(s) in manifest")
        
        loaded_overrides = []
        for i, o in enumerate(overrides):
            logger.info(f"  [{i+1}/{len(overrides)}] Processing: {o.get('entity', '?')}.{o.get('method', '?')}()")
            try:
                if not all([o.get("entity"), o.get("method"), o.get("implementation")]):
                    logger.warning(f"    ⚠️ Skipping - missing required fields (entity/method/implementation)")
                    continue
                    
                entity_class = getattr(ggg, o["entity"], None)
                if not entity_class:
                    logger.warning(f"    ⚠️ Skipping - entity class '{o['entity']}' not found in ggg")
                    continue
                    
                parts = o["implementation"].split(".")
                if len(parts) != 3 or parts[0] != "Codex":
                    logger.warning(f"    ⚠️ Skipping - invalid implementation format: {o['implementation']} (expected Codex.name.function)")
                    continue
                
                codex_name = parts[1]
                func_name = parts[2]
                logger.info(f"    🔍 Looking for Codex['{codex_name}']...")
                target_codex = Codex[codex_name]
                if not target_codex:
                    logger.warning(f"    ⚠️ Skipping - Codex['{codex_name}'] not found")
                    continue
                
                logger.info(f"    ✅ Found codex '{codex_name}' (code length: {len(str(target_codex.code))} chars)")
                ns = {}
                exec(str(target_codex.code), ns)
                func = ns.get(func_name)
                if not func:
                    logger.warning(f"    ⚠️ Skipping - function '{func_name}' not found in codex")
                    logger.info(f"    📦 Available names in codex: {list(ns.keys())}")
                    continue
                
                method_type = o.get("type", "method")
                wrapper = classmethod(func) if method_type == "classmethod" else staticmethod(func) if method_type == "staticmethod" else func
                setattr(entity_class, o["method"], wrapper)
                loaded_overrides.append(f"{o['entity']}.{o['method']}() -> {o['implementation']}")
                logger.info(f"    ✅ Successfully loaded {o['entity']}.{o['method']}() [{method_type}] -> {o['implementation']}")
            except Exception as e:
                logger.error(f"    ❌ Failed to reload override: {e}")
        
        logger.info(f"🏁 Completed: {len(loaded_overrides)}/{len(overrides)} overrides loaded successfully")
        return json.dumps({"success": True, "loaded_overrides": loaded_overrides}, indent=2)
    except Exception as e:
        logger.error(f"❌ reload_entity_method_overrides failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


# @heartbeat
# def check_scheduled_tasks() -> void:
#     """
#     Heartbeat function that runs automatically to check and execute scheduled tasks.
#     This is called periodically by the Internet Computer to process task schedules.
#     """
#     try:
#         task_manager = TaskManager()
#         task_manager._update_timers()
#     except Exception as e:
#         logger.error(f"Error in heartbeat checking scheduled tasks: {e}")
#         logger.error(traceback.format_exc())
