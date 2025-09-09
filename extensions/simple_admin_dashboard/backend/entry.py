"""
Simple Admin Dashboard Backend Extension Entry Point
Provides basic administrative operations for the GGG system.
"""

import json
import traceback

from kybra_simple_logging import get_logger

logger = get_logger("extensions.simple_admin_dashboard")


def extension_sync_call(method_name: str, args: dict):
    """
    Synchronous extension API calls for simple admin operations
    """
    methods = {
        "get_status": (get_status, False),
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
        logger.error(f"Error calling {method_name}: {str(e)}\n{traceback.format_exc()}")
        return {"success": False, "error": f"Error calling {method_name}: {str(e)}"}


def get_status():
    """
    Get extension status
    """
    return {
        "success": True,
        "data": {
            "extension": "simple_admin_dashboard",
            "status": "active",
            "version": "1.0.0",
        },
    }
