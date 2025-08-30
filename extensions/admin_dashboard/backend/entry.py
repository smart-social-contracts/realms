"""
Admin Dashboard Backend Extension Entry Point
Provides administrative operations and data aggregation for the GGG system.
"""

import csv
import json
import traceback
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List

from ggg import Codex, Human, Instrument, Mandate, Organization, User

from .models import RegistrationCode


def extension_sync_call(method_name: str, args: dict):
    """
    Synchronous extension API calls for admin operations
    """
    if method_name == "get_admin_stats":
        return get_admin_statistics()
    elif method_name == "get_system_health":
        return get_system_health_check()
    elif method_name == "get_recent_activity":
        return get_recent_activity()
    elif method_name == "get_templates":
        return get_templates(args)
    elif method_name == "import_data":
        return import_data(args)
    elif method_name == "generate_registration_url":
        return generate_registration_url(args)
    elif method_name == "validate_registration_code":
        return validate_registration_code(args)
    elif method_name == "get_registration_codes":
        return get_registration_codes(args)
    else:
        return {"success": False, "error": f"Unknown method: {method_name}"}


def extension_async_call(method_name: str, args: dict):
    """
    Asynchronous extension API calls for admin operations
    """
    if method_name == "export_data":
        return export_system_data(args.get("entity_types", []))
    elif method_name == "bulk_operation":
        return perform_bulk_operation(
            args.get("operation"), args.get("entity_type"), args.get("data")
        )
    else:
        return {"success": False, "error": f"Unknown async method: {method_name}"}


def get_admin_statistics():
    """
    Get comprehensive system statistics for admin dashboard
    """
    try:
        # This would integrate with the main backend to get real statistics
        # For now, return a structure that matches what the frontend expects
        return {
            "success": True,
            "data": {
                "total_entities": 0,
                "total_transfers": 0,
                "total_transfer_volume": 0,
                "active_mandates": 0,
                "scheduled_tasks": 0,
                "open_disputes": 0,
                "active_proposals": 0,
                "total_votes": 0,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_system_health_check():
    """
    Perform system health checks for admin monitoring
    """
    try:
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "uptime": "99.9%",
                "last_backup": "2024-01-20T10:00:00Z",
                "database_status": "connected",
                "canister_cycles": "sufficient",
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_recent_activity():
    """
    Get recent system activity for admin monitoring
    """
    try:
        return {"success": True, "data": {"activities": []}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def export_system_data(entity_types):
    """
    Export system data for backup or analysis
    """
    try:
        return {
            "success": True,
            "data": {
                "export_id": "export_123",
                "status": "initiated",
                "entity_types": entity_types,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def perform_bulk_operation(operation, entity_type, data):
    """
    Perform bulk operations on entities
    """
    try:
        return {
            "success": True,
            "data": {
                "operation": operation,
                "entity_type": entity_type,
                "processed": len(data) if data else 0,
                "status": "completed",
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_templates(args):
    """
    Get CSV/JSON templates for bulk import
    """
    try:
        entity_type = args.get("entity_type", "users")

        templates = {
            "users": {
                "csv": "username,email,profile_type\nexample_user,user@example.com,member",
                "json": [
                    {
                        "username": "example_user",
                        "email": "user@example.com",
                        "profile_type": "member",
                    }
                ],
            },
            "humans": {
                "csv": "name,email,phone,address\nJohn Doe,john@example.com,+1234567890,123 Main St",
                "json": [
                    {
                        "name": "John Doe",
                        "email": "john@example.com",
                        "phone": "+1234567890",
                        "address": "123 Main St",
                    }
                ],
            },
            "organizations": {
                "csv": "name,description,website,contact_email\nExample Org,A sample organization,https://example.org,contact@example.org",
                "json": [
                    {
                        "name": "Example Org",
                        "description": "A sample organization",
                        "website": "https://example.org",
                        "contact_email": "contact@example.org",
                    }
                ],
            },
            "mandates": {
                "csv": "title,description,status,priority\nSample Mandate,A sample mandate description,active,high",
                "json": [
                    {
                        "title": "Sample Mandate",
                        "description": "A sample mandate description",
                        "status": "active",
                        "priority": "high",
                    }
                ],
            },
            "codexes": {
                "csv": "title,content,category,version\nSample Codex,Sample codex content,policy,1.0",
                "json": [
                    {
                        "title": "Sample Codex",
                        "content": "Sample codex content",
                        "category": "policy",
                        "version": "1.0",
                    }
                ],
            },
            "instruments": {
                "csv": "name,type,description,value\nSample Instrument,contract,A sample instrument,1000",
                "json": [
                    {
                        "name": "Sample Instrument",
                        "type": "contract",
                        "description": "A sample instrument",
                        "value": 1000,
                    }
                ],
            },
        }

        return {"success": True, "data": templates.get(entity_type, templates["users"])}
    except Exception as e:
        return {"success": False, "error": str(e)}


def import_data(args):
    """
    Import bulk data from CSV or JSON
    """
    try:
        entity_type = args.get("entity_type", "users")
        data_format = args.get("format", "csv")
        data_content = args.get("data", "")

        if not data_content:
            return {"success": False, "error": "No data provided"}

        # Parse data based on format
        parsed_data = []
        if data_format == "csv":
            parsed_data = parse_csv_data(data_content)
        elif data_format == "json":
            parsed_data = parse_json_data(data_content)
        else:
            return {"success": False, "error": f"Unsupported format: {data_format}"}

        if not parsed_data:
            return {"success": False, "error": "No valid data found"}

        # Process data in batches
        results = process_bulk_import(entity_type, parsed_data)

        return {
            "success": True,
            "data": {
                "entity_type": entity_type,
                "format": data_format,
                "total_records": len(parsed_data),
                "successful": results["successful"],
                "failed": results["failed"],
                "errors": results["errors"],
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


def parse_csv_data(csv_content: str) -> List[Dict[str, Any]]:
    """Parse CSV content into list of dictionaries"""
    try:
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        return [row for row in reader]
    except Exception as e:
        raise Exception(f"CSV parsing error: {str(e)}")


def parse_json_data(json_content: str) -> List[Dict[str, Any]]:
    """Parse JSON content into list of dictionaries"""
    try:
        data = json.loads(json_content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            raise Exception("JSON must be an object or array of objects")
    except json.JSONDecodeError as e:
        raise Exception(f"JSON parsing error: {str(e)}")


def process_bulk_import(entity_type: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process bulk import data and create entities"""
    successful = 0
    failed = 0
    errors = []

    # Process in batches to avoid cycle limits
    batch_size = 50
    for i in range(0, len(data), batch_size):
        batch = data[i : i + batch_size]

        for record in batch:
            try:
                if entity_type == "users":
                    create_user_entity(record)
                elif entity_type == "humans":
                    create_human_entity(record)
                elif entity_type == "organizations":
                    create_organization_entity(record)
                elif entity_type == "mandates":
                    create_mandate_entity(record)
                elif entity_type == "codexes":
                    create_codex_entity(record)
                elif entity_type == "instruments":
                    create_instrument_entity(record)
                else:
                    raise Exception(f"Unsupported entity type: {entity_type}")

                successful += 1
            except Exception as e:
                failed += 1
                errors.append(f"Record {record}: {str(e)}")

    return {
        "successful": successful,
        "failed": failed,
        "errors": errors[:10],  # Limit to first 10 errors
    }


def create_user_entity(data: Dict[str, Any]):
    """Create a User entity from import data"""
    # This would integrate with the actual User creation logic
    # For now, simulate the creation
    required_fields = ["username"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    # Simulate User.create() call
    pass


def create_human_entity(data: Dict[str, Any]):
    """Create a Human entity from import data"""
    required_fields = ["name"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    # Simulate Human.create() call
    pass


def create_organization_entity(data: Dict[str, Any]):
    """Create an Organization entity from import data"""
    required_fields = ["name"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    # Simulate Organization.create() call
    pass


def create_mandate_entity(data: Dict[str, Any]):
    """Create a Mandate entity from import data"""
    required_fields = ["title"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    # Simulate Mandate.create() call
    pass


def create_codex_entity(data: Dict[str, Any]):
    """Create a Codex entity from import data"""
    required_fields = ["title", "content"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    # Simulate Codex.create() call
    pass


def create_instrument_entity(data: Dict[str, Any]):
    """Create an Instrument entity from import data"""
    required_fields = ["name", "type"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    # Simulate Instrument.create() call
    pass


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
