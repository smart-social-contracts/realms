import os
import subprocess

"""
ANSI color codes for terminal output.
"""

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def print_ok(message):
    """
    Print a success message with green checkmark.

    Args:
        message (str): The success message to print
    """
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message):
    """
    Print an error message with red cross.

    Args:
        message (str): The error message to print
    """
    print(f"{RED}✗ {message}{RESET}")


def run_command(command):
    """Run a shell command and return its output."""
    print(f"Running: {command}")
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        print_error(f"Error executing command: {command}")
        print_error(f"Error: {process.stderr}")
        return None
    return process.stdout.strip()


def assert_in(text, substring):
    if substring not in text:
        raise AssertionError(f"Substring '{substring}' not found in text: {text}")
    print_ok(f"Substring '{substring}' found in text: {text}")


def assert_file_exists(file_path):
    if not os.path.exists(file_path):
        raise AssertionError(f"File '{file_path}' does not exist")
    print_ok(f"File '{file_path}' exists")
