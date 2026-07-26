"""In-sandbox SDK for codices (issue #265, Workstream B).

This module runs *inside* the Basilisk subinterpreter. It gives codex authors
a pythonic surface over the raw capability bridge so they write

    from ggg_sdk import hook, realm

    @hook
    def on_user_register(args):
        user = realm.users.get(args["user_id"])
        cfg = realm.config()
        now = realm.now()["epoch"]
        realm.invoices.create(
            amount=cfg["fees"]["registration"], currency="DOM",
            due_date=iso_days_from(now, 30), status="Pending",
            user_id=user["id"], metadata="registration invoice",
        )
        return {"success": True}

instead of hand-rolling ``rpc('invoice.create', ...)`` calls.

Trust model: this SDK is **convenience only**. Every call ultimately reaches
the host through the injected ``rpc(action, **kwargs)`` builtin, and all
security (capability authorization, reserved-domain policy, strict plain-data
serialization) is enforced on the host side in ``core.codex_bridge``. A hostile
codex may ignore or rewrite this SDK entirely; doing so buys it nothing, since
the host never trusts anything the sandbox says.

The module imports only the standard library so it can execute unchanged inside
the subinterpreter. ``rpc`` is resolved as a free name at call time: inside the
sandbox it is the injected builtin; in host-side unit tests, set
``ggg_sdk.rpc = <fake>`` before calling.
"""

import json


# ---------------------------------------------------------------------------
# Raw bridge call
# ---------------------------------------------------------------------------


def _rpc(action, **kwargs):
    """Invoke a host verb. ``rpc`` is the sandbox-injected builtin (or a test
    double set on this module)."""
    return rpc(action, **kwargs)  # noqa: F821 - injected builtin inside sandbox


# ---------------------------------------------------------------------------
# @hook — adapt the JSON-string hook contract to plain dicts
# ---------------------------------------------------------------------------


def hook(func):
    """Adapt ``func(args: dict) -> dict|None`` to the codex hook ABI.

    Core calls hooks as ``name(args_json_str) -> json_str``. This decorator
    parses the incoming JSON to a dict, calls the author's function, and
    serializes the result back to a JSON string. Exceptions are turned into a
    ``{"success": False, "error": ...}`` JSON string so a failing hook never
    leaks a live exception across the boundary.
    """

    def wrapper(args=""):
        try:
            params = json.loads(args) if args else {}
        except (ValueError, TypeError):
            params = {}
        try:
            result = func(params)
        except Exception as exc:  # noqa: BLE001 - boundary: stringify only
            return json.dumps({"success": False, "error": str(exc)})
        if result is None:
            result = {"success": True}
        return json.dumps(result)

    wrapper.__name__ = getattr(func, "__name__", "hook")
    wrapper.__doc__ = getattr(func, "__doc__", None)
    wrapper.__wrapped__ = func
    return wrapper


# ---------------------------------------------------------------------------
# Pure helpers (no host round-trip)
# ---------------------------------------------------------------------------


def iso_days_from(epoch_seconds, days):
    """ISO-8601 ``YYYY-MM-DDTHH:MM:SS`` *days* after an epoch-seconds instant.

    Pure arithmetic (no host time utilities), so it runs inside the sandbox.
    """
    import datetime

    dt = datetime.datetime.utcfromtimestamp(int(epoch_seconds) + int(days) * 86400)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# realm facade — namespaced verb wrappers
# ---------------------------------------------------------------------------


class _Users:
    def get(self, user_id):
        return _rpc("user.get", user_id=user_id)


class _Invoices:
    def create(self, amount, currency, due_date, status="Pending",
               user_id="", metadata=""):
        return _rpc(
            "invoice.create", amount=amount, currency=currency,
            due_date=due_date, status=status, user_id=user_id, metadata=metadata,
        )


class _Notifications:
    def create(self, topic, title, message, user_id="", **fields):
        return _rpc(
            "notification.create", topic=topic, title=title, message=message,
            user_id=user_id, **fields,
        )


class _Members:
    def activate(self, user_id, **fields):
        return _rpc("member.activate", user_id=user_id, **fields)


class _Realm:
    """Entry point codices import as ``realm``."""

    def __init__(self):
        self.users = _Users()
        self.invoices = _Invoices()
        self.notifications = _Notifications()
        self.members = _Members()

    def config(self):
        return _rpc("config.get")

    def now(self):
        return _rpc("time.now")

    def info(self):
        return _rpc("realm.get")

    def currency(self):
        return _rpc("currency.get")


realm = _Realm()

__all__ = ["hook", "realm", "iso_days_from"]
