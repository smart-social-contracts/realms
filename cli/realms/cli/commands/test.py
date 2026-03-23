"""Test command for running codex tests locally using the mock ggg framework."""

import glob
import os
import sys
import time
import traceback

import typer
from rich.console import Console

console = Console()


def _discover_tests(path):
    """Return sorted list of test file paths."""
    if os.path.isfile(path):
        return [path]
    patterns = [
        os.path.join(path, "tests", "test_*.py"),
        os.path.join(path, "test_*.py"),
    ]
    found = []
    for pat in patterns:
        found.extend(glob.glob(pat))
    return sorted(set(found))


def _run_single_test(test_file, codex_dir, reset_fn, verbose=False):
    """Run a single test file. Returns (name, status, duration, error)."""
    import builtins
    import logging

    name = os.path.basename(test_file)
    reset_fn()

    codex_parent = os.path.dirname(test_file)
    codex_root = (
        os.path.dirname(codex_parent)
        if os.path.basename(codex_parent) == "tests"
        else codex_parent
    )
    paths_to_add = []
    if codex_root not in sys.path:
        paths_to_add.append(codex_root)
    if codex_dir not in sys.path and codex_dir != codex_root:
        paths_to_add.append(codex_dir)

    for p in paths_to_add:
        sys.path.insert(0, p)

    # Clear cached codex module imports for isolation
    modules_to_remove = [
        mod_name
        for mod_name, mod in sys.modules.items()
        if getattr(mod, "__file__", None)
        and codex_root in getattr(mod, "__file__", "")
        and mod_name != "__main__"
    ]
    for mod_name in modules_to_remove:
        del sys.modules[mod_name]

    # Provide ic and logger in the exec namespace
    logger = logging.getLogger(f"codex.test.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    ns = {
        "__builtins__": __builtins__,
        "__name__": "__main__",
        "__file__": test_file,
        "ic": builtins.ic,
        "logger": logger,
    }

    t0 = time.time()
    try:
        with open(test_file, "r") as f:
            code = f.read()
        compiled = compile(code, test_file, "exec")
        exec(compiled, ns)
        duration = time.time() - t0
        return (name, "PASSED", duration, None)
    except Exception:
        duration = time.time() - t0
        tb = traceback.format_exc()
        return (name, "FAILED", duration, tb)
    finally:
        for p in paths_to_add:
            if p in sys.path:
                sys.path.remove(p)


def test_command(
    path: str = ".",
    verbose: bool = False,
) -> None:
    """Run codex tests locally using the mock ggg framework.

    PATH can be a codices directory, a single realm directory, or a
    specific test file.  Examples::

        realms test codices/agora
        realms test codices/
        realms test codices/agora/tests/test_financial_setup.py
    """
    from realms.testing import setup_test_env, reset_registry

    path = os.path.abspath(path)

    if not os.path.exists(path):
        console.print(f"[red]❌ Path not found: {path}[/red]")
        raise typer.Exit(1)

    # Discover test files
    if os.path.isdir(path):
        test_files = _discover_tests(path)
        if not test_files:
            # Maybe it's a top-level codices dir — scan all realms
            all_tests = []
            for entry in sorted(os.listdir(path)):
                realm_path = os.path.join(path, entry)
                if os.path.isdir(realm_path) and not entry.startswith("_"):
                    realm_tests = _discover_tests(realm_path)
                    all_tests.extend(realm_tests)
            test_files = all_tests
    else:
        test_files = [path]

    if not test_files:
        console.print(f"[yellow]No test files found in {path}[/yellow]")
        raise typer.Exit(0)

    # Setup mock environment
    setup_test_env()

    codex_dir = path if os.path.isdir(path) else os.path.dirname(path)

    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print(f"  [bold cyan]Codex Test Runner[/bold cyan]")
    console.print(f"  {len(test_files)} test file(s)")
    console.print(f"[bold]{'='*60}[/bold]\n")

    passed = 0
    failed = 0

    for test_file in test_files:
        name, status, duration, error = _run_single_test(
            test_file, codex_dir, reset_registry, verbose
        )

        icon = "✅" if status == "PASSED" else "❌"
        color = "green" if status == "PASSED" else "red"
        console.print(f"  {icon} [{color}]{name}[/{color}] ({duration:.3f}s)")

        if error and (verbose or status == "FAILED"):
            for line in error.strip().split("\n"):
                console.print(f"     [dim]{line}[/dim]")

        if status == "PASSED":
            passed += 1
        else:
            failed += 1

    console.print(f"\n[bold]{'='*60}[/bold]")
    if failed:
        console.print(f"  [bold red]Results: {passed} passed, {failed} failed[/bold red]")
    else:
        console.print(f"  [bold green]Results: {passed} passed, {failed} failed[/bold green]")
    console.print(f"[bold]{'='*60}[/bold]\n")

    if failed:
        raise typer.Exit(1)
