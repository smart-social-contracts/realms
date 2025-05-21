#!/usr/bin/env python3
"""
Output formatting utilities for scripts.
"""

def print_success(message: str):
    """Print a success message with green checkmark."""
    print(f"✅ {message}")

def print_error(message: str):
    """Print an error message with red X."""
    print(f"❌ {message}")

def print_warning(message: str):
    """Print a warning message with yellow triangle."""
    print(f"⚠️ {message}")

def print_info(message: str):
    """Print an info message with blue circle."""
    print(f"🔍 {message}")
