"""
Realms SDK - registry module

Provides async functions for interacting with realm registries from workstation-side Python code.

Usage:
    from realms import registry
    
    realms = await registry.list()
    await registry.register(realm_id, folder)
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional


async def _run_command(cmd: list[str], cwd: Optional[str] = None) -> dict:
    """Run a command asynchronously and return parsed JSON output or raw result."""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nError: {stderr.decode()}")
    
    output = stdout.decode().strip()
    
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"raw": output}


async def list_realms(network: str = "local") -> list:
    """
    List all registered realms.
    
    Args:
        network: Target network
        
    Returns:
        List of registered realms
    """
    cmd = ["realms", "registry", "list", "-n", network]
    result = await _run_command(cmd)
    return result.get("realms", []) if isinstance(result, dict) else result


async def register(
    realm_id: str,
    folder: str,
    network: str = "local"
) -> dict:
    """
    Register a realm with the registry.
    
    Args:
        realm_id: Unique realm identifier
        folder: Path to the realm folder
        network: Target network
        
    Returns:
        Registration result
    """
    cmd = ["realms", "registry", "register", realm_id, "-f", folder, "-n", network]
    return await _run_command(cmd)


async def get(realm_id: str, network: str = "local") -> dict:
    """
    Get information about a registered realm.
    
    Args:
        realm_id: Realm identifier
        network: Target network
        
    Returns:
        Realm information
    """
    cmd = ["realms", "registry", "get", realm_id, "-n", network]
    return await _run_command(cmd)
