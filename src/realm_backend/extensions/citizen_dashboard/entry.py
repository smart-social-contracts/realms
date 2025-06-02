import json
import traceback
from datetime import datetime, timedelta

from kybra import Async
from kybra_simple_logging import get_logger

# Initialize logger
logger = get_logger("citizen_dashboard")


def get_dashboard_summary(args: str) -> Async[str]:
    try:
        args = "{}"
        logger.info(f"get_dashboard_summary called with args: {args}")
        params = json.loads(args)
        user_id = params.get("user_id", "anonymous")

        # In a real implementation, we would fetch this data from a database or service
        # For demonstration, we'll return mock data
        summary_data = {
            "user_name": "John Citizen",
            "services_count": 5,
            "services_approaching": 2,
            "tax_records": 4,
            "tax_overdue": 1,
            "personal_data_items": 8,
            "personal_data_updated": 2,
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
    Get a list of public services for the citizen.

    Args:
        args (str): JSON string containing user_id

    Returns:
        str: JSON string with public services data
    """
    try:
        logger.info(f"get_public_services called with args: {args}")
        params = json.loads(args)
        user_id = params.get("user_id", "anonymous")

        # Mock data - in a real implementation, we would fetch this from a database
        today = datetime.now()
        services = [
            {
                "id": "srv-001",
                "name": "Citizen ID Renewal",
                "description": "Renew your citizen identification card",
                "provider": "Department of Citizen Affairs",
                "status": "Active",
                "due_date": (today + timedelta(days=30)).isoformat(),
                "link": "/service/id-renewal",
            },
            {
                "id": "srv-002",
                "name": "Property Tax Filing",
                "description": "Annual property tax declaration",
                "provider": "Tax Department",
                "status": "Pending",
                "due_date": (today + timedelta(days=5)).isoformat(),
                "link": "/service/property-tax",
            },
            {
                "id": "srv-003",
                "name": "Vehicle Registration",
                "description": "Renew your vehicle registration",
                "provider": "Transport Authority",
                "status": "Expired",
                "due_date": (today - timedelta(days=15)).isoformat(),
                "link": "/service/vehicle-reg",
            },
            {
                "id": "srv-004",
                "name": "Health Insurance Verification",
                "description": "Verify your health insurance status",
                "provider": "Health Department",
                "status": "Active",
                "due_date": (today + timedelta(days=90)).isoformat(),
                "link": "/service/health-insurance",
            },
            {
                "id": "srv-005",
                "name": "Business License Renewal",
                "description": "Renew your business operating license",
                "provider": "Business Registry",
                "status": "Pending",
                "due_date": (today + timedelta(days=7)).isoformat(),
                "link": "/service/business-license",
            },
        ]

        response = {
            "success": True,
            "data": {"services": services, "total_count": len(services)},
        }

        logger.info(f"get_public_services successful for user: {user_id}")
        return json.dumps(response)
    except Exception as e:
        logger.error(f"Error in get_public_services: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def get_tax_information(args: str) -> str:
    """
    Get tax information for the citizen.

    Args:
        args (str): JSON string containing user_id

    Returns:
        str: JSON string with tax information data
    """
    try:
        args = "{}"
        logger.info(f"get_tax_information called with args: {args}")
        params = json.loads(args)
        user_id = params.get("user_id", "anonymous")

        # Mock data - in a real implementation, we would fetch this from a tax database
        today = datetime.now()

        tax_records = [
            {
                "id": "tax-001",
                "tax_type": "Income Tax",
                "description": "Annual personal income tax",
                "period": "2024",
                "amount": 2450.75,
                "due_date": (today + timedelta(days=45)).isoformat(),
                "status": "Pending",
            },
            {
                "id": "tax-002",
                "tax_type": "Property Tax",
                "description": "Residential property tax",
                "period": "2024 Q1",
                "amount": 650.00,
                "due_date": (today - timedelta(days=15)).isoformat(),
                "status": "Overdue",
            },
            {
                "id": "tax-003",
                "tax_type": "Vehicle Tax",
                "description": "Annual vehicle ownership tax",
                "period": "2024",
                "amount": 320.50,
                "due_date": (today - timedelta(days=60)).isoformat(),
                "status": "Paid",
            },
            {
                "id": "tax-004",
                "tax_type": "Business Tax",
                "description": "Quarterly business operations tax",
                "period": "2024 Q2",
                "amount": 1200.00,
                "due_date": (today + timedelta(days=10)).isoformat(),
                "status": "Pending",
            },
        ]

        # Calculate summary
        total_paid = sum(
            record["amount"] for record in tax_records if record["status"] == "Paid"
        )
        total_pending = sum(
            record["amount"] for record in tax_records if record["status"] == "Pending"
        )
        total_overdue = sum(
            record["amount"] for record in tax_records if record["status"] == "Overdue"
        )

        summary = {
            "total_paid": total_paid,
            "total_pending": total_pending,
            "total_overdue": total_overdue,
            "total_amount": total_paid + total_pending + total_overdue,
        }

        response = {
            "success": True,
            "data": {"tax_records": tax_records, "summary": summary},
        }

        logger.info(f"get_tax_information successful for user: {user_id}")
        return json.dumps(response)
    except Exception as e:
        logger.error(
            f"Error in get_tax_information: {str(e)}\n{traceback.format_exc()}"
        )
        return json.dumps({"success": False, "error": str(e)})


def get_personal_data(args: str) -> str:
    """
    Get personal data for the citizen.

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

        # Mock data - in a real implementation, we would fetch this from a secure database
        today = datetime.now()

        personal_data = {
            "name": "John Citizen",
            "id_number": "CTZ-12345678",
            "date_of_birth": "1980-05-15",
            "citizenship_status": "Full Citizenship",
            "registration_date": "2010-03-22",
            "address": "123 Main Street, Cityville, State 12345",
            "email": "john.citizen@email.com",
            "phone": "+1 (555) 123-4567",
        }

        response = {"success": True, "data": {"personal_data": personal_data}}

        logger.info(f"get_personal_data successful for user: {user_id}")
        return json.dumps(response)
    except Exception as e:
        logger.error(f"Error in get_personal_data: {str(e)}\n{traceback.format_exc()}")
        return json.dumps({"success": False, "error": str(e)})
