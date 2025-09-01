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
from kybra import (
    Async,
    CallResult,
    Func,
    Opt,
    Principal,
    Query,
    Record,
    StableBTreeMap,
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
    TimerId,
    Duration
)
from kybra_simple_db import Database
from kybra_simple_logging import get_logger
from ggg import Codex

storage = StableBTreeMap[str, str](memory_id=1, max_key_size=100, max_value_size=3000)
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


@update
def run() -> RealmResponse:
    try:
        logger.info("Executing run")

        # Execute legacy codex
        import codex

        codex.run()

        # Process TaskManager queue (includes scheduled tasks)
        from core.task_manager import run_pending_tasks

        task_results = run_pending_tasks()

        message = f"Run executed successfully. Processed {len(task_results)} tasks."
        logger.info(message)
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                Message=message, Data={"task_results": task_results}
            ),
        )
    except Exception as e:
        logger.error(f"Error running: {str(e)}\n{traceback.format_exc()}")
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

    # import codex
    # codex.run()

    # Create a codex with the tax collection code
    import codex
    
    c = ggg.Codex()
    c.code = """
from ggg import Mandate, User
from kybra_simple_logging import get_logger

logger = get_logger("codex")

def mandate_1_tax_payment():
    # check if citizens have paid their taxes on time
    user_count = User.count()
    logger.info("mandate_1_tax_payment: User.count()" + str(user_count))
    
    if user_count == 0:
        logger.info("No users found, skipping tax payment processing")
        return
    
    # Process tax payments for users
    logger.info("Processing tax payments for users")

def run():
    logger.info("run inside codex")
    mandate_1_tax_payment()

run()
"""

    t = ggg.Task()
    t.codex = c
    t.name = "codex"
    t.metadata = "codex"

    from core.task_manager import task_manager

    # task_manager.set_timer_interval(t, 1000)
    task_execution = task_manager.run_now(t)
    logger.info(f"Task execution result: {task_execution}")


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
    success, message = yield download_code_from_url(c.url, c.checksum, c)
    logger.info("Success: " + str(success))
    logger.info("Downloaded code: " + message)



def download_code_from_url(
    url: str, expected_checksum: Optional[str] = None, codex: Codex = None
) -> Async[Tuple[bool, str]]:
    """
    Download code from a URL and verify its checksum.

    Args:
        url: The URL to download from
        expected_checksum: Optional SHA-256 checksum to verify against (format: "sha256:hash")

    Returns:
        Tuple of (success: bool, result: str)
        - If success=True, result contains the downloaded code
        - If success=False, result contains the error message
    """
    try:
        logger.info(f"Downloading code from URL: {url}")

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
                logger.info(f"Successfully downloaded {len(code_content)} bytes")

                # Verify checksum if provided
                if expected_checksum:
                    is_valid, checksum_error = verify_checksum(
                        code_content, expected_checksum
                    )
                    if not is_valid:
                        logger.error(f"Checksum verification failed: {checksum_error}")
                        return False, checksum_error
                    logger.info("Checksum verification passed")

                if codex:
                    codex.code = code_content
                    logger.info("Codex code updated")

                return True, code_content

            except UnicodeDecodeError as e:
                error_msg = f"Failed to decode response as UTF-8: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
            except Exception as e:
                error_msg = f"Error processing response: {str(e)}"
                logger.error(error_msg)
                return False, error_msg

        def handle_error(err: str) -> Tuple[bool, str]:
            error_msg = f"HTTP request failed: {err}"
            logger.error(error_msg)
            return False, error_msg

        return match(http_result, {"Ok": handle_response, "Err": handle_error})

    except Exception as e:
        error_msg = f"Unexpected error downloading code: {str(e)}"
        logger.error(error_msg)
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


# TaskManager API endpoints
@update
def run_task(task_id: str) -> RealmResponse:
    """Add a specific task to the execution queue"""
    try:
        from core.task_manager import execute_task

        success = execute_task(task_id)
        if success:
            return RealmResponse(
                success=True,
                data=RealmResponseData(Message=f"Task {task_id} added to queue"),
            )
        else:
            return RealmResponse(
                success=False,
                data=RealmResponseData(Error=f"Failed to add task {task_id} to queue"),
            )
    except Exception as e:
        logger.error(
            f"Error running task {task_id}: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@update
def process_task_queue() -> RealmResponse:
    """Process all pending tasks in the TaskManager queue"""
    try:
        from core.task_manager import run_pending_tasks

        results = run_pending_tasks()
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                Message=f"Processed {len(results)} tasks", Data=results
            ),
        )
    except Exception as e:
        logger.error(f"Error processing task queue: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@update
def clear_task_queue() -> RealmResponse:
    """Clear all pending tasks from the queue"""
    try:
        from core.task_manager import task_manager

        cleared_count = task_manager.clear_queue()
        return RealmResponse(
            success=True,
            data=RealmResponseData(Message=f"Cleared {cleared_count} tasks from queue"),
        )
    except Exception as e:
        logger.error(f"Error clearing task queue: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@update
def cancel_task(task_id: str) -> RealmResponse:
    """Cancel a pending task by removing it from the queue"""
    try:
        from core.task_manager import task_manager

        success = task_manager.cancel_task(task_id)
        if success:
            return RealmResponse(
                success=True,
                data=RealmResponseData(
                    Message=f"Task {task_id} cancelled successfully"
                ),
            )
        else:
            return RealmResponse(
                success=False,
                data=RealmResponseData(Error=f"Task {task_id} not found in queue"),
            )
    except Exception as e:
        logger.error(
            f"Error cancelling task {task_id}: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@update
def create_task_timer(task_id: str, delay_seconds: nat) -> RealmResponse:
    """Create a one-time timer to execute a task after delay_seconds"""
    try:
        from core.task_manager import create_task_timer

        success = create_task_timer(task_id, int(delay_seconds))
        if success:
            return RealmResponse(
                success=True,
                data=RealmResponseData(
                    Message=f"Timer created for task {task_id} with {delay_seconds}s delay"
                ),
            )
        else:
            return RealmResponse(
                success=False,
                data=RealmResponseData(
                    Error=f"Failed to create timer for task {task_id}"
                ),
            )
    except Exception as e:
        logger.error(
            f"Error creating timer for task {task_id}: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@update
def create_task_interval_timer(task_id: str, interval_seconds: nat) -> RealmResponse:
    """Create a recurring timer to execute a task every interval_seconds"""
    try:
        from core.task_manager import create_task_interval_timer

        success = create_task_interval_timer(task_id, int(interval_seconds))
        if success:
            return RealmResponse(
                success=True,
                data=RealmResponseData(
                    Message=f"Interval timer created for task {task_id} with {interval_seconds}s interval"
                ),
            )
        else:
            return RealmResponse(
                success=False,
                data=RealmResponseData(
                    Error=f"Failed to create interval timer for task {task_id}"
                ),
            )
    except Exception as e:
        logger.error(
            f"Error creating interval timer for task {task_id}: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@update
def cancel_task_timer(task_id: str) -> RealmResponse:
    """Cancel a timer for a specific task"""
    try:
        from core.task_manager import cancel_task_timer

        success = cancel_task_timer(task_id)
        if success:
            return RealmResponse(
                success=True,
                data=RealmResponseData(Message=f"Timer cancelled for task {task_id}"),
            )
        else:
            return RealmResponse(
                success=False,
                data=RealmResponseData(Error=f"No timer found for task {task_id}"),
            )
    except Exception as e:
        logger.error(
            f"Error cancelling timer for task {task_id}: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_active_timers() -> RealmResponse:
    """Get list of all active timers"""
    try:
        from core.task_manager import get_active_timers

        timers = get_active_timers()
        return RealmResponse(
            success=True,
            data=RealmResponseData(Message="Active timers retrieved", Data=timers),
        )
    except Exception as e:
        logger.error(f"Error getting active timers: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_task_status(task_id: str) -> RealmResponse:
    """Get the execution status of a specific task"""
    try:
        from core.task_manager import get_task_execution_status

        status = get_task_execution_status(task_id)
        if status:
            return RealmResponse(
                success=True,
                data=RealmResponseData(Message=f"Task {task_id} status: {status}"),
            )
        else:
            return RealmResponse(
                success=False,
                data=RealmResponseData(
                    Error=f"Task {task_id} not found or no status available"
                ),
            )
    except Exception as e:
        logger.error(
            f"Error getting task status for {task_id}: {str(e)}\n{traceback.format_exc()}"
        )
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))
