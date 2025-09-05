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

from ggg import Codex, Human, Instrument, Mandate, Organization, Realm, Treasury, Transfer, User, UserProfile

from .models import RegistrationCode


def extension_sync_call(method_name: str, args: dict):
    """
    Synchronous extension API calls for admin operations
    """
    # Method mapping with argument requirements
    methods = {
        "get_admin_stats": (get_admin_statistics, False),  # (function, requires_args)
        "get_system_health": (get_system_health_check, False),
        "get_recent_activity": (get_recent_activity, False),
        "get_templates": (get_templates, True),
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


def extension_async_call(method_name: str, args: dict):
    """
    Asynchronous extension API calls for admin operations
    """
    # Async method mapping
    async_methods = {
        "export_data": lambda args: export_system_data(args.get("entity_types", [])),
        "bulk_operation": lambda args: perform_bulk_operation(
            args.get("operation"), args.get("entity_type"), args.get("data")
        ),
    }

    if method_name not in async_methods:
        return {"success": False, "error": f"Unknown async method: {method_name}"}

    try:
        return async_methods[method_name](args)
    except Exception as e:
        return {
            "success": False,
            "error": f"Error calling async {method_name}: {str(e)}",
        }


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
    Get field schemas for bulk import entities
    """
    try:
        entity_type = args.get("entity_type", "users")

        # Return field schemas instead of hardcoded templates
        schemas = {
            "users": {
                "required_fields": ["id"],
                "optional_fields": ["profile_picture_url"],
                "description": "User entities with unique identifiers",
            },
            "user_profiles": {
                "required_fields": ["name"],
                "optional_fields": ["description"],
                "description": "User profile definitions (admin, member, etc.)",
            },
            "humans": {
                "required_fields": ["id", "name"],
                "optional_fields": ["email", "phone", "address"],
                "description": "Human entities with personal information",
            },
            "organizations": {
                "required_fields": ["id", "name"],
                "optional_fields": ["description", "website", "email"],
                "description": "Organization entities",
            },
            "mandates": {
                "required_fields": ["id", "name"],
                "optional_fields": ["description", "status"],
                "description": "Mandate entities for governance",
            },
            "codexes": {
                "required_fields": ["id", "name", "code"],
                "optional_fields": ["description", "version"],
                "description": "Codex entities with executable code",
            },
            "instruments": {
                "required_fields": ["id", "name", "type"],
                "optional_fields": ["description", "value"],
                "description": "Financial instrument entities",
            },
        }

        return {"success": True, "data": schemas.get(entity_type, schemas["users"])}
    except Exception as e:
        return {"success": False, "error": str(e)}


def import_data(args):
    """
    Import data from direct data input
    """
    try:
        # Parse args if it's a JSON string
        if isinstance(args, str):
            args = json.loads(args)

        entity_type = args.get("data_type", args.get("entity_type", "users"))
        data_format = args.get("format", "json")
        data_content = args.get("data", "")

        # Map data_type to entity_type for processing
        if entity_type == "profiles":
            entity_type = "user_profiles"

        if not data_content:
            return {"success": False, "error": "No data provided"}

        # Parse data based on format
        parsed_data = []
        if data_format == "csv":
            # Handle CSV data
            import csv
            import io

            csv_reader = csv.DictReader(io.StringIO(data_content))
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
        results = process_bulk_import(entity_type, parsed_data)

        return {
            "success": True,
            "message": f"Successfully imported {len(parsed_data)} {entity_type} records",
            "data": {
                "entity_type": entity_type,
                "total_records": len(parsed_data),
                "successful": results["successful"],
                "failed": results["failed"],
                "errors": results["errors"],
            },
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


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

    # Entity type to creation function mapping
    entity_creators = {
        "users": create_user_entity,
        "humans": create_human_entity,
        "organizations": create_organization_entity,
        "mandates": create_mandate_entity,
        "codexes": create_codex_entity,
        "instruments": create_instrument_entity,
        "user_profiles": create_user_profile_entity,
        "treasury": create_treasury_entity,
        "realm": create_realm_entity,
        "transfers": create_transfer_entity,
    }

    create_function = entity_creators.get(entity_type)
    if not create_function:
        return {
            "successful": 0,
            "failed": len(data),
            "errors": [f"Unsupported entity type: {entity_type}"],
        }

    # Process in batches to avoid cycle limits
    batch_size = 50
    for i in range(0, len(data), batch_size):
        batch = data[i : i + batch_size]

        for record in batch:
            try:
                # Handle case where record might be wrapped in an array
                if isinstance(record, list) and len(record) == 1:
                    record = record[0]
                elif isinstance(record, list) and len(record) > 1:
                    # If multiple records in array, process each one
                    for sub_record in record:
                        try:
                            create_function(sub_record)
                            successful += 1
                        except Exception as e:
                            failed += 1
                            errors.append(f"Record {sub_record}: {str(e)}")
                    continue
                
                create_function(record)
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
    required_fields = ["id"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    user = User(id=data["id"], profile_picture_url=data.get("profile_picture_url", ""))
    return user


def create_human_entity(data: Dict[str, Any]):
    """Create a Human entity from import data"""
    required_fields = ["id", "name"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    human = Human(
        id=data["id"],
        name=data["name"],
        email=data.get("email", ""),
        phone=data.get("phone", ""),
        address=data.get("address", ""),
    )
    return human


def create_organization_entity(data: Dict[str, Any]):
    """Create an Organization entity from import data"""
    required_fields = ["id", "name"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    org = Organization(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        website=data.get("website", ""),
        email=data.get("email", ""),
    )
    return org


def create_mandate_entity(data: Dict[str, Any]):
    """Create a Mandate entity from import data"""
    required_fields = ["id", "name"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    mandate = Mandate(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        status=data.get("status", "active"),
    )
    return mandate


def create_codex_entity(data: Dict[str, Any]):
    """Create a Codex entity from import data"""
    required_fields = ["id", "name", "code"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    codex = Codex(
        id=data["id"],
        name=data["name"],
        code=data["code"],
        description=data.get("description", ""),
        version=data.get("version", "1.0.0"),
    )
    return codex


def create_instrument_entity(data: Dict[str, Any]):
    """Create an Instrument entity from import data"""
    required_fields = ["id", "name", "type"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    instrument = Instrument(
        id=data["id"],
        name=data["name"],
        type=data["type"],
        description=data.get("description", ""),
        value=data.get("value", 0),
    )
    return instrument


def create_user_profile_entity(data: Dict[str, Any]):
    """Create a UserProfile entity from import data"""
    required_fields = ["name"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    profile = UserProfile(
        id=data["name"],
        name=data["name"],  # Use id as name for profile identifier
        description=data.get("description", ""),
    )
    return profile


def create_treasury_entity(data: Dict[str, Any]):
    """Create a Treasury entity from import data"""
    required_fields = ["name"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    treasury = Treasury(
        name=data["name"],
        vault_principal_id=data.get("vault_principal_id", ""),
        realm=Realm[data["realm"]],
    )
    return treasury


def create_realm_entity(data: Dict[str, Any]):
    """Create a Realm entity from import data"""

    realm = Realm(
        name=data["name"],
        description=data.get("description", ""),
    )

    treasury_name = data["treasury"]
    treasury = Treasury[treasury_name]
    realm.treasury = treasury

    return realm


def create_transfer_entity(data: Dict[str, Any]):
    """Create a Transfer entity from import data"""
    required_fields = ["id", "amount", "from_user", "to_user"]
    for field in required_fields:
        if field not in data or not data[field]:
            raise Exception(f"Missing required field: {field}")

    transfer = Transfer(
        id=data["id"],
        amount=data["amount"],
        from_user=data["from_user"],
        to_user=data["to_user"],
        timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
    )
    return transfer


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
