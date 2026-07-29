"""In-sandbox SDK for codices (issue #265).

The SDK runs *inside* the Basilisk subinterpreter, spawned via the real
primitive ``_basilisk_sandbox.spawn_subinterpreter(source, hash)`` /
``call_in_subinterpreter(handle, fn, kwargs)``. Only plain data crosses the
boundary. The SDK follows a *gather → compute → effects* model:

  * **Reads** (``realm.config()``, ``realm.now()``, ``realm.currency()``,
    ``realm.info()``, ``realm.users.get(id)``) are served from the ``context``
    the host injected when it invoked the hook, with no round-trip. When a read
    is not in the context — a user other than the triggering one, or a key the
    hook's context spec deliberately omits — the SDK falls back to a live
    ``rpc`` call, which the host authorizes against the codex's declared read
    capabilities.

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


def _rpc(action, kwargs):
    """Call a host *read* verb through the sandbox rpc bridge.

    Returns ``(True, value)`` on success and ``(False, None)`` when no rpc
    channel exists — host-side unit tests, or a canister image predating the
    callback — so callers can fall back to the injected context.

    A denial or host-side error is *not* swallowed: if a codex asks for
    something it did not declare in ``capabilities``, the author should see the
    failure rather than silently receive ``None``. ``@hook`` turns it into a
    clean ``{"ok": False}`` envelope.
    """
    try:
        _fn = rpc  # noqa: F821 - builtin injected by the subinterpreter
    except NameError:
        return (False, None)
    if "action" in kwargs:
        # The bridge spends the name ``action`` on the verb itself, so a verb
        # kwarg of the same name would arrive as a duplicate argument. Caught
        # here rather than as a confusing TypeError from the handler.
        raise ValueError("rpc kwargs cannot contain 'action'")
    return (True, _fn(action, **kwargs))


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
        """A user projection, or ``None``.

        Served from the injected context when the host pre-gathered this user
        (the common case: the one the hook fired for), otherwise fetched live
        over ``rpc`` and memoized for repeat lookups in the same call.
        """
        users = _state.context.get("users")
        if users is None:
            users = {}
            _state.context["users"] = users
        if user_id in users:
            return users[user_id]
        ok, value = _rpc("user.get", {"user_id": user_id})
        if not ok:
            return None
        users[user_id] = value
        return value


class _Proposals:
    def find_executed(self, target_principal, profile_name, change="assign"):
        """An executed governance proposal authorizing one role change, or
        ``None``. *change* is ``"assign"`` or ``"revoke"``.

        Always a live read: an approval that landed a second ago has to count.
        """
        ok, value = _rpc("proposal.find_executed", {
            "target_principal": target_principal,
            "profile_name": profile_name,
            "change": change,
        })
        return value if ok else None


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

    def assign_profile(self, user_id, profile_name):
        """Record a ``member.assign_profile`` effect."""
        return _state.record("member.assign_profile", {
            "user_id": user_id,
            "profile_name": profile_name,
        })

    def revoke_profile(self, user_id, profile_name):
        """Record a ``member.revoke_profile`` effect."""
        return _state.record("member.revoke_profile", {
            "user_id": user_id,
            "profile_name": profile_name,
        })


class _Treasury:
    def transfer(self, to_principal, amount, treasury_name=""):
        """Record a deferred ``treasury.transfer`` effect."""
        return _state.record("treasury.transfer", {
            "to_principal": to_principal,
            "amount": amount,
            "treasury_name": treasury_name,
        })


class _Init:
    def apply_init_policy(self):
        codex_id = _state.context.get("codex_id", "")
        return _state.record("realm.apply_init_policy", {"codex_id": codex_id})

    def seed_org(self, template="departments"):
        codex_id = _state.context.get("codex_id", "")
        return _state.record("org.seed_template", {
            "codex_id": codex_id,
            "template": template,
        })

    def seed_justice(self):
        codex_id = _state.context.get("codex_id", "")
        return _state.record("justice.seed_template", {"codex_id": codex_id})


class _Realm:
    """Entry point codices import as ``realm``."""

    def __init__(self):
        self.users = _Users()
        self.proposals = _Proposals()
        self.invoices = _Invoices()
        self.notifications = _Notifications()
        self.members = _Members()
        self.treasury = _Treasury()
        self.init = _Init()

    def _read(self, key, verb, default):
        """Context value for *key*, falling back to a live ``rpc`` read.

        The host pre-gathers whatever a hook is likely to need, so the context
        hit is the normal path. The fallback matters for hooks whose context
        deliberately omits a key — notably ``get_config``, whose context cannot
        contain ``config`` without the host re-entering the very hook it is
        gathering for.
        """
        if key in _state.context:
            value = _state.context.get(key)
            return default if value is None else value
        ok, value = _rpc(verb, {})
        if not ok or value is None:
            return default
        return value

    def config(self):
        return self._read("config", "config.get", {})

    def now(self):
        return self._read("now", "time.now", {"epoch": 0, "ns": 0})

    def info(self):
        return self._read("realm", "realm.get", {})

    def currency(self):
        return self._read("currency", "currency.get", "REALMS")


realm = _Realm()

__all__ = ["hook", "realm", "iso_days_from"]
'''

exec(compile(GGG_SDK_SOURCE, "ggg_sdk.py", "exec"), globals())
