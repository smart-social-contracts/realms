"""Static import scanner for codex packages (issue #265, Workstream A).

A codex may call the realm only through the public ``ggg`` facade. Reaching
into ``core.*`` or a private ``ggg`` submodule couples legislation to host
internals that can change without notice, and — once codices run sandboxed
(issue #265, Workstream C) — such imports fail outright. This scanner finds
those imports at install time by parsing each ``.py`` file's AST.

Enforcement policy (issue #265):

* **Warn mode** (Phase 1, current): violations are logged, never rejected.
  Legacy codices (no ``ggg_api_version`` in the manifest) always run in warn
  mode so existing packages keep installing unchanged.
* **Hard-fail mode** (later phase): the same violations become an install
  error. A codex that declares ``ggg_api_version`` opts in to enforcement.

The scanner is intentionally conservative: it flags only *imports*, uses the
AST (never executes codex code), and ignores relative imports (a codex's own
sibling modules).
"""

import ast
from typing import Dict, List, NamedTuple

from ic_python_logging import get_logger

logger = get_logger("core.codex_scan")

# Top-level packages a codex must never import from directly.
_FORBIDDEN_ROOTS = ("core",)

# Only the public ``ggg`` facade is allowed: ``import ggg`` / ``from ggg import
# X``. A dotted path (``ggg.system.user_profile``) reaches private internals.
_GGG_ROOT = "ggg"


class Violation(NamedTuple):
    filename: str
    lineno: int
    statement: str
    reason: str


def _module_forbidden(module: str) -> str:
    """Return a human reason if importing *module* is disallowed, else ''."""
    if not module:
        return ""
    root = module.split(".")[0]
    if root in _FORBIDDEN_ROOTS:
        return (
            f"imports host-internal '{module}'; call the realm through the "
            f"public 'ggg' API instead"
        )
    if root == _GGG_ROOT and "." in module:
        return (
            f"imports private '{module}'; use the public 'ggg' facade "
            f"(e.g. 'from ggg import ...') instead"
        )
    return ""


def scan_source(filename: str, source: str) -> List[Violation]:
    """Parse one source string and return its import-policy violations."""
    violations: List[Violation] = []
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        logger.warning(f"codex_scan: {filename} failed to parse ({e}); skipping")
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                reason = _module_forbidden(alias.name)
                if reason:
                    violations.append(
                        Violation(filename, node.lineno, f"import {alias.name}", reason)
                    )
        elif isinstance(node, ast.ImportFrom):
            # Relative imports (``from . import x``) are a codex's own siblings.
            if node.level and node.level > 0:
                continue
            module = node.module or ""
            reason = _module_forbidden(module)
            if reason:
                names = ", ".join(a.name for a in node.names)
                violations.append(
                    Violation(
                        filename, node.lineno, f"from {module} import {names}", reason
                    )
                )
    return violations


def scan_codex_files(files: Dict[str, str]) -> List[Violation]:
    """Scan every ``.py`` file in a codex package's ``{filename: content}`` map."""
    violations: List[Violation] = []
    for filename, content in (files or {}).items():
        if not isinstance(filename, str) or not filename.endswith(".py"):
            continue
        if not isinstance(content, str):
            continue
        violations.extend(scan_source(filename, content))
    return violations


def check_codex_imports(ext_id: str, files: Dict[str, str], enforce: bool) -> str:
    """Scan *files* and report violations.

    Logs every violation. When ``enforce`` is True and any violation exists,
    returns an error string (the install gate turns this into a hard reject);
    otherwise returns "" (warn mode).
    """
    violations = scan_codex_files(files)
    for v in violations:
        logger.warning(
            f"codex_scan[{ext_id}]: {v.filename}:{v.lineno}: {v.statement} — {v.reason}"
        )
    if not violations:
        return ""
    if enforce:
        first = violations[0]
        return (
            f"Codex '{ext_id}' violates the GGG import policy: "
            f"{first.filename}:{first.lineno}: {first.statement} — {first.reason} "
            f"({len(violations)} violation(s) total). Codices may import only the "
            f"public 'ggg' API."
        )
    logger.warning(
        f"codex_scan[{ext_id}]: {len(violations)} import-policy warning(s); these "
        f"become hard errors once the codex declares 'ggg_api_version' or sandbox "
        f"enforcement is enabled (issue #265)"
    )
    return ""
