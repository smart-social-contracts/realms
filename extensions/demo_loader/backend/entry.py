import json
import traceback

from kybra import Record
from kybra_simple_logging import get_logger

logger = get_logger("demo_loader.entry")

"""

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"base_setup\"}";
  }
)'

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"user_management\", \"batch\": 0}";
  }
)'

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"user_management\", \"batch\": 1}";
  }
)'


dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"financial_services\"}";
  }
)'

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"government_services\"}";
  }
)'

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"transactions\"}";
  }
)'

dfx canister call realm_backend extension_sync_call '(
  record {
    extension_name = "demo_loader";
    function_name = "load";
    args = "{\"step\": \"justice_litigation\"}";
  }
)'

"""


class ResponseDemoLoader(Record):
    data: str


def load(args: str):
    """Load demo data in a modular way, creating entities in chunks to avoid cycle limits."""
    try:
        args = args or "{}"
        args = json.loads(args)
        step = args.get("step")
        batch = args.get("batch")

        if not step:
            return "Error: 'step' parameter is required. Valid steps are: base_setup, user_management, financial_services, government_services, transactions, governance_activity, justice_litigation"

        logger.info(f"Starting modular demo data loading for step: {step}")

        # Step 1: Base setup
        if step == "base_setup":
            logger.info("Step 1: Running base setup")
            from .base_setup import run as run_base_setup

            return run_base_setup()

        # Step 2: User management
        elif step == "user_management":
            logger.info("Step 2: Creating users and humans")
            from .user_management import run as run_user_management

            return run_user_management(batch)

        # Step 3: Financial services
        elif step == "financial_services":
            logger.info("Step 3: Creating financial services")
            from .financial_services import run as run_financial_services

            return run_financial_services()

        # Step 4: Government services
        elif step == "government_services":
            logger.info("Step 4: Creating government services")
            from .government_services import run as run_government_services

            return run_government_services()

        # Step 5: Transactions
        elif step == "transactions":
            logger.info("Step 5: Creating transactions")
            from .transactions import run as run_transactions

            return run_transactions()

        # Step 6: Governance Activity (NEW)
        elif step == "governance_activity":
            logger.info("Step 6: Creating governance proposals and votes")
            from .governance_activity import run as run_governance_activity

            return run_governance_activity(batch)

        # Step 7: Justice Litigation
        elif step == "justice_litigation":
            logger.info("Step 7: Creating justice litigation cases")
            from .justice_litigation import run as run_justice_litigation

            return run_justice_litigation(batch)

        else:
            return f"Error: Invalid step '{step}'. Valid steps are: base_setup, user_management, financial_services, government_services, transactions, governance_activity, justice_litigation"

    except Exception as e:
        error_msg = f"Error loading demo data: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg
