#!/usr/bin/env python3
"""
Command execution utilities for scripts.
"""

import subprocess
import sys
import os
from typing import Tuple, Optional

# Add scripts directory to path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.utils.output import print_error

def run_command(command: str) -> Tuple[bool, Optional[str]]:
    """
    Run a shell command and return its output.
    
    Args:
        command: The shell command to execute
        
    Returns:
        Tuple containing:
            - Boolean success status
            - Command output (if successful) or None (if failed)
    """
    print(f"Running: {command}")
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        print_error(f"Error executing command: {command}")
        print_error(f"Error: {process.stderr}")
        return False, None
    output = process.stdout.strip()
    print(f"Output: {output}")
    return True, output
