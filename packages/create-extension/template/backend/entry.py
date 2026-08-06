"""Minimal backend stub for a sandboxed Realms extension.

Runs in a subinterpreter with only CPython frozen/builtin modules — no ``json``.
Use plain string handling for args and return values.
"""


def _extract(args: str, key: str) -> str:
    """Read one top-level string value out of a flat JSON object."""
    marker = '"%s"' % key
    start = args.find(marker)
    if start < 0:
        return ""
    colon = args.find(":", start + len(marker))
    if colon < 0:
        return ""
    open_quote = args.find('"', colon)
    if open_quote < 0:
        return ""
    close_quote = args.find('"', open_quote + 1)
    if close_quote < 0:
        return ""
    return args[open_quote + 1 : close_quote]


def _quote(value: str) -> str:
    return '"%s"' % value.replace("\\", "\\\\").replace('"', '\\"')


def greet(args: str) -> str:
    """Return a greeting for the given name.

    Declared in manifest.json entry_access.functions and invoked from the
    frontend via ctx.callExtension('greet', { name }).

    Args:
        args: JSON string, e.g. '{"name": "Ada"}'.

    Returns:
        JSON string with the greeting, e.g. '"Hello, Ada!"'.
    """
    name = _extract(args or "", "name").strip() or "World"
    return _quote("Hello, %s!" % name)
