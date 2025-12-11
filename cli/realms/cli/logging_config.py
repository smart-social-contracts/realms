"""Logging configuration for Realms CLI."""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(
    level: str = "INFO", log_file: Optional[str] = None, verbose: bool = False
) -> logging.Logger:
    """Setup logging configuration for Realms CLI."""

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger("realms_cli")
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler with Rich formatting
    console_handler = RichHandler(
        console=console,
        show_time=verbose,
        show_path=verbose,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(numeric_level)

    # Format for console output
    console_format = "%(message)s"
    if verbose:
        console_format = "[%(name)s] %(message)s"

    console_handler.setFormatter(logging.Formatter(console_format))
    logger.addHandler(console_handler)

    # File handler if log file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)  # Always debug level for file

        file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        file_handler.setFormatter(logging.Formatter(file_format))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "realms_cli") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class CLIError(Exception):
    """Base exception for CLI errors."""

    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)


class ConfigurationError(CLIError):
    """Configuration-related errors."""

    pass


class DeploymentError(CLIError):
    """Deployment-related errors."""

    pass


class DependencyError(CLIError):
    """Dependency-related errors."""

    pass


class ExtensionError(CLIError):
    """Extension-related errors."""

    pass


def handle_error(error: Exception, logger: Optional[logging.Logger] = None) -> int:
    """Handle errors and return appropriate exit code."""

    if logger is None:
        logger = get_logger()

    if isinstance(error, CLIError):
        logger.error(f"[red]{error.message}[/red]")
        return error.exit_code

    elif isinstance(error, KeyboardInterrupt):
        logger.info("[yellow]Operation cancelled by user[/yellow]")
        return 130

    elif isinstance(error, FileNotFoundError):
        logger.error(f"[red]File not found: {error.filename}[/red]")
        return 2

    elif isinstance(error, PermissionError):
        logger.error(f"[red]Permission denied: {error.filename}[/red]")
        return 13

    else:
        logger.error(f"[red]Unexpected error: {error}[/red]")
        logger.debug("Full traceback:", exc_info=True)
        return 1
