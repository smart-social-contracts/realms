import json
import traceback
from typing import Optional, Tuple

import api
from api.extensions import list_extensions
from api.ggg_entities import (
    list_codexes,
    list_disputes,
    list_instruments,
    list_licenses,
    list_mandates,
    list_organizations,
    list_proposals,
    list_realms,
    list_tasks,
    list_trades,
    list_transfers,
    list_users,
    list_votes,
)
from api.status import get_status
from api.user import user_get, user_register, user_update_profile_picture
from core.candid_types_realm import (
    CodexesListRecord,
    DisputesListRecord,
    ExtensionCallArgs,
    ExtensionCallResponse,
    InstrumentsListRecord,
    LicensesListRecord,
    MandatesListRecord,
    OrganizationsListRecord,
    PaginationInfo,
    ProposalsListRecord,
    RealmResponse,
    RealmResponseData,
    RealmsListRecord,
    StatusRecord,
    TasksListRecord,
    TradesListRecord,
    TransfersListRecord,
    UserGetRecord,
    UsersListRecord,
    VotesListRecord,
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
            success=True, data=RealmResponseData(Status=StatusRecord(**get_status()))
        )
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


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
                UserGet=UserGetRecord(
                    principal=Principal.from_str(user["principal"]),
                    profiles=profiles,
                    profile_picture_url=user.get("profile_picture_url", ""),
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


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
                success=False, data=RealmResponseData(Error=user["error"])
            )

        profiles = Vec[text]()
        if "profiles" in user and user["profiles"]:
            for p in user["profiles"]:
                profiles.append(p)
        logger.info(f"Profiles: {profiles}")
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UserGet=UserGetRecord(
                    principal=Principal.from_str(user["principal"]),
                    profiles=profiles,
                    profile_picture_url=user["profile_picture_url"],
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@update
def update_my_profile_picture(profile_picture_url: str) -> RealmResponse:
    try:
        result = user_update_profile_picture(ic.caller().to_str(), profile_picture_url)
        if not result["success"]:
            return RealmResponse(
                success=False, data=RealmResponseData(Error=result["error"])
            )

        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UserGet=UserGetRecord(
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
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


# New GGG API endpoints


@query
def get_users(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        logger.info(f"Listing users for page {page_num} with page size {page_size}")
        result = list_users(page_num=page_num, page_size=page_size)
        users = result["items"]
        users_json = [json.dumps(user.to_dict()) for user in users]
        pagination = PaginationInfo(
            page_num=result["page_num"],
            page_size=result["page_size"],
            total_items_count=result["total_items_count"],
            total_pages=result["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UsersList=UsersListRecord(users=users_json, pagination=pagination)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_mandates(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        mandates_data = list_mandates(page_num=page_num, page_size=page_size)
        mandates_json = [
            json.dumps(mandate.to_dict()) for mandate in mandates_data["items"]
        ]
        pagination = PaginationInfo(
            page_num=mandates_data["page_num"],
            page_size=mandates_data["page_size"],
            total_items_count=mandates_data["total_items_count"],
            total_pages=mandates_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                MandatesList=MandatesListRecord(
                    mandates=mandates_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing mandates: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_tasks(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        tasks_data = list_tasks(page_num=page_num, page_size=page_size)
        tasks_json = [json.dumps(task.to_dict()) for task in tasks_data["items"]]
        pagination = PaginationInfo(
            page_num=tasks_data["page_num"],
            page_size=tasks_data["page_size"],
            total_items_count=tasks_data["total_items_count"],
            total_pages=tasks_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                TasksList=TasksListRecord(tasks=tasks_json, pagination=pagination)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_transfers(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        logger.info(f"Listing transfers for page {page_num} with page size {page_size}")
        result = list_transfers(page_num=page_num, page_size=page_size)
        transfers = result["items"]
        transfers_json = [json.dumps(transfer.to_dict()) for transfer in transfers]
        pagination = PaginationInfo(
            page_num=result["page_num"],
            page_size=result["page_size"],
            total_items_count=result["total_items_count"],
            total_pages=result["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                TransfersList=TransfersListRecord(
                    transfers=transfers_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing transfers: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_instruments(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        instruments_data = list_instruments(page_num=page_num, page_size=page_size)
        instruments_json = [
            json.dumps(instrument.to_dict()) for instrument in instruments_data["items"]
        ]
        pagination = PaginationInfo(
            page_num=instruments_data["page_num"],
            page_size=instruments_data["page_size"],
            total_items_count=instruments_data["total_items_count"],
            total_pages=instruments_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                InstrumentsList=InstrumentsListRecord(
                    instruments=instruments_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing instruments: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_codexes(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        codexes_data = list_codexes(page_num=page_num, page_size=page_size)
        codexes_json = [json.dumps(codex.to_dict()) for codex in codexes_data["items"]]
        pagination = PaginationInfo(
            page_num=codexes_data["page_num"],
            page_size=codexes_data["page_size"],
            total_items_count=codexes_data["total_items_count"],
            total_pages=codexes_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                CodexesList=CodexesListRecord(
                    codexes=codexes_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing codexes: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_organizations(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        organizations_data = list_organizations(page_num=page_num, page_size=page_size)
        organizations_json = [
            json.dumps(org.to_dict()) for org in organizations_data["items"]
        ]
        pagination = PaginationInfo(
            page_num=organizations_data["page_num"],
            page_size=organizations_data["page_size"],
            total_items_count=organizations_data["total_items_count"],
            total_pages=organizations_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                OrganizationsList=OrganizationsListRecord(
                    organizations=organizations_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_disputes(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        disputes_data = list_disputes(page_num=page_num, page_size=page_size)
        disputes_json = [
            json.dumps(dispute.to_dict()) for dispute in disputes_data["items"]
        ]
        pagination = PaginationInfo(
            page_num=disputes_data["page_num"],
            page_size=disputes_data["page_size"],
            total_items_count=disputes_data["total_items_count"],
            total_pages=disputes_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                DisputesList=DisputesListRecord(
                    disputes=disputes_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing disputes: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_licenses(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        licenses_data = list_licenses(page_num=page_num, page_size=page_size)
        licenses_json = [
            json.dumps(license.to_dict()) for license in licenses_data["items"]
        ]
        pagination = PaginationInfo(
            page_num=licenses_data["page_num"],
            page_size=licenses_data["page_size"],
            total_items_count=licenses_data["total_items_count"],
            total_pages=licenses_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                LicensesList=LicensesListRecord(
                    licenses=licenses_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing licenses: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_realms(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        realms_data = list_realms(page_num=page_num, page_size=page_size)
        realms_json = [json.dumps(realm.to_dict()) for realm in realms_data["items"]]
        pagination = PaginationInfo(
            page_num=realms_data["page_num"],
            page_size=realms_data["page_size"],
            total_items_count=realms_data["total_items_count"],
            total_pages=realms_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                RealmsList=RealmsListRecord(realms=realms_json, pagination=pagination)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing realms: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_trades(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        trades_data = list_trades(page_num=page_num, page_size=page_size)
        trades_json = [json.dumps(trade.to_dict()) for trade in trades_data["items"]]
        pagination = PaginationInfo(
            page_num=trades_data["page_num"],
            page_size=trades_data["page_size"],
            total_items_count=trades_data["total_items_count"],
            total_pages=trades_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                TradesList=TradesListRecord(trades=trades_json, pagination=pagination)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing trades: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_proposals(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        proposals_data = list_proposals(page_num=page_num, page_size=page_size)
        proposals_json = [
            json.dumps(proposal.to_dict()) for proposal in proposals_data["items"]
        ]
        pagination = PaginationInfo(
            page_num=proposals_data["page_num"],
            page_size=proposals_data["page_size"],
            total_items_count=proposals_data["total_items_count"],
            total_pages=proposals_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                ProposalsList=ProposalsListRecord(
                    proposals=proposals_json, pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing proposals: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_votes(page_num: nat, page_size: nat) -> RealmResponse:
    try:
        votes_data = list_votes(page_num=page_num, page_size=page_size)
        votes_json = [json.dumps(vote.to_dict()) for vote in votes_data["items"]]
        pagination = PaginationInfo(
            page_num=votes_data["page_num"],
            page_size=votes_data["page_size"],
            total_items_count=votes_data["total_items_count"],
            total_pages=votes_data["total_pages"],
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                VotesList=VotesListRecord(votes=votes_json, pagination=pagination)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing votes: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


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
        logger.info(
            f"Sync calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        extension_result = api.extensions.extension_sync_call(
            args["extension_name"], args["function_name"], args["args"]
        )

        logger.info(
            f"Got extension result from {args['extension_name']} function {args['function_name']}: {extension_result}, type: {type(extension_result)}"
        )

        return ExtensionCallResponse(success=True, response=str(extension_result))

    except Exception as e:
        logger.error(f"Error calling extension: {str(e)}\n{traceback.format_exc()}")
        return ExtensionCallResponse(success=False, response=str(e))


@update
def extension_async_call(args: ExtensionCallArgs) -> Async[ExtensionCallResponse]:
    try:
        logger.info(
            f"Async calling extension '{args['extension_name']}' entry point '{args['function_name']}' with args {args['args']}"
        )

        extension_coroutine = api.extensions.extension_async_call(
            args["extension_name"], args["function_name"], args["args"]
        )
        extension_result = yield extension_coroutine

        logger.info(
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


@query
def transform_response(args: HttpTransformArgs) -> HttpResponse:
    """Transform function for HTTP responses from extensions"""
    logger.info("🔄 Transforming HTTP response")
    http_response = args["response"]
    logger.info(f"📊 Original response status: {http_response['status']}")
    logger.info(f"📄 Response body size: {len(http_response['body'])} bytes")
    logger.info("🧹 Clearing response headers for security")
    http_response["headers"] = []
    return http_response


@query
def http_transform(args: HttpTransformArgs) -> HttpResponse:
    """Transform function for HTTP requests - removes headers for consensus"""
    http_response = args["response"]
    http_response["headers"] = []
    return http_response


@update
def set_timer(delay: Duration) -> TimerId:
    ic.call_self("timer_callback")
    return ic.set_timer(delay, timer_callback)


def timer_callback():
    ic.print("timer_callback")


@update
def fire_download(codex_id: str) -> str:
    logger.info("Firing download for codex: " + codex_id)
    ic.set_timer(1, lambda: run_download)


@update
async def run_download() -> Async[None]:
    codex_id = "test"
    logger.info("Downloading code for codex: " + codex_id)
    c = Codex[codex_id]
    success, message = yield download_file_from_url(c.url)
    logger.info("Success: " + str(success))
    logger.info("Downloaded code: " + message)


@update
def download_file_from_url(url: str) -> Async[Tuple[bool, str]]:
    """
    Download file from a URL.

    Returns:
        Tuple of (success: bool, result: str)
        - If success=True, result contains the downloaded file content
        - If success=False, result contains the error message
    """

    try:
        ic.print(f"Downloading code from URL: {url}")

        # Make HTTP request to download the code
        http_result: CallResult[HttpResponse] = yield management_canister.http_request(
            {
                "url": url,
                "max_response_bytes": 1024 * 1024,  # 1MB limit for security
                "method": {"get": None},
                "headers": [
                    {"name": "User-Agent", "value": "Realms-Codex-Downloader/1.0"}
                ],
                "body": None,
                "transform": {
                    "function": (ic.id(), "http_transform"),
                    "context": bytes(),
                },
            }
        ).with_cycles(15_000_000_000)

        def handle_response(response: HttpResponse) -> Tuple[bool, str]:
            try:
                # Decode the response body
                code_content = response["body"].decode("utf-8")
                ic.print(f"Successfully downloaded {len(code_content)} bytes")

                downloaded_content[url] = code_content
                return True, code_content

            except UnicodeDecodeError as e:
                error_msg = f"Failed to decode response as UTF-8: {str(e)}"
                ic.print(error_msg)
                return False, error_msg
            except Exception as e:
                error_msg = f"Error processing response: {str(e)}"
                ic.print(error_msg)
                return False, error_msg

        def handle_error(err: str) -> Tuple[bool, str]:
            error_msg = f"HTTP request failed: {err}"
            ic.print(error_msg)
            return False, error_msg

        return match(http_result, {"Ok": handle_response, "Err": handle_error})

    except Exception as e:
        error_msg = f"Unexpected error downloading code: {str(e)}"
        ic.print(error_msg)
        return False, error_msg


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


@query
def http_request(req: HttpRequest) -> HttpResponse:
    """Handle HTTP requests to the canister. Only for unauthenticated read operations."""

    try:
        method = req["method"]
        url = req["url"]

        logger.info(f"HTTP {method} request to {url}")

        not_found = HttpResponse(
            status_code=404,
            headers=[],
            body=bytes("Not found", "ascii"),
            streaming_strategy=None,
            upgrade=False,
        )

        if method == "GET":
            url_path = url.split("/")

            if url_path[0] != "api":
                return not_found

            if url_path[1] != "v1":
                return not_found

            if url_path[2] == "status":
                return http_request_core(get_status())

            # if url_path[2] == "extensions":
            #     if len(url_path) < 4:
            #         # List all extensions
            #         extensions_list = list_extensions()
            #         return http_request_core({"extensions": extensions_list})

            # Note: We no longer need to handle extension-specific HTTP endpoints here
            # as we have proper canister methods now

        return not_found
    except Exception as e:
        logger.error(f"Error handling HTTP request: {str(e)}\n{traceback.format_exc()}")
        return {
            "status_code": 500,
            "headers": [],
            "body": bytes(traceback.format_exc(), "ascii"),
            "streaming_strategy": None,
            "upgrade": False,
        }


@update
def execute_code(code: str) -> str:
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


from core.task_manager import Call, Task, TaskManager, TaskStep
from ggg.task_schedule import TaskSchedule

downloaded_content: dict = {}


@update
def test_mixed_sync_async_task() -> void:
    try:
        """Test function to verify TaskManager can handle mixed sync/async steps in sequence"""
        ic.print("Setting up mixed sync/async task test")

        url = "https://raw.githubusercontent.com/smart-social-contracts/realms/refs/heads/main/src/realm_backend/codex.py"

        async_call = Call()
        async_call.is_async = True
        async_call._function_def = download_file_from_url
        async_call._function_params = [url]
        step1 = TaskStep(call=async_call, run_next_after=10)

        sync_call = Call()
        sync_call.is_async = False
        codex = Codex()
        codex.code = """
from main import downloaded_content

content = downloaded_content['{url}']

codex = Codex["the_code"]
if not codex:
    codex = Codex()
    codex.name = "the_code"
codex.code = content

ic.print("=== VERIFICATION STEP ===")
ic.print(f"Downloaded content length: len(content)")
if len(content) > 0:
    ic.print("✅ SUCCESS: File was downloaded successfully!")
    if "def " in downloaded_content:
        ic.print("✅ SUCCESS: Content contains Python code (found 'def')")
    else:
        ic.print("❌ WARNING: Content doesn't appear to be Python code")
    preview = downloaded_content[:100].replace("\\n", " ")
    ic.print("Content preview: " + preview + "...")
else:
    ic.print("❌ FAILURE: No content was downloaded!")
ic.print("=== VERIFICATION COMPLETE ===")""".strip()
        sync_call.codex = codex
        step2 = TaskStep(call=sync_call)

        task = Task(name="test_mixed_steps", steps=[step1, step2])
        schedule = TaskSchedule(run_at=0, repeat_every=30)
        task.schedules = [schedule]

        task_manager = TaskManager()
        task_manager.add_task(task)
        task_manager.run()

        ic.print("Mixed sync/async task test initiated...")
    except Exception as e:
        logger.error(traceback.format_exc())
