#!/usr/bin/env python3

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List, NoReturn, Optional

import ggg.utils as utils  # gotten = utils.parse_dfx_answer(gotten)
import requests
from requests.exceptions import RequestException

# Configuration
LOCAL_PORT = 8000
CANISTER_NAME = "canister_main"
EXECUTION_FUNCTION = "run_code"
GET_UNIVERSE_FUNCTION = "get_universe"


@dataclass
class Config:
    """Configuration for command execution."""

    use_ic: bool = False
    use_http: bool = False
    verbose: bool = False


class CommandError(Exception):
    """Base exception for command errors."""

    pass


# TODO: add `get_code` and `set_code` functions, to get/set the extension code of organizations/tokens
# TODO: add `realm add`, `realm ls` functionalities


def print_usage() -> None:
    """Print usage information."""
    print("Usage: ggg [--ic] [--http] [--verbose] <command> [args]\n")
    print("Commands:")
    print("  get_universe        Fetch universe data")
    print("  run_code <file>     Execute a Python script")
    print("  get_token <id>      Get token data by ID")
    print("  list_tokens         List all tokens")
    print("  parse_dfx <file>    Parse a dfx answer from a file")
    print("\nOptions:")
    print(
        "  --ic      Enable Internet Computer-specific mode (you can customize behavior for this flag)."
    )
    print(
        "  --http    Use an off-chain server instead of dfx (localhost:%s)" % LOCAL_PORT
    )
    print(
        "  --verbose Enable verbose output (shows additional information and comments)"
    )


def parse_args() -> tuple[Config, List[str]]:
    """Parse command line arguments.

    Returns:
        Tuple of (Config, remaining arguments)
    """
    config = Config()
    args = sys.argv[1:]

    while args and args[0].startswith("--"):
        flag = args.pop(0)
        if flag == "--http":
            config.use_http = True
            config.use_ic = False
        elif flag == "--ic":
            config.use_http = False
            config.use_ic = True
        elif flag == "--verbose":
            config.verbose = True
        else:
            print(f"Error: Unknown flag '{flag}'")
            print_usage()
            sys.exit(1)

    return config, args


def handle_http_request(
    method: str, endpoint: str, data: Optional[bytes] = None
) -> str:
    """Handle HTTP request to local server.

    Args:
        method: HTTP method (GET or POST)
        endpoint: Server endpoint
        data: Optional data for POST requests

    Returns:
        Server response text

    Raises:
        CommandError: If request fails
    """
    url = f"http://localhost:{LOCAL_PORT}/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        else:
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            return response.text
        else:
            raise CommandError(
                f"Server returned status code {response.status_code}: {response.text}"
            )
    except RequestException as e:
        raise CommandError(f"Unable to connect to the server: {e}")


def handle_dfx_command(command: str, input_data: Optional[str] = None) -> str:
    """Execute dfx command.

    Args:
        command: Command to execute
        input_data: Optional input data

    Returns:
        Command output

    Raises:
        CommandError: If command fails
    """
    try:
        result = subprocess.run(
            ["dfx", "canister", "call", CANISTER_NAME, command],
            input=input_data,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise CommandError(f"Command failed with exit code {result.returncode}")
        return result.stdout
    except FileNotFoundError:
        raise CommandError(
            "'dfx' command not found. Make sure DFX is installed and in your PATH."
        )


def get_universe(config: Config) -> None:
    """Handle get_universe command."""
    if config.verbose:
        print("Fetching universe data...")

    try:
        if config.use_http:
            result = handle_http_request("GET", GET_UNIVERSE_FUNCTION)
        else:
            result = handle_dfx_command(GET_UNIVERSE_FUNCTION)
        print(result)
    except CommandError as e:
        print(f"Error: {e}")
        sys.exit(1)


def get_token(config: Config, token_id: str) -> None:
    """Handle get_token command.

    Args:
        config: Command configuration
        token_id: Token ID to fetch data for
    """
    try:
        if config.verbose:
            print(f"Fetching data for token {token_id}...")

        response = handle_http_request("GET", f"api/v1/tokens/{token_id}")
        print(response)
    except CommandError as e:
        print(f"Error: {e}")
        sys.exit(1)


def run_code(config: Config, script_path: str) -> None:
    """Handle run_code command.

    Args:
        config: Command configuration
        script_path: Path to script file
    """
    if not os.path.isfile(script_path):
        print(f"Error: File '{script_path}' not found.")
        sys.exit(1)

    if config.verbose:
        print(f"Executing script: {script_path}")

    try:
        if config.use_http:
            with open(script_path, "rb") as file:
                result = handle_http_request("POST", EXECUTION_FUNCTION, file.read())
        else:
            with open(script_path, "r") as file:
                result = handle_dfx_command(EXECUTION_FUNCTION, file.read())
        print(result)
    except CommandError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except IOError as e:
        print(f"Error reading script file: {e}")
        sys.exit(1)


def list_tokens(config: Config) -> None:
    """Handle list_tokens command.

    Args:
        config: Command configuration
    """
    try:
        if config.verbose:
            print("Fetching list of all tokens...")

        response = handle_http_request("GET", "api/v1/tokens")
        print(response)
    except CommandError as e:
        print(f"Error: {e}")
        sys.exit(1)


def parse_dfx(config: Config, file_path: str) -> None:
    """Handle parse_dfx command.

    Args:
        config: Command configuration
        file_path: Path to file containing dfx answer
    """
    try:
        with open(file_path, "r") as f:
            content = f.read()

        if config.verbose:
            print(f"Reading dfx answer from {file_path}")

        parsed = json.dumps(utils.parse_dfx_answer(content))
        print(parsed)

    except FileNotFoundError:
        raise CommandError(f"File not found: {file_path}")
    except Exception as e:
        raise CommandError(f"Failed to parse dfx answer: {str(e)}")


def handle_command(config: Config, args: List[str]) -> None:
    """Handle command execution.

    Args:
        config: Command configuration
        args: Command arguments
    """
    if not args:
        print_usage()
        sys.exit(1)

    command = args[0]
    if command == "get_universe":
        get_universe(config)
    elif command == "run_code":
        if len(args) < 2:
            raise CommandError("Missing script path")
        run_code(config, args[1])
    elif command == "get_token":
        if len(args) < 2:
            raise CommandError("Missing token ID")
        get_token(config, args[1])
    elif command == "list_tokens":
        list_tokens(config)
    elif command == "parse_dfx":
        if len(args) < 2:
            raise CommandError("Missing file path")
        parse_dfx(config, args[1])
    else:
        raise CommandError(f"Unknown command: {command}")


def main() -> None:
    """Main entry point."""
    try:
        config, args = parse_args()
        handle_command(config, args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
