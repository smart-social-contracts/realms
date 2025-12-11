"""
Realms SDK - mundus module

Provides async functions for interacting with mundus (realm networks) from workstation-side Python code.

Usage:
    from realms import mundus
    
    await mundus.create(deploy=True)
    await mundus.status()
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


async def create(
    deploy: bool = False,
    network: str = "local",
    name: Optional[str] = None,
) -> str:
    """
    Create a new mundus (realm network).
    
    Args:
        deploy: If True, deploy the mundus after creation
        network: Target network (local, ic, staging)
        name: Name of the mundus
        
    Returns:
        Path to the created mundus folder or status
    """
    cmd = ["realms", "mundus", "create", "--network", network]
    
    if deploy:
        cmd.append("--deploy")
    if name:
        cmd.extend(["--name", name])
    
    result = await _run_command(cmd)
    return result.get("folder", result.get("raw", ""))


async def status(folder: Optional[str] = None, network: str = "local") -> dict:
    """
    Get the status of a mundus.
    
    Args:
        folder: Path to the mundus folder
        network: Target network
        
    Returns:
        Mundus status information
    """
    cmd = ["realms", "mundus", "status", "-n", network]
    if folder:
        cmd.extend(["-f", folder])
    return await _run_command(cmd)


async def deploy(folder: str, network: str = "local") -> dict:
    """
    Deploy a mundus.
    
    Args:
        folder: Path to the mundus folder
        network: Target network
        
    Returns:
        Deployment result
    """
    cmd = ["realms", "mundus", "deploy", "-f", folder, "-n", network]
    return await _run_command(cmd)
