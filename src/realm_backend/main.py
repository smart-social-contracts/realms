import json
import traceback

import api
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

# from api.extensions import list_extensions
from api.status import get_status
from api.user import user_get, user_register
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
    UserRegisterRecord,
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
    Tuple,
    Variant,
    Vec,
    blob,
    ic,
    init,
    nat,
    query,
    text,
    update,
    void,
)
from kybra_simple_db import Database
from kybra_simple_logging import get_logger

storage = StableBTreeMap[str, str](memory_id=1, max_key_size=100, max_value_size=2000)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("main")


class HttpRequest(Record):
    method: str
    url: str
    headers: Vec["Header"]
    body: blob


class HttpResponse(Record):
    status_code: nat
    headers: Vec["Header"]
    body: blob
    streaming_strategy: Opt["StreamingStrategy"]
    upgrade: Opt[bool]


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
def register_user(principal: Principal) -> RealmResponse:
    try:
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UserRegister=UserRegisterRecord(
                    principal=Principal.from_str(
                        user_register(principal.to_str())["principal"]
                    )
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_user(principal: Principal) -> RealmResponse:
    try:
        user_data = user_get(principal.to_str())
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                UserGet=UserGetRecord(
                    principal=Principal.from_str(user_data["principal"])
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


# New GGG API endpoints


@query
def get_users() -> RealmResponse:
    try:
        users_data = list_users()
        # Convert dictionary to JSON string
        users_json = [json.dumps(user) for user in users_data["users"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(UsersList=UsersListRecord(users=users_json)),
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_mandates() -> RealmResponse:
    try:
        mandates_data = list_mandates()
        # Convert dictionary to JSON string
        mandates_json = [json.dumps(mandate) for mandate in mandates_data["mandates"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                MandatesList=MandatesListRecord(mandates=mandates_json)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing mandates: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_tasks() -> RealmResponse:
    try:
        tasks_data = list_tasks()
        # Convert dictionary to JSON string
        tasks_json = [json.dumps(task) for task in tasks_data["tasks"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(TasksList=TasksListRecord(tasks=tasks_json)),
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
            total_pages=result["total_pages"]
        )
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                TransfersList=TransfersListRecord(
                    transfers=transfers_json,
                    pagination=pagination
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing transfers: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_instruments() -> RealmResponse:
    try:
        instruments_data = list_instruments()
        # Convert dictionary to JSON string
        instruments_json = [
            json.dumps(instrument) for instrument in instruments_data["instruments"]
        ]
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                InstrumentsList=InstrumentsListRecord(instruments=instruments_json)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing instruments: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_codexes() -> RealmResponse:
    try:
        codexes_data = list_codexes()
        # Convert dictionary to JSON string
        codexes_json = [json.dumps(codex) for codex in codexes_data["codexes"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(CodexesList=CodexesListRecord(codexes=codexes_json)),
        )
    except Exception as e:
        logger.error(f"Error listing codexes: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_organizations() -> RealmResponse:
    try:
        organizations_data = list_organizations()
        # Convert dictionary to JSON string
        organizations_json = [
            json.dumps(org) for org in organizations_data["organizations"]
        ]
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                OrganizationsList=OrganizationsListRecord(
                    organizations=organizations_json
                )
            ),
        )
    except Exception as e:
        logger.error(f"Error listing organizations: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_disputes() -> RealmResponse:
    try:
        disputes_data = list_disputes()
        # Convert dictionary to JSON string
        disputes_json = [json.dumps(dispute) for dispute in disputes_data["disputes"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                DisputesList=DisputesListRecord(disputes=disputes_json)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing disputes: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_licenses() -> RealmResponse:
    try:
        licenses_data = list_licenses()
        # Convert dictionary to JSON string
        licenses_json = [json.dumps(license) for license in licenses_data["licenses"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                LicensesList=LicensesListRecord(licenses=licenses_json)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing licenses: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_realms() -> RealmResponse:
    try:
        realms_data = list_realms()
        # Convert dictionary to JSON string
        realms_json = [json.dumps(realm) for realm in realms_data["realms"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(RealmsList=RealmsListRecord(realms=realms_json)),
        )
    except Exception as e:
        logger.error(f"Error listing realms: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_trades() -> RealmResponse:
    try:
        trades_data = list_trades()
        # Convert dictionary to JSON string
        trades_json = [json.dumps(trade) for trade in trades_data["trades"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(TradesList=TradesListRecord(trades=trades_json)),
        )
    except Exception as e:
        logger.error(f"Error listing trades: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_proposals() -> RealmResponse:
    try:
        proposals_data = list_proposals()
        # Convert dictionary to JSON string
        proposals_json = [
            json.dumps(proposal) for proposal in proposals_data["proposals"]
        ]
        return RealmResponse(
            success=True,
            data=RealmResponseData(
                ProposalsList=ProposalsListRecord(proposals=proposals_json)
            ),
        )
    except Exception as e:
        logger.error(f"Error listing proposals: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@query
def get_votes() -> RealmResponse:
    try:
        votes_data = list_votes()
        # Convert dictionary to JSON string
        votes_json = [json.dumps(vote) for vote in votes_data["votes"]]
        return RealmResponse(
            success=True,
            data=RealmResponseData(VotesList=VotesListRecord(votes=votes_json)),
        )
    except Exception as e:
        logger.error(f"Error listing votes: {str(e)}\n{traceback.format_exc()}")
        return RealmResponse(success=False, data=RealmResponseData(Error=str(e)))


@init
def init_() -> void:
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
