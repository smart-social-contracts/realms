"""In-sandbox SDK for codices (issue #265).

The SDK runs *inside* the Basilisk subinterpreter, spawned via the real
primitive ``_basilisk_sandbox.spawn_subinterpreter(source, hash)`` /
``call_in_subinterpreter(handle, fn, kwargs)``. That primitive is **pure
compute**: the host passes a plain-data ``context`` in and receives plain data
out — there is NO live callback channel from the sandbox back into the host. The
SDK therefore follows a *gather → compute → effects* model:

  * **Reads** (``realm.config()``, ``realm.now()``, ``realm.currency()``,
    ``realm.info()``, ``realm.users.get(id)``) are served from the ``context``
    the host injected when it invoked the hook. No host round-trip happens.

  * **Writes** (``realm.invoices.create()``, ``realm.notifications.create()``,
    ``realm.members.activate()``) do not execute inside the sandbox. They are
    *recorded* as intended effects and returned to the host, which authorizes
    each against the codex's declared ``capabilities`` and applies it through the
    public ``ggg`` API. A ``create()`` returns a light ref whose ``id`` is a
    ``$eff:<n>:id`` token; the host substitutes the real id when it applies later
    effects (and in the hook's return value), so an author can still write
    ``metadata="invoice_id:" + str(invoice["id"])`` naturally.

Example::

    from ggg_sdk import hook, iso_days_from, realm

    @hook
    def on_user_register(args):
        user = realm.users.get(args["user_id"])
        cfg = realm.config()
        now = realm.now()["epoch"]
        inv = realm.invoices.create(
            amount=cfg["fees"]["registration"], currency=realm.currency(),
            due_date=iso_days_from(now, 30), status="Pending",
            user_id=user["id"], metadata="registration invoice",
        )
        return {"success": True, "invoice_id": inv["id"]}

Trust model: the SDK is **convenience only**. All security (capability
authorization, strict plain-data serialization) is enforced host-side in
``core.codex_bridge.apply_effects``. A hostile codex may rewrite this SDK; it
still cannot make the host apply an effect for a capability it did not declare,
nor smuggle a live object across the boundary.

Why the code lives in a string constant: in the canister the realm_backend
modules are frozen to *bytecode* — there is no ``__file__``, no
``loader.get_source``, no ``inspect.getsource`` — yet the host must inject the
SDK's *source text* into each fresh subinterpreter
(``runtime_sandbox._build_codex_sandbox_source``). String constants survive
freezing, so ``GGG_SDK_SOURCE`` below is the single source of truth: the host
embeds it into the sandbox source, and this module ``exec``s it at import time
so host-side code (unit tests) can still ``import ggg_sdk`` normally. The
payload imports only the standard library so it executes unchanged inside the
subinterpreter.
"""

GGG_SDK_SOURCE = r'''
# The sandbox stdlib is minimal: only builtin (C) modules exist, so pure-Python
# stdlib like ``json`` is unavailable. The host passes hook args as an
# already-parsed dict; ``json`` is used only when a caller (host-side tests)
# passes a JSON string instead.
try:
    import json
except ImportError:
    json = None

_REF_TOKEN = "$eff:%d:%s"


class _State:
    """Per-invocation reads (``context``) and recorded writes (``effects``).

    A fresh subinterpreter runs exactly one hook call, but ``reset`` is called at
    the start of every hook anyway so host-side unit tests (which reuse the
    module) start clean.
    """

    def __init__(self):
        self.context = {}
        self.effects = []

    def reset(self, context):
        self.context = context or {}
        self.effects = []

    def record(self, verb, kwargs):
        index = len(self.effects)
        self.effects.append({"verb": verb, "kwargs": kwargs})
        return {"id": _REF_TOKEN % (index, "id")}


_state = _State()


# ---------------------------------------------------------------------------
# @hook — adapt the author's function to the sandbox hook ABI
# ---------------------------------------------------------------------------


def hook(func):
    """Adapt ``func(args: dict) -> dict|None`` to the sandbox hook ABI.

    The host calls ``name(args=<dict>, context=<dict>)`` and expects a
    plain-data envelope back::

        {"ok": bool, "error": str?, "effects": [...], "result": <func return>}

    ``args`` may also arrive as a JSON string (host-side tests / legacy
    callers); it is parsed when ``json`` is importable. Reads come from
    ``context``; writes accumulate in ``_state.effects``. Exceptions are
    stringified so a live exception never crosses the boundary.
    """

    def wrapper(args="", context=None):
        _state.reset(context)
        if isinstance(args, dict):
            params = args
        elif isinstance(args, str) and args and json is not None:
            try:
                params = json.loads(args)
            except (ValueError, TypeError):
                params = {}
        else:
            params = {}
        if not isinstance(params, dict):
            params = {}
        try:
            result = func(params)
        except Exception as exc:  # noqa: BLE001 - boundary: stringify only
            return {"ok": False, "error": str(exc), "effects": []}
        return {"ok": True, "effects": list(_state.effects), "result": result}

    wrapper.__name__ = getattr(func, "__name__", "hook")
    wrapper.__doc__ = getattr(func, "__doc__", None)
    wrapper.__wrapped__ = func
    return wrapper


# ---------------------------------------------------------------------------
# Pure helpers (no host round-trip)
# ---------------------------------------------------------------------------


def iso_days_from(epoch_seconds, days):
    """ISO-8601 ``YYYY-MM-DDTHH:MM:SS`` *days* after an epoch-seconds instant.

    Pure integer arithmetic (``datetime`` is unavailable in the sandbox);
    civil-from-days per Howard Hinnant's algorithm.
    """
    total = int(epoch_seconds) + int(days) * 86400
    days_since_epoch, rem = divmod(total, 86400)
    hh, rem = divmod(rem, 3600)
    mm, ss = divmod(rem, 60)
    z = days_since_epoch + 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    if m <= 2:
        y += 1
    return "%04d-%02d-%02dT%02d:%02d:%02d" % (y, m, d, hh, mm, ss)


# ---------------------------------------------------------------------------
# realm facade — reads from context, writes recorded as effects
# ---------------------------------------------------------------------------


class _Users:
    def get(self, user_id):
        """A user projection from the injected context, or ``None``."""
        return (_state.context.get("users") or {}).get(user_id)


class _Invoices:
    def create(self, amount, currency, due_date, status="Pending",
               user_id="", metadata=""):
        """Record an ``invoice.create`` effect; return ``{"id": <ref token>}``."""
        return _state.record("invoice.create", {
            "amount": amount, "currency": currency, "due_date": due_date,
            "status": status, "user_id": user_id, "metadata": metadata,
        })


class _Notifications:
    def create(self, topic, title, message, user_id="", **fields):
        """Record a ``notification.create`` effect."""
        kwargs = {"topic": topic, "title": title, "message": message,
                  "user_id": user_id}
        kwargs.update(fields)
        return _state.record("notification.create", kwargs)


class _Members:
    def activate(self, user_id, **fields):
        """Record a ``member.activate`` effect."""
        kwargs = {"user_id": user_id}
        kwargs.update(fields)
        return _state.record("member.activate", kwargs)


class _Realm:
    """Entry point codices import as ``realm``."""

    def __init__(self):
        self.users = _Users()
        self.invoices = _Invoices()
        self.notifications = _Notifications()
        self.members = _Members()

    def config(self):
        return _state.context.get("config", {}) or {}

    def now(self):
        return _state.context.get("now", {"epoch": 0, "ns": 0})

    def info(self):
        return _state.context.get("realm", {}) or {}

    def currency(self):
        return _state.context.get("currency", "REALMS")


realm = _Realm()

__all__ = ["hook", "realm", "iso_days_from"]
'''

exec(compile(GGG_SDK_SOURCE, "ggg_sdk.py", "exec"), globals())
