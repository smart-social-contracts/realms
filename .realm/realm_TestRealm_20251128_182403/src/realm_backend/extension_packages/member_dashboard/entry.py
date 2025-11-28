import json
import re
import traceback
from typing import Any, Dict

from datetime import datetime

from ggg import Invoice, PaymentAccount, Service, User
from kybra import Async, ic
from kybra_simple_logging import get_logger

# Initialize logger
logger = get_logger("member_dashboard")


def _service_to_dict(service: Service) -> Dict[str, Any]:
    """Convert Service entity to dictionary format"""
    return {
        "id": service.service_id,
        "name": service.name,
        "description": service.description,
        "provider": service.provider,
        "status": service.status,
        "due_date": service.due_date,
        "link": service.link,
    }


def _invoice_to_dict(
    invoice: Invoice, include_deposit_address: bool = True
) -> Dict[str, Any]:
    """Convert Invoice entity to dictionary format with optional deposit address."""
    vault_principal = ic.id().to_str()

    result = {
        "id": invoice.id,
        "amount": invoice.amount,
        "currency": getattr(invoice, "currency", "ckBTC") or "ckBTC",
        "due_date": invoice.due_date,
        "status": invoice.status,
        "paid_at": getattr(invoice, "paid_at", None),
        "metadata": invoice.metadata,
    }

    if include_deposit_address:
        result["deposit_address"] = {
            "owner": vault_principal,
            "subaccount": invoice.get_subaccount_hex(),
        }

    return result


def get_dashboard_summary(args: str) -> Async[str]:
    try:
        args = "{}"
        logger.info(f"get_dashboard_summary called with args: {args}")
        params = json.loads(args)
        user_id = params.get("user_id", "anonymous")

        # Get data from database
        all_services = Service.instances()
        all_invoices = Invoice.instances()

        # Filter by user if provided
        if user_id and user_id != "anonymous":
            user_services = [s for s in all_services if s.user and s.user.id == user_id]
            user_invoices = [i for i in all_invoices if i.user and i.user.id == user_id]
        else:
            user_services = list(all_services)
            user_invoices = list(all_invoices)

        # Calculate summary
        services_approaching = len(
            [s for s in user_services if s.status == "Approaching"]
        )
        invoices_overdue = len([i for i in user_invoices if i.status == "Overdue"])

        summary_data = {
            "user_name": user_id,
            "services_count": len(user_services),
            "services_approaching": services_approaching,
            "tax_records": len(user_invoices),
            "tax_overdue": invoices_overdue,
            "personal_data_items": 0,
            "personal_data_updated": 0,
        }

        response = {"success": True, "data": summary_data}

        logger.info(f"get_dashboard_summary successful for user: {user_id}")
        return json.dumps(response)
    except Exception as e:
        logger.error(
            f"Error in get_dashboard_summary: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def get_public_services(args: str) -> Async[str]:
    """
    Get a list of public services for the member.

    Args:
        args (str): JSON string containing user_id

    Returns:
        str: JSON string with public services data
    """
    try:
        logger.info(f"get_public_services called with args: {args}")
        params = json.loads(args)
        user_id = params.get("user_id", "anonymous")

        # Get services from database
        all_services = Service.instances()

        # Filter by user if user_id provided
        if user_id and user_id != "anonymous":
            services = [s for s in all_services if s.user and s.user.id == user_id]
        else:
            services = list(all_services)

        # Convert to dict format
        services_list = [_service_to_dict(s) for s in services]

        response = {
            "success": True,
            "data": {"services": services_list, "total_count": len(services_list)},
        }

        logger.info(f"get_public_services successful for user: {user_id}")
        return json.dumps(response)
    except Exception as e:
        logger.error(
            f"Error in get_public_services: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def get_tax_information(args: str) -> str:
    """
    Get invoice information for the member (tax/billing data).

    Args:
        args (str): JSON string containing user_id

    Returns:
        str: JSON string with invoice information data
    """
    try:
        logger.info(f"get_tax_information called with args: {args}")
        params = json.loads(args) if args else {}
        user_id = params.get("user_id", "anonymous")

        # Get invoices from database
        all_invoices = Invoice.instances()

        # Filter by user if user_id provided
        if user_id and user_id != "anonymous":
            invoices = [i for i in all_invoices if i.user and i.user.id == user_id]
        else:
            invoices = list(all_invoices)

        # Convert to dict format
        invoices_list = [_invoice_to_dict(i) for i in invoices]

        # Calculate summary
        total_paid = sum(
            record["amount"] for record in invoices_list if record["status"] == "Paid"
        )
        total_pending = sum(
            record["amount"]
            for record in invoices_list
            if record["status"] == "Pending"
        )
        total_overdue = sum(
            record["amount"]
            for record in invoices_list
            if record["status"] == "Overdue"
        )

        summary = {
            "total_paid": total_paid,
            "total_pending": total_pending,
            "total_overdue": total_overdue,
            "total_amount": total_paid + total_pending + total_overdue,
        }

        response = {
            "success": True,
            "data": {"tax_records": invoices_list, "summary": summary},
        }

        logger.info(f"get_tax_information successful for user: {user_id}")
        return json.dumps(response)
    except Exception as e:
        logger.error(
            f"Error in get_tax_information: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def get_vault_address(args: str) -> str:
    """
    Get the realm's vault address (canister principal) for deposits.

    Returns:
        JSON string with vault principal ID
    """
    try:
        vault_principal = ic.id().to_str()

        return json.dumps(
            {
                "success": True,
                "data": {
                    "vault_principal": vault_principal,
                    "network": "ICP",
                    "currency": "ckBTC",
                },
            }
        )
    except Exception as e:
        logger.error(f"Error in get_vault_address: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def get_invoice_deposit_address(args: str) -> str:
    """
    Get the deposit address for a specific invoice.

    Args:
        args: JSON string with {"invoice_id": "..."}

    Returns:
        JSON string with owner (vault principal) and subaccount
    """
    try:
        logger.info(f"get_invoice_deposit_address called with args: {args}")
        params = json.loads(args) if args else {}
        invoice_id = params.get("invoice_id")

        if not invoice_id:
            return json.dumps({"success": False, "error": "invoice_id is required"})

        # Find the invoice
        invoice = Invoice[invoice_id]
        if not invoice:
            return json.dumps({"success": False, "error": "Invoice not found"})

        vault_principal = ic.id().to_str()

        return json.dumps(
            {
                "success": True,
                "data": {
                    "owner": vault_principal,
                    "subaccount": invoice.get_subaccount_hex(),
                    "subaccount_bytes": invoice.get_subaccount_list(),
                    "invoice_id": invoice_id,
                    "amount_due": invoice.amount,
                    "currency": getattr(invoice, "currency", "ckBTC") or "ckBTC",
                },
            }
        )
    except Exception as e:
        logger.error(
            f"Error in get_invoice_deposit_address: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def check_invoice_payment(args: str) -> Async[str]:
    """
    Check if an invoice has been paid by querying its subaccount balance.
    If sufficient funds are found, marks the invoice as Paid.

    This is an async function that queries the ckBTC ledger.

    Args:
        args: JSON string with {"invoice_id": "..."}

    Returns:
        JSON string with payment status and balance info
    """
    try:
        logger.info(f"check_invoice_payment called with args: {args}")
        params = json.loads(args) if args else {}
        invoice_id = params.get("invoice_id")

        if not invoice_id:
            return json.dumps({"success": False, "error": "invoice_id is required"})

        # Find the invoice
        invoice = Invoice[invoice_id]
        if not invoice:
            return json.dumps({"success": False, "error": "Invoice not found"})

        if invoice.status == "Paid":
            return json.dumps(
                {
                    "success": True,
                    "data": {
                        "already_paid": True,
                        "invoice_id": invoice_id,
                        "paid_at": getattr(invoice, "paid_at", None),
                    },
                }
            )

        # Import vault utilities for ledger queries
        from extension_packages.vault.vault_lib.entities import Canisters
        from extension_packages.vault.vault_lib.candid_types import ICRCLedger, Account
        from kybra import Principal

        # Get ledger canister
        ledger_canister = Canisters["ckBTC ledger"]
        if not ledger_canister:
            return json.dumps(
                {"success": False, "error": "ckBTC ledger not configured"}
            )

        # Query the invoice's subaccount balance
        vault_principal = ic.id()
        subaccount_bytes = invoice.get_subaccount()

        ledger = ICRCLedger(Principal.from_str(ledger_canister.principal))
        result = yield ledger.icrc1_balance_of(
            Account(owner=vault_principal, subaccount=list(subaccount_bytes))
        )

        # Unwrap the CallResult
        if hasattr(result, "Ok"):
            balance = result.Ok
        else:
            balance = result

        # Convert invoice amount to satoshis (1 ckBTC = 100,000,000 satoshis)
        amount_satoshis = int(invoice.amount * 100_000_000)

        logger.info(
            f"Invoice {invoice_id}: balance={balance}, required={amount_satoshis}"
        )

        if balance >= amount_satoshis:
            # Payment received! Mark invoice as paid
            invoice.status = "Paid"
            invoice.paid_at = datetime.utcnow().isoformat()

            logger.info(f"Invoice {invoice_id} marked as Paid")

            return json.dumps(
                {
                    "success": True,
                    "data": {
                        "paid": True,
                        "invoice_id": invoice_id,
                        "balance_satoshis": balance,
                        "amount_required_satoshis": amount_satoshis,
                        "paid_at": invoice.paid_at,
                    },
                }
            )
        else:
            return json.dumps(
                {
                    "success": True,
                    "data": {
                        "paid": False,
                        "invoice_id": invoice_id,
                        "balance_satoshis": balance,
                        "amount_required_satoshis": amount_satoshis,
                        "shortfall_satoshis": amount_satoshis - balance,
                    },
                }
            )

    except Exception as e:
        logger.error(
            f"Error in check_invoice_payment: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def get_personal_data(args: str) -> str:
    """
    Get personal data for the member.

    Args:
        args (str): JSON string containing user_id

    Returns:
        str: JSON string with personal data
    """
    try:
        args = "{}"
        logger.info(f"get_personal_data called with args: {args}")
        params = json.loads(args)
        user_id = params.get("user_id", "anonymous")

        # Get user from database
        user = None
        for u in User.instances():
            if u.id == user_id:
                user = u
                break

        if not user:
            return json.dumps({"success": False, "error": "User not found"})

        personal_data = {
            "name": user.name or "",
            "id_number": user.id or "",
            "date_of_birth": "",
            "citizenship_status": (
                "Full Membership"
                if user.profiles and "member" in user.profiles
                else "Pending"
            ),
            "registration_date": (
                str(user.timestamp_created)
                if hasattr(user, "timestamp_created")
                else ""
            ),
            "address": "",
            "email": user.email or "",
            "phone": "",
        }

        response = {"success": True, "data": {"personal_data": personal_data}}

        logger.info(f"get_personal_data successful for user: {user_id}")
        return json.dumps(response)
    except Exception as e:
        logger.error(
            f"Error in get_personal_data: {str(e)}\n" f"{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def _validate_address(address: str, network: str) -> tuple[bool, str]:
    """Validate address format based on network"""
    if not address or len(address) == 0:
        return False, "Address cannot be empty"

    if network == "ICP":
        # ICP principals: one or more 5-char segments,
        # ending with 3-char checksum
        pattern = r"^([a-z0-9]{5}-)+[a-z0-9]{3}$"
        if not re.match(pattern, address):
            return False, "Invalid ICP principal format"
    elif network == "Bitcoin":
        if not (
            (address.startswith("1") and 26 <= len(address) <= 35)
            or (address.startswith("3") and 26 <= len(address) <= 35)
            or (address.startswith("bc1") and len(address) >= 42)
        ):
            return False, "Invalid Bitcoin address format"
    elif network == "Ethereum":
        if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
            return False, "Invalid Ethereum address format"
    elif network == "SEPA":
        if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$", address.upper()):
            return False, "Invalid IBAN format"

    return True, ""


def add_payment_account(args: str) -> str:
    """
    Add a new payment account for a user.

    Args:
        args (str): JSON string containing user_id, address, label,
                    network, currency

    Returns:
        str: JSON string with success status and account data
    """
    try:
        logger.info(f"add_payment_account called with args: {args}")
        params = json.loads(args)
        user_id = params.get("user_id")
        address = params.get("address")
        label = params.get("label")
        network = params.get("network")
        currency = params.get("currency")

        if not all([user_id, address, label, network, currency]):
            return json.dumps({"success": False, "error": "Missing required fields"})

        # Get user
        user = User[user_id]
        if not user:
            return json.dumps({"success": False, "error": "User not found"})

        # Validate address
        is_valid, error_msg = _validate_address(address, network)
        if not is_valid:
            return json.dumps({"success": False, "error": error_msg})

        # Check for duplicates
        existing = [
            pa
            for pa in list(user.payment_accounts)
            if pa.address == address and pa.is_active
        ]
        if existing:
            return json.dumps(
                {
                    "success": False,
                    "error": "Payment account with this address already exists",
                }
            )

        # Create payment account (ID auto-generated by PaymentAccount entity)
        payment_account = PaymentAccount(
            address=address,
            label=label,
            network=network,
            currency=currency,
            user=user,
            is_active=True,
            is_verified=False,
            metadata="{}",
        )

        logger.info(f"Created payment account {payment_account.id} for user {user_id}")

        return json.dumps({"success": True, "data": payment_account.serialize()})
    except Exception as e:
        logger.error(
            f"Error in add_payment_account: {str(e)}\n" f"{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def list_payment_accounts(args: str) -> str:
    """
    List payment accounts for a user.

    Args:
        args (str): JSON string containing user_id (principal)

    Returns:
        str: JSON string with success status and accounts list
    """
    try:
        params = json.loads(args)
        user_id = params.get("user_id")

        if not user_id:
            return json.dumps({"success": False, "error": "Missing user_id"})

        # Get user
        user = User[user_id]
        if not user:
            return json.dumps({"success": False, "error": "User not found"})

        # Get active payment accounts
        accounts = [
            pa.serialize() for pa in list(user.payment_accounts) if pa.is_active
        ]

        return json.dumps({"success": True, "data": accounts})

    except Exception as e:
        logger.error(f"Error listing payment accounts: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def remove_payment_account(args: str) -> str:
    """
    Remove a payment account (soft delete).

    Args:
        args (str): JSON string containing user_id and account_id

    Returns:
        str: JSON string with success status
    """
    try:
        params = json.loads(args)
        user_id = params.get("user_id")
        account_id = params.get("account_id")

        if not all([user_id, account_id]):
            return json.dumps({"success": False, "error": "Missing required fields"})

        # Get user
        user = User[user_id]
        if not user:
            return json.dumps({"success": False, "error": "User not found"})

        # Find account
        account = PaymentAccount[account_id]
        if not account or account.user != user:
            return json.dumps({"success": False, "error": "Payment account not found"})

        # Soft delete
        account.is_active = False

        return json.dumps({"success": True})

    except Exception as e:
        logger.error(f"Error removing payment account: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})
