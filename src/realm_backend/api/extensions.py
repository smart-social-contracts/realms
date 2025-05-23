from typing import Any, Dict, List, Optional

from core.extensions import call_extension, extension_registry
from kybra import Opt, Record, Vec, nat, query, update, text
from kybra_simple_logging import get_logger

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


# Settings type for configuration
class ExtensionSettings(Record):
    enabled: bool = True
    # Add other common settings here


# Modified ExtensionCallArgs to avoid using Dict directly
class ExtensionCallArgs(Record):
    extension_name: str
    entry_point: str
    args: Opt[Vec[str]] = None  # Simplified to string arguments
    kwargs: Opt[Vec[KeyValuePair]] = None


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


class ExtensionConfig(Record):
    settings: Vec[KeyValuePair]  # Replace Dict with Vec of KeyValuePair


class ExtensionStatusItem(Record):
    name: str
    description: str
    enabled: bool
    required_permissions: Vec[str]
    granted_permissions: Vec[str]
    entry_points: Vec[str]
    settings: Opt[Vec[KeyValuePair]] = None


class ExtensionStatusResponse(Record):
    success: bool
    extensions: Vec[ExtensionStatusItem]


class ExtensionUpdateResponse(Record):
    success: bool
    message: str


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
        ext_args = []
        if args.args is not None:
            ext_args = args.args.value

        # Convert key-value pairs to dict
        ext_kwargs = {}
        if args.kwargs is not None:
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
async def get_vault_status() -> Record:
    """Get vault status (convenience method for vault_manager.get_status)"""
    try:
        result = await call_extension("vault_manager", "get_status")
        logger.info(f"Vault status retrieved: {result}")
        return SuccessResponse(success=True, message=str(result))
    except Exception as e:
        logger.error(f"Error in get_vault_status: {str(e)}")
        return ErrorResponse(success=False, error=str(e))


@query
async def get_balance(principal_id: Opt[str] = None) -> Record:
    """Get balance for a principal (convenience method for vault_manager.get_balance)"""
    try:
        kwargs = {}
        if principal_id is not None:
            kwargs["principal_id"] = principal_id.value

        result = await call_extension("vault_manager", "get_balance", **kwargs)
        logger.info(f"Balance retrieved: {result}")

        return BalanceResponse(
            success=True,
            balance=result.get("balance", 0),
            token=result.get("token", ""),
            principal_id=result.get("principal_id", "")
        )
    except Exception as e:
        logger.error(f"Error in get_balance: {str(e)}")
        return ErrorResponse(success=False, error=str(e))


@query
async def get_transactions(
    limit: Opt[nat] = None, offset: Opt[nat] = None
) -> Record:
    """Get transaction history (convenience method for vault_manager.get_transactions)"""
    try:
        kwargs = {}
        if limit is not None:
            kwargs["limit"] = limit.value
        if offset is not None:
            kwargs["offset"] = offset.value
            
        result = await call_extension("vault_manager", "get_transactions", **kwargs)
        logger.info(
            f"Transactions retrieved successfully"
        )

        return SuccessResponse(success=True, message=str(result))
    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}")
        return ErrorResponse(success=False, error=str(e))


@update
async def transfer_tokens(
    to_principal_id: str, amount: nat, memo: Opt[str] = None
) -> Record:
    """Transfer tokens (convenience method for vault_manager.transfer)"""
    try:
        kwargs = {"to_principal_id": to_principal_id, "amount": amount}
        if memo is not None:
            kwargs["memo"] = memo.value
            
        result = await call_extension("vault_manager", "transfer", **kwargs)
        logger.info(f"Transfer completed: {result}")

        return SuccessResponse(success=True, message=str(result))
    except Exception as e:
        logger.error(f"Error in transfer_tokens: {str(e)}")
        return ErrorResponse(success=False, error=str(e))


# Extension Management API


@query
def get_extension_status() -> ExtensionStatusResponse:
    """Get status of all installed extensions"""
    try:
        extensions_list = extension_registry.list_extensions()
        logger.info(f"Retrieved status for {len(extensions_list)} extensions")
        
        ext_items = []
        for ext in extensions_list:
            # Convert settings dict to KeyValuePair list
            settings_list = None
            if "settings" in ext:
                settings_list = [
                    KeyValuePair(key=k, value=str(v)) 
                    for k, v in ext.get("settings", {}).items()
                ]
                
            ext_items.append(
                ExtensionStatusItem(
                    name=ext["name"],
                    description=ext["description"],
                    enabled=ext.get("enabled", True),
                    required_permissions=ext["required_permissions"],
                    granted_permissions=ext["granted_permissions"],
                    entry_points=ext["entry_points"],
                    settings=Opt[Vec[KeyValuePair]](settings_list) if settings_list else None
                )
            )
            
        return ExtensionStatusResponse(success=True, extensions=ext_items)
    except Exception as e:
        logger.error(f"Error getting extension status: {str(e)}")
        return ExtensionStatusResponse(success=False, extensions=[])


@update
def set_extension_status(extension_id: str, enabled: bool) -> ExtensionUpdateResponse:
    """Enable or disable an extension"""
    try:
        success = extension_registry.set_extension_enabled(extension_id, enabled)
        if success:
            status = "enabled" if enabled else "disabled"
            message = f"Extension '{extension_id}' {status} successfully"
            logger.info(message)
            return ExtensionUpdateResponse(success=True, message=message)
        else:
            message = f"Failed to update status for extension '{extension_id}'"
            logger.error(message)
            return ExtensionUpdateResponse(success=False, message=message)
    except Exception as e:
        logger.error(f"Error setting extension status: {str(e)}")
        return ExtensionUpdateResponse(success=False, message=str(e))


@update
def set_extension_config(extension_id: str, config: ExtensionConfig) -> ExtensionUpdateResponse:
    """Update extension configuration"""
    try:
        # Convert Vec[KeyValuePair] to dict
        settings = {}
        for pair in config.settings:
            settings[pair.key] = pair.value
            
        success = extension_registry.set_extension_config(extension_id, settings)
        if success:
            message = f"Configuration updated for extension '{extension_id}'"
            logger.info(message)
            return ExtensionUpdateResponse(success=True, message=message)
        else:
            message = f"Failed to update configuration for extension '{extension_id}'"
            logger.error(message)
            return ExtensionUpdateResponse(success=False, message=message)
    except Exception as e:
        logger.error(f"Error setting extension config: {str(e)}")
        return ExtensionUpdateResponse(success=False, message=str(e))
