from typing import Any, Callable, Dict, List, Optional
import inspect

from kybra import Record
from kybra_simple_logging import get_logger
from kybra_simple_db import query_all

from ggg.extension import Extension
from ggg.permission import Permission

logger = get_logger("core.extensions")


class ExtensionRegistry:
    """Registry for managing extensions"""

    _instance = None  # Singleton instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExtensionRegistry, cls).__new__(cls)
            cls._instance._entry_points = {}  # Maps extension_name -> entry point functions
        return cls._instance

    def register_extension(self, name: str, description: str, required_permissions: List[str]) -> None:
        """Register an extension"""
        # Get or create extension
        ext = Extension[name] or Extension(_id=name, description=description, enabled=True)
        
        # Update description if it exists
        if ext.description != description:
            ext.description = description
            
        # Set required permissions
        for perm_name in required_permissions:
            perm = Permission[perm_name] or Permission(_id=perm_name, description=f"Permission for {perm_name}")
            ext.required_permissions.add(perm)
        
        # Initialize entry points registry
        self._entry_points.setdefault(name, {})
        
        logger.info(f"Registered extension: {name}")

    def register_entry_point(self, extension_name: str, entry_point_name: str, func: Callable) -> None:
        """Register an entry point function for an extension"""
        # Ensure extension exists
        if Extension[extension_name] is None:
            raise ValueError(f"Extension '{extension_name}' not found in database")
            
        # Initialize if needed
        self._entry_points.setdefault(extension_name, {})
        
        # Store entry point
        self._entry_points[extension_name][entry_point_name] = func
        logger.info(f"Registered entry point '{entry_point_name}' for extension '{extension_name}'")

    def grant_permission(self, extension_name: str, permission_name: str) -> None:
        """Grant a permission to an extension"""
        ext = Extension[extension_name]
        if not ext:
            raise ValueError(f"Extension '{extension_name}' not found")
            
        perm = Permission[permission_name] or Permission(_id=permission_name, description=f"Permission for {permission_name}")
        ext.granted_permissions.add(perm)
        logger.info(f"Granted permission '{permission_name}' to extension '{extension_name}'")

    def has_permission(self, extension_name: str, permission_name: str) -> bool:
        """Check if an extension has a specific permission"""
        ext = Extension[extension_name]
        if not ext or not ext.enabled:
            return False
            
        return any(perm._id == permission_name for perm in ext.granted_permissions)


# Singleton instance for global access
extension_registry = ExtensionRegistry()


async def call_extension(extension_name: str, entry_point: str, *args, **kwargs) -> Any:
    """Call an entry point of an extension with permission checking"""
    # Check extension exists and is enabled
    ext = Extension[extension_name]
    if not ext.enabled:
        raise ValueError(f"Extension '{extension_name}' is disabled")
    
    # Get entry points
    entry_points = extension_registry._entry_points.get(extension_name, {})
    if entry_point not in entry_points:
        raise ValueError(f"Entry point '{entry_point}' not found in extension '{extension_name}'")
    
    # Get function and call it
    func = entry_points[entry_point]
    logger.info(f"Calling entry point '{entry_point}' of extension '{extension_name}'")
    
    # Call appropriately based on function type
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)
