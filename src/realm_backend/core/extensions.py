from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from kybra import StableBTreeMap, StableCell, ic
from kybra_simple_logging import get_logger

logger = get_logger("core.extensions")

# Stable storage for extension configuration
extension_config_storage = StableBTreeMap[str, Dict[str, Any]](0, 65536, None)


class ExtensionPermission(Enum):
    READ_VAULT = "read_vault"  # Permission to read vault data
    TRANSFER_TOKENS = "transfer_tokens"  # Permission to transfer tokens
    READ_REALM = "read_realm"  # Permission to read realm data
    MODIFY_REALM = "modify_realm"  # Permission to modify realm data
    READ_ORGANIZATION = "read_organization"  # Permission to read organization data
    MODIFY_ORGANIZATION = (
        "modify_organization"  # Permission to modify organization data
    )


class Extension:
    """Base class for all backend extensions"""

    def __init__(
        self,
        name: str,
        description: str,
        required_permissions: List[ExtensionPermission],
    ):
        self.name = name
        self.description = description
        self.required_permissions = required_permissions
        self.entry_points: Dict[str, Callable] = {}
        logger.info(f"Initializing extension: {name}")

    def register_entry_point(self, name: str, func: Callable) -> None:
        """Register an entry point function for this extension"""
        self.entry_points[name] = func
        logger.info(f"Registered entry point '{name}' for extension '{self.name}'")

    async def call(self, entry_point: str, *args, **kwargs) -> Any:
        """Call an entry point of this extension"""
        if entry_point not in self.entry_points:
            logger.error(
                f"Entry point '{entry_point}' not found in extension '{self.name}'"
            )
            raise ValueError(f"Entry point '{entry_point}' not found")

        logger.info(f"Calling entry point '{entry_point}' for extension '{self.name}'")
        func = self.entry_points[entry_point]

        # Check if the function is a coroutine function (async)
        import inspect

        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)


class ExtensionRegistry:
    """Registry for managing extensions"""

    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExtensionRegistry, cls).__new__(cls)
            cls._instance.extensions = {}
            cls._instance.permissions = {}  # Maps extension_name -> granted_permissions
        return cls._instance

    def register_extension(self, extension: Extension) -> None:
        """Register an extension"""
        if extension.name in self.extensions:
            logger.warning(
                f"Extension '{extension.name}' already registered, replacing"
            )

        self.extensions[extension.name] = extension
        logger.info(f"Registered extension: {extension.name}")

    def grant_permission(
        self, extension_name: str, permission: ExtensionPermission
    ) -> None:
        """Grant a permission to an extension"""
        if extension_name not in self.extensions:
            logger.error(f"Extension '{extension_name}' not found")
            raise ValueError(f"Extension '{extension_name}' not found")

        if extension_name not in self.permissions:
            self.permissions[extension_name] = set()

        self.permissions[extension_name].add(permission)
        logger.info(
            f"Granted permission '{permission.value}' to extension '{extension_name}'"
        )

    def has_permission(
        self, extension_name: str, permission: ExtensionPermission
    ) -> bool:
        """Check if an extension has a specific permission"""
        if extension_name not in self.extensions:
            return False
            
        # Check if extension is enabled
        if not self.is_extension_enabled(extension_name):
            logger.info(f"Extension '{extension_name}' is disabled")
            return False

        return (
            extension_name in self.permissions
            and permission in self.permissions[extension_name]
        )
        
    def is_extension_enabled(self, extension_name: str) -> bool:
        """Check if an extension is enabled"""
        if extension_name not in self.extensions:
            return False
            
        # Get extension configuration
        config = extension_config_storage.get(extension_name)
        if config is not None and "enabled" in config.value:
            return config.value["enabled"]
            
        # Default to enabled if no configuration exists
        return True
        
    def set_extension_enabled(self, extension_name: str, enabled: bool) -> bool:
        """Enable or disable an extension"""
        if extension_name not in self.extensions:
            logger.error(f"Extension '{extension_name}' not found")
            return False
            
        # Get existing config or create new
        config = extension_config_storage.get(extension_name)
        if config is None:
            config_data = {"enabled": enabled}
        else:
            config_data = config.value
            config_data["enabled"] = enabled
            
        # Save configuration
        extension_config_storage.insert(extension_name, config_data)
        logger.info(f"Extension '{extension_name}' {'enabled' if enabled else 'disabled'}")
        return True
        
    def get_extension_config(self, extension_name: str) -> Dict[str, Any]:
        """Get extension configuration"""
        if extension_name not in self.extensions:
            return {}
            
        config = extension_config_storage.get(extension_name)
        return config.value if config is not None else {}
        
    def set_extension_config(self, extension_name: str, config_data: Dict[str, Any]) -> bool:
        """Set extension configuration"""
        if extension_name not in self.extensions:
            logger.error(f"Extension '{extension_name}' not found")
            return False
            
        # Get existing config or create new
        config = extension_config_storage.get(extension_name)
        if config is None:
            new_config = config_data
        else:
            new_config = config.value
            # Update with new values, preserving enabled state
            enabled = new_config.get("enabled", True)
            new_config.update(config_data)
            new_config["enabled"] = enabled
            
        # Save configuration
        extension_config_storage.insert(extension_name, new_config)
        logger.info(f"Updated configuration for extension '{extension_name}'")
        return True

    def get_extension(self, name: str) -> Optional[Extension]:
        """Get an extension by name"""
        return self.extensions.get(name)

    def list_extensions(self) -> List[Dict[str, Any]]:
        """List all registered extensions with their metadata"""
        result = []
        for ext in self.extensions.values():
            # Get extension configuration
            config = extension_config_storage.get(ext.name)
            enabled = True
            settings = {}
            
            if config is not None:
                enabled = config.value.get("enabled", True)
                settings = {k: v for k, v in config.value.items() if k != "enabled"}
            
            result.append({
                "name": ext.name,
                "description": ext.description,
                "required_permissions": [p.value for p in ext.required_permissions],
                "granted_permissions": [
                    p.value for p in self.permissions.get(ext.name, set())
                ],
                "entry_points": list(ext.entry_points.keys()),
                "enabled": enabled,
                "settings": settings
            })
        
        return result


# Singleton instance for global access
extension_registry = ExtensionRegistry()


async def call_extension(extension_name: str, entry_point: str, *args, **kwargs) -> Any:
    """Call an entry point of an extension with permission checking"""
    extension = extension_registry.get_extension(extension_name)
    if not extension:
        logger.error(f"Extension '{extension_name}' not found")
        raise ValueError(f"Extension '{extension_name}' not found")

    # Check if all required permissions are granted
    for permission in extension.required_permissions:
        if not extension_registry.has_permission(extension_name, permission):
            logger.error(
                f"Extension '{extension_name}' lacks required permission: {permission.value}"
            )
            raise PermissionError(
                f"Extension lacks required permission: {permission.value}"
            )

    return await extension.call(entry_point, *args, **kwargs)
