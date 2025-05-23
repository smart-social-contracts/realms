from typing import Any, Dict, Optional

from kybra import Opt, Record, Vec, nat, query, update
from kybra_simple_logging import get_logger

from realm_backend.core.extensions import call_extension, extension_registry

logger = get_logger("api.extensions")


# Type definitions for candid interface
class ExtensionInfo(Record):
    name: str
    description: str
    required_permissions: Vec[str]
    granted_permissions: Vec[str]
    entry_points: Vec[str]


# Dictionary representation for Candid
class KeyValuePair(Record):
    key: str
    value: str  # Using str for simplicity; Candid has limited variant support


# Modified ExtensionCallArgs to avoid using Dict directly
class ExtensionCallArgs(Record):
    extension_name: str
    entry_point: str
    args: Opt[Vec[str]]  # Simplified to string arguments
    kwargs: Opt[Vec[KeyValuePair]]


# Response types
class SuccessResponse(Record):
    success: bool
    message: str


class BalanceResponse(Record):
    success: bool
    balance: nat
    token: str
    principal_id: str


class ErrorResponse(Record):
    success: bool
    error: str


@query
def list_extensions() -> Vec[ExtensionInfo]:
    """List all available extensions with their metadata"""
    try:
        extensions = extension_registry.list_extensions()
        logger.info(f"Listed {len(extensions)} extensions")
        return [
            ExtensionInfo(
                name=ext["name"],
                description=ext["description"],
                required_permissions=ext["required_permissions"],
                granted_permissions=ext["granted_permissions"],
                entry_points=ext["entry_points"],
            )
            for ext in extensions
        ]
    except Exception as e:
        logger.error(f"Error listing extensions: {str(e)}")
        return []


@update
async def call_extension_api(args: ExtensionCallArgs) -> SuccessResponse:
    """Call an extension's entry point with the provided arguments"""
    try:
        # Convert string args to appropriate types as needed
        ext_args = (
            args.args.value if hasattr(args, "args") and args.args is not None else []
        )

        # Convert key-value pairs to dict
        ext_kwargs = {}
        if hasattr(args, "kwargs") and args.kwargs is not None:
            for pair in args.kwargs.value:
                ext_kwargs[pair.key] = pair.value

        logger.info(
            f"Calling extension '{args.extension_name}' entry point '{args.entry_point}'"
        )

        await call_extension(
            args.extension_name, args.entry_point, *ext_args, **ext_kwargs
        )

        return SuccessResponse(success=True, message="Extension call successful")
    except Exception as e:
        logger.error(f"Error calling extension: {str(e)}")
        return ErrorResponse(success=False, error=str(e))


# Convenience API endpoints for Vault Manager


@query
async def get_vault_status() -> Dict[str, Any]:
    """Get vault status (convenience method for vault_manager.get_status)"""
    try:
        result = await call_extension("vault_manager", "get_status")
        logger.info(f"Vault status retrieved: {result}")
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error in get_vault_status: {str(e)}")
        return {"success": False, "error": str(e)}


@query
async def get_balance(principal_id: Optional[str] = None) -> Dict[str, Any]:
    """Get balance for a principal (convenience method for vault_manager.get_balance)"""
    try:
        kwargs = {}
        if principal_id:
            kwargs["principal_id"] = principal_id

        result = await call_extension("vault_manager", "get_balance", **kwargs)
        logger.info(f"Balance retrieved: {result}")

        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error in get_balance: {str(e)}")
        return {"success": False, "error": str(e)}


@query
async def get_transactions(
    limit: Optional[int] = 10, offset: Optional[int] = 0
) -> Dict[str, Any]:
    """Get transaction history (convenience method for vault_manager.get_transactions)"""
    try:
        kwargs = {"limit": limit, "offset": offset}
        result = await call_extension("vault_manager", "get_transactions", **kwargs)
        logger.info(
            f"Transactions retrieved: {len(result.get('transactions', []))} transactions"
        )

        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}")
        return {"success": False, "error": str(e)}


@update
async def transfer_tokens(
    to_principal_id: str, amount: int, memo: Optional[str] = ""
) -> Dict[str, Any]:
    """Transfer tokens (convenience method for vault_manager.transfer)"""
    try:
        kwargs = {"to_principal_id": to_principal_id, "amount": amount, "memo": memo}
        result = await call_extension("vault_manager", "transfer", **kwargs)
        logger.info(f"Transfer completed: {result}")

        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error in transfer_tokens: {str(e)}")
        return {"success": False, "error": str(e)}
