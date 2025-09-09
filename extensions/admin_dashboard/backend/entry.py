"""
Admin Dashboard Backend Extension Entry Point
Provides administrative operations and data aggregation for the GGG system.
"""

import base64
import csv
import json
import traceback
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List

import ggg
from kybra_simple_logging import get_logger

from .models import RegistrationCode

logger = get_logger("extensions.admin_dashboard")


def extension_sync_call(method_name: str, args: dict):
    """
    Synchronous extension API calls for admin operations
    """
    # Method mapping with argument requirements
    methods = {
        "import_data": (import_data, True),
        "generate_registration_url": (generate_registration_url, True),
        "validate_registration_code": (validate_registration_code, True),
        "get_registration_codes": (get_registration_codes, True),
    }

    if method_name not in methods:
        return {"success": False, "error": f"Unknown method: {method_name}"}

    function, requires_args = methods[method_name]

    try:
        if requires_args:
            return function(args)
        else:
            return function()
    except Exception as e:
        return {"success": False, "error": f"Error calling {method_name}: {str(e)}"}


def import_data(args):
    """
    Import data from direct data input
    """
    try:
        # Parse args if it's a JSON string
        if isinstance(args, str):
            args = json.loads(args)

        data_format = args.get("format", "json")
        data_content = args.get("data", "")

        logger.info(f"data_content: {data_content}")
        logger.info(f"data_format: {data_format}")

        if not data_content:
            return {"success": False, "error": "No data provided"}

        # Parse data based on format
        parsed_data = []
        if data_format == "csv":
            # Handle CSV data
            csv_reader = csv.DictReader(StringIO(data_content))
            parsed_data = list(csv_reader)
        else:
            # Handle JSON data
            try:
                if isinstance(data_content, str):
                    parsed_data = json.loads(data_content)
                else:
                    parsed_data = data_content

                if not isinstance(parsed_data, list):
                    parsed_data = [parsed_data]
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"Invalid JSON data: {str(e)}"}

        # Process data in batches
        logger.info(f"parsed_data: {parsed_data}")
        results = process_bulk_import(parsed_data)

        return {
            "success": True,
            "message": f"Successfully imported {len(parsed_data)} records",
            "data": {
                "total_records": len(parsed_data),
                "successful": results["successful"],
                "failed": results["failed"],
                "errors": results["errors"],
            },
        }

    except Exception as e:
        logger.error(f"Error processing import data: {e}\n{traceback.format_exc()}")
        return {"success": False, "error": str(e)}


def process_bulk_import(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process bulk import data and create entities"""
    successful = 0
    failed = 0
    errors = []

    logger.info(f"data: {data}")

    for record in data:
        try:
            entity_type = record.get("class")
            logger.info(f"entity_type: {entity_type}")

            entity = getattr(ggg, entity_type)
            logger.info(f"entity: {entity}")

            entity_data = record["data"]

            create_entity(entity, entity_data)
            successful += 1
        except Exception as e:
            logger.error(f"Error creating entity: {str(e)}\n{traceback.format_exc()}")
            failed += 1
            errors.append(f"Record {record}: {str(e)}")

    return {
        "successful": successful,
        "failed": failed,
        "errors": errors[:10],  # Limit to first 10 errors
    }


def create_entity(entity, data: Dict[str, Any]):
    if entity == "Codex":
        obj = ggg.Codex()
        obj.name = data["name"]
        obj.code = base64.b64decode(data["code"])
        return obj
    return entity(**data)


def generate_registration_url(args: dict):
    """Generate a registration URL for a user"""
    try:
        user_id = args.get("user_id")
        created_by = args.get("created_by", "admin")
        frontend_url = args.get("frontend_url", "https://localhost:3000")
        email = args.get("email")
        expires_in_hours = args.get("expires_in_hours", 24)

        if not user_id:
            return {"success": False, "error": "user_id is required"}

        # Create registration code
        reg_code = RegistrationCode.create(
            user_id=user_id,
            created_by=created_by,
            frontend_url=frontend_url,
            email=email,
            expires_in_hours=expires_in_hours,
        )

        return {
            "success": True,
            "data": {
                "code": reg_code.code,
                "registration_url": reg_code.registration_url,
                "expires_at": datetime.fromtimestamp(reg_code.expires_at).isoformat(),
                "user_id": reg_code.user_id,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def validate_registration_code(args: dict):
    """Validate a registration code"""
    try:
        code = args.get("code")
        if not code:
            return {"success": False, "error": "code is required"}

        # Find registration code
        reg_code = RegistrationCode.find_by_code(code)
        if not reg_code:
            return {"success": False, "error": "Invalid registration code"}

        # Check if valid
        if not reg_code.is_valid():
            current_timestamp = int(datetime.utcnow().timestamp())
            reason = (
                "expired" if reg_code.expires_at < current_timestamp else "already used"
            )
            return {"success": False, "error": f"Registration code is {reason}"}

        return {
            "success": True,
            "data": {
                "user_id": reg_code.user_id,
                "email": reg_code.email,
                "expires_at": datetime.fromtimestamp(reg_code.expires_at).isoformat(),
                "created_by": reg_code.created_by,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_registration_codes(args: dict):
    """Get registration codes with optional filtering"""
    try:
        user_id = args.get("user_id")
        include_used = args.get("include_used", False)

        if user_id:
            codes = RegistrationCode.find_by_user_id(user_id)
        else:
            codes = RegistrationCode.instances()

        # Filter out used codes if requested
        if not include_used:
            codes = [code for code in codes if code.used == 0]

        return {
            "success": True,
            "data": [
                {
                    "code": code.code,
                    "user_id": code.user_id,
                    "email": code.email,
                    "registration_url": code.registration_url,
                    "expires_at": datetime.fromtimestamp(code.expires_at).isoformat(),
                    "used": code.used == 1,
                    "used_at": (
                        datetime.fromtimestamp(code.used_at).isoformat()
                        if code.used_at > 0
                        else None
                    ),
                    "created_by": code.created_by,
                    "is_valid": code.is_valid(),
                }
                for code in codes
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
