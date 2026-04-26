# ============================================================================
# WASI stdlib compatibility patches — must run BEFORE any imports.
# ============================================================================
import sys as _wsys

import builtins as _bi
if not hasattr(_bi, 'open'):
    def _stub_open(*a, **kw):
        raise OSError("open() not available in WASI")
    _bi.open = _stub_open
del _bi

_os = _wsys.modules.get('os')
if _os is None or not hasattr(_os, 'path') or not hasattr(getattr(_os, 'path', None) or _os, 'exists'):
    if _os is None:
        _os = type(_wsys)('os')
        _os.__file__ = '<wasi-stub>'
        _os.__path__ = []
        _os.__package__ = 'os'
        _wsys.modules['os'] = _os
    class _FakePath:
        sep = '/'
        def exists(self, p): return False
        def join(self, *a): return '/'.join(a)
        def dirname(self, p): return p.rsplit('/', 1)[0] if '/' in p else ''
        def basename(self, p): return p.rsplit('/', 1)[-1]
        def isfile(self, p): return False
        def isdir(self, p): return False
        def abspath(self, p): return p
        def expanduser(self, p): return p
        def normpath(self, p): return p
        def realpath(self, p): return p
        def splitext(self, p):
            i = p.rfind('.')
            return (p[:i], p[i:]) if i > 0 else (p, '')
    _os.path = _FakePath()
    if not hasattr(_os, 'sep'): _os.sep = '/'
    if not hasattr(_os, 'getcwd'): _os.getcwd = lambda: '/'
    if not hasattr(_os, 'environ'): _os.environ = {}
    if not hasattr(_os, 'listdir'): _os.listdir = lambda p='/': []
    if not hasattr(_os, 'makedirs'): _os.makedirs = lambda p, exist_ok=False: None
    if not hasattr(_os, 'remove'): _os.remove = lambda p: None
    if not hasattr(_os, 'urandom'):
        import random as _osrnd
        _os.urandom = lambda n: bytes(_osrnd.getrandbits(8) for _ in range(n))
        del _osrnd
del _os

_dc = _wsys.modules.get('dataclasses')
if _dc and getattr(_dc, '__file__', '') == '<frozen dataclasses>':
    def _real_dataclass(cls=None, **kw):
        def _wrap(c):
            ann = {}
            for _b in reversed(c.__mro__):
                ann.update(getattr(_b, '__annotations__', {}))
            if ann and '__init__' not in c.__dict__:
                _fs = list(ann.keys())
                _ds = {n: getattr(c, n) for n in _fs if n in c.__dict__}
                def _mkinit(fs, ds):
                    def __init__(self, *args, **kwargs):
                        for i, f in enumerate(fs):
                            if i < len(args): object.__setattr__(self, f, args[i])
                            elif f in kwargs: object.__setattr__(self, f, kwargs[f])
                            elif f in ds:
                                v = ds[f]
                                object.__setattr__(self, f, v() if callable(v) else v)
                            else: raise TypeError(f"{c.__name__}() missing: '{f}'")
                    return __init__
                c.__init__ = _mkinit(_fs, _ds)
            if '__repr__' not in c.__dict__ and ann:
                _fs = list(ann.keys())
                def _mkrepr(fs):
                    def __repr__(self):
                        return f'{type(self).__name__}({", ".join(f"{f}={getattr(self, f, None)!r}" for f in fs)})'
                    return __repr__
                c.__repr__ = _mkrepr(_fs)
            return c
        return _wrap if cls is None else _wrap(cls)
    _dc.dataclass = _real_dataclass
del _dc

import traceback as _tb
if not hasattr(_tb, 'format_exc'):
    def _format_exc(limit=None, chain=True, _s=_wsys):
        ei = _s.exc_info()
        if ei[1] is None: return ''
        parts = [f'{type(ei[1]).__name__}: {ei[1]}']
        tb = ei[2]
        frames = []
        while tb:
            f = tb.tb_frame
            frames.append(f'  File "{f.f_code.co_filename}", line {tb.tb_lineno}, in {f.f_code.co_name}')
            tb = tb.tb_next
        if frames:
            parts.insert(0, 'Traceback (most recent call last):')
            for fr in frames: parts.insert(-1, fr)
        return '\n'.join(parts)
    _tb.format_exc = _format_exc
    _tb.format_exception = lambda tp, val, tb, **kw: [_format_exc()]
    _tb.print_exc = lambda **kw: print(_format_exc())
del _tb

import random as _rnd
if not hasattr(_rnd, 'getrandbits'):
    _c = [0]
    def _getrandbits(k, _c=_c):
        _c[0] += 1
        return hash((_c[0], id(_c))) & ((1 << k) - 1)
    _rnd.getrandbits = _getrandbits
    if not hasattr(_rnd, 'randint'):
        _rnd.randint = lambda a, b: a + (_getrandbits(32) % (b - a + 1))
del _rnd

import hashlib as _hl
if not hasattr(_hl, 'sha256'):
    _K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
          0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
          0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
          0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
          0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
          0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
          0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
          0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
    class _Sha256:
        def __init__(self, data=b''):
            self._h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
            self._buf, self._count = b'', 0
            if data: self.update(data)
        def _rr(self, x, n): return ((x >> n) | (x << (32 - n))) & 0xffffffff
        def _compress(self, block):
            w = [int.from_bytes(block[i:i+4], 'big') for i in range(0, 64, 4)]
            for i in range(16, 64):
                s0 = self._rr(w[i-15],7) ^ self._rr(w[i-15],18) ^ (w[i-15]>>3)
                s1 = self._rr(w[i-2],17) ^ self._rr(w[i-2],19) ^ (w[i-2]>>10)
                w.append((w[i-16]+s0+w[i-7]+s1) & 0xffffffff)
            a,b,c,d,e,f,g,h = self._h
            for i in range(64):
                S1 = self._rr(e,6)^self._rr(e,11)^self._rr(e,25)
                t1 = (h+S1+(e&f^(~e)&g)+_K[i]+w[i]) & 0xffffffff
                S0 = self._rr(a,2)^self._rr(a,13)^self._rr(a,22)
                t2 = (S0+(a&b^a&c^b&c)) & 0xffffffff
                h,g,f,e,d,c,b,a = g,f,e,(d+t1)&0xffffffff,c,b,a,(t1+t2)&0xffffffff
            for i,v in enumerate([a,b,c,d,e,f,g,h]):
                self._h[i] = (self._h[i]+v) & 0xffffffff
        def update(self, data):
            if isinstance(data, str): data = data.encode('utf-8')
            self._buf += data; self._count += len(data)
            while len(self._buf) >= 64:
                self._compress(self._buf[:64]); self._buf = self._buf[64:]
        def digest(self):
            buf = self._buf + b'\x80'
            buf += b'\x00' * ((55 - len(self._buf)) % 64)
            buf += (self._count * 8).to_bytes(8, 'big')
            h = list(self._h); tmp = _Sha256.__new__(_Sha256)
            tmp._h, tmp._buf, tmp._count = h, b'', 0
            for i in range(0, len(buf), 64): tmp._compress(buf[i:i+64])
            return b''.join(v.to_bytes(4, 'big') for v in tmp._h)
        def hexdigest(self): return self.digest().hex()
        def copy(self):
            c = _Sha256.__new__(_Sha256)
            c._h, c._buf, c._count = list(self._h), self._buf, self._count
            return c
    _hl.sha256 = lambda data=b'': _Sha256(data)
    _hl.new = lambda name, data=b'': _Sha256(data) if name == 'sha256' else None
del _hl

import math as _ma
if not hasattr(_ma, 'ceil'):
    _ma.ceil = lambda x: int(x) if x == int(x) else int(x) + (1 if x > 0 else 0)
    _ma.floor = lambda x: int(x) if x >= 0 or x == int(x) else int(x) - 1
    _ma.fabs = lambda x: x if x >= 0 else -x
    _ma.sqrt = lambda x: x ** 0.5
    _ma.pi, _ma.e = 3.141592653589793, 2.718281828459045
    _ma.inf, _ma.nan = float('inf'), float('nan')
del _ma
del _wsys
# ============================================================================
# End WASI stdlib compatibility patches
# ============================================================================

import json
import traceback

from api.credits import (
    add_user_credits, capture_deployment_hold, create_deployment_hold,
    deduct_user_credits, get_billing_status, get_user_credits,
    get_user_transactions, release_deployment_hold,
)
from api.registry import (
    count_registered_realms, get_registered_realm,
    list_registered_realms, register_realm_by_caller, remove_registered_realm,
)
from api.status import get_status
from _cdk import (
    Async, CallResult, Func, Opt, Principal, Query, Record, Service,
    StableBTreeMap, Variant, Vec, blob, float64, ic, init, match, nat,
    nat64, post_upgrade, query, service_update, text, update, void,
)
from ic_python_db import Database
from ic_python_logging import get_logger

# ── Inter-canister: realm_installer ────────────────────────────────────

class RInstallerError(Record):
    message: text
    traceback: text

class REnqueueOk(Record):
    job_id: text
    status: text
    realm_name: text
    network: text

class RResultEnqueue(Variant, total=False):
    Ok: REnqueueOk
    Err: RInstallerError

class RealmInstallerService(Service):
    @service_update
    def enqueue_deployment(self, manifest_json: text) -> RResultEnqueue: ...
    @service_update
    def cancel_deployment(self, job_id: text) -> text: ...

# ── Candid types (must be in main.py for basilisk .did generator) ──────

class UserCreditsRecord(Record):
    principal_id: text
    balance: nat64
    total_purchased: nat64
    total_spent: nat64

class CreditTransactionRecord(Record):
    id: text
    principal_id: text
    amount: nat64
    transaction_type: text
    description: text
    stripe_session_id: text
    timestamp: float64

class GetCreditsResult(Variant, total=False):
    Ok: UserCreditsRecord
    Err: text

class AddCreditsResult(Variant, total=False):
    Ok: UserCreditsRecord
    Err: text

class DeductCreditsResult(Variant, total=False):
    Ok: UserCreditsRecord
    Err: text

class TransactionHistoryResult(Variant, total=False):
    Ok: Vec[CreditTransactionRecord]
    Err: text

class RealmRecord(Record):
    id: text
    name: text
    url: text
    backend_url: text
    logo: text
    users_count: nat64
    created_at: float64
    frontend_canister_id: text

class AddRealmResult(Variant, total=False):
    Ok: text
    Err: text

class GetRealmResult(Variant, total=False):
    Ok: RealmRecord
    Err: text

class StatusRecord(Record):
    version: text
    commit: text
    commit_datetime: text
    status: text
    realms_count: nat64
    dependencies: Vec[text]
    python_version: text

class GetStatusResult(Variant, total=False):
    Ok: StatusRecord
    Err: text

class BillingStatusRecord(Record):
    users_count: nat64
    total_balance: nat64
    total_purchased: nat64
    total_spent: nat64

class GetBillingStatusResult(Variant, total=False):
    Ok: BillingStatusRecord
    Err: text

# ── Storage ────────────────────────────────────────────────────────────

storage = StableBTreeMap[str, str](memory_id=1, max_key_size=200, max_value_size=2000)
Database.init(db_storage=storage, audit_enabled=True)
logger = get_logger("main")

DEPLOYMENT_COST_CREDITS = 5
_INSTALLER_IDS = {
    "staging": "lusjm-wqaaa-aaaau-ago7q-cai",
    "demo": "2s4td-daaaa-aaaao-bazmq-cai",
    "test": "fltjm-tyaaa-aaaap-qunhq-cai",
}


def _realm_record(r: dict) -> RealmRecord:
    return RealmRecord(
        id=r.get("id", ""), name=r.get("name", ""),
        url=r.get("url", ""), backend_url=r.get("backend_url", ""),
        logo=r.get("logo", ""), users_count=int(r.get("users_count", 0)),
        created_at=float(r.get("created_at", 0.0)),
        frontend_canister_id=r.get("frontend_canister_id", ""),
    )


def _credits_record(c: dict) -> UserCreditsRecord:
    return UserCreditsRecord(
        principal_id=c["principal_id"], balance=c["balance"],
        total_purchased=c["total_purchased"], total_spent=c["total_spent"],
    )


@init
def init_canister() -> void:
    logger.info("Realm Registry canister initialized")

# ── Registry endpoints ─────────────────────────────────────────────────

@query
def status() -> GetStatusResult:
    try:
        s = get_status()
        return {"Ok": StatusRecord(
            version=s["version"], commit=s["commit"],
            commit_datetime=s["commit_datetime"], status=s["status"],
            realms_count=s["realms_count"], dependencies=s["dependencies"],
            python_version=s["python_version"],
        )}
    except Exception as e:
        return {"Err": str(e)}

@query
def list_realms() -> Vec[RealmRecord]:
    try:
        return [_realm_record(r) for r in list_registered_realms()]
    except Exception:
        return []

@update
def register_realm(name: text, url: text, logo: text,
                   backend_url: text = "", canister_ids_json: text = "{}") -> AddRealmResult:
    try:
        frontend_id = ""
        realm_id_override = ""
        if canister_ids_json and "|" in canister_ids_json:
            parts = canister_ids_json.split("|")
            frontend_id = parts[0] if len(parts) > 0 else ""
            realm_id_override = parts[3].strip() if len(parts) > 3 else ""
        elif canister_ids_json and canister_ids_json.startswith("{"):
            ids = json.loads(canister_ids_json)
            frontend_id = ids.get("frontend_canister_id", "")
            realm_id_override = ids.get("backend_canister_id", "")
        result = register_realm_by_caller(
            name, url, logo, backend_url,
            frontend_canister_id=frontend_id, realm_id_override=realm_id_override,
        )
        return {"Ok": result["message"]} if result["success"] else {"Err": result["error"]}
    except Exception as e:
        return {"Err": str(e)}

@query
def get_realm(realm_id: text) -> GetRealmResult:
    try:
        result = get_registered_realm(realm_id)
        if result["success"]:
            return {"Ok": _realm_record(result["realm"])}
        return {"Err": result["error"]}
    except Exception as e:
        return {"Err": str(e)}

@update
def remove_realm(realm_id: text) -> AddRealmResult:
    try:
        result = remove_registered_realm(realm_id)
        return {"Ok": result["message"]} if result["success"] else {"Err": result["error"]}
    except Exception as e:
        return {"Err": str(e)}

@query
def realm_count() -> nat64:
    return count_registered_realms()

# ── Credits endpoints ──────────────────────────────────────────────────

@query
def get_credits(principal_id: text) -> GetCreditsResult:
    try:
        r = get_user_credits(principal_id)
        return {"Ok": _credits_record(r["credits"])} if r["success"] else {"Err": r["error"]}
    except Exception as e:
        return {"Err": str(e)}

@update
def add_credits(principal_id: text, amount: nat64,
                stripe_session_id: text = "", description: text = "Credit top-up") -> AddCreditsResult:
    try:
        r = add_user_credits(principal_id, int(amount), stripe_session_id, description)
        return {"Ok": _credits_record(r["credits"])} if r["success"] else {"Err": r["error"]}
    except Exception as e:
        return {"Err": str(e)}

@update
def deduct_credits(principal_id: text, amount: nat64,
                   description: text = "Credit spend") -> DeductCreditsResult:
    try:
        r = deduct_user_credits(principal_id, int(amount), description)
        return {"Ok": _credits_record(r["credits"])} if r["success"] else {"Err": r["error"]}
    except Exception as e:
        return {"Err": str(e)}

@query
def get_transactions(principal_id: text, limit: nat64 = 50) -> TransactionHistoryResult:
    try:
        r = get_user_transactions(principal_id, int(limit))
        if not r["success"]:
            return {"Err": r["error"]}
        return {"Ok": [{
            "id": t["id"], "principal_id": t["principal_id"],
            "amount": abs(t["amount"]), "transaction_type": t["transaction_type"],
            "description": t["description"], "stripe_session_id": t["stripe_session_id"],
            "timestamp": float(t["timestamp"]),
        } for t in r["transactions"]]}
    except Exception as e:
        return {"Err": str(e)}

@query
def billing_status() -> GetBillingStatusResult:
    try:
        r = get_billing_status()
        if not r["success"]:
            return {"Err": r["error"]}
        b = r["billing"]
        return {"Ok": BillingStatusRecord(
            users_count=b["users_count"], total_balance=b["total_balance"],
            total_purchased=b["total_purchased"], total_spent=b["total_spent"],
        )}
    except Exception as e:
        return {"Err": str(e)}

# ── Deployment queue endpoints ─────────────────────────────────────────

@update
def request_deployment(manifest_json: text) -> Async[text]:
    try:
        caller = str(ic.caller())
        manifest = json.loads(manifest_json)
        network = manifest.get("network", "")
        realm_name = manifest.get("name", "unknown")

        cr = get_user_credits(caller)
        if not cr.get("success"):
            return json.dumps({"success": False, "error": cr.get("error", "credit check failed")})
        balance = int((cr.get("credits") or {}).get("balance", 0))
        if balance < DEPLOYMENT_COST_CREDITS:
            return json.dumps({"success": False,
                "error": f"Insufficient credits: {balance} < {DEPLOYMENT_COST_CREDITS}"})

        installer_id = _INSTALLER_IDS.get(network) or manifest.get("installer_canister_id", "")
        if not installer_id:
            return json.dumps({"success": False, "error": f"No installer for network '{network}'"})

        manifest["requesting_principal"] = caller
        manifest["registry_canister_id"] = str(ic.id())

        installer = RealmInstallerService(Principal.from_str(installer_id))
        call_result: CallResult = yield installer.enqueue_deployment(json.dumps(manifest))

        result = _unwrap_enqueue(call_result)
        if not result.get("success"):
            return json.dumps(result)

        job_id = (result.get("job_id") or "").strip()
        if not job_id:
            return json.dumps({"success": False, "error": "installer missing job_id"})

        hold = create_deployment_hold(caller, job_id, DEPLOYMENT_COST_CREDITS,
                                      f"Realm deployment: {realm_name}")
        if not hold.get("success"):
            try:
                yield installer.cancel_deployment(job_id)
            except Exception:
                pass
            return json.dumps({"success": False, "error": hold.get("error", "hold failed")})

        result["credits_held"] = DEPLOYMENT_COST_CREDITS
        result["caller"] = caller
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def _unwrap_enqueue(raw):
    v = raw
    if isinstance(v, dict):
        if v.get("Err") is not None:
            e = v["Err"]
            return {"success": False, "error": e.get("message", str(e)) if isinstance(e, dict) else str(e)}
        if "Ok" in v:
            v = v["Ok"]
    if hasattr(v, "Err") and getattr(v, "Err", None) is not None:
        e = v.Err
        return {"success": False, "error": getattr(e, "message", str(e))}
    if hasattr(v, "Ok"):
        v = v.Ok
    if isinstance(v, dict):
        if v.get("Err") is not None:
            e = v["Err"]
            return {"success": False, "error": e.get("message", str(e)) if isinstance(e, dict) else str(e)}
        if "Ok" in v:
            v = v["Ok"]
        if "job_id" in v:
            return {"success": True, **v}
    if hasattr(v, "job_id"):
        return {"success": True, "job_id": v.job_id, "status": getattr(v, "status", ""),
                "realm_name": getattr(v, "realm_name", ""), "network": getattr(v, "network", "")}
    return {"success": False, "error": f"unexpected response: {str(raw)[:200]}"}


@update
def deployment_failed(job_id: text, reason: text, caller_principal: text = "") -> text:
    try:
        release_deployment_hold(job_id, f"Failed: {reason}")
        return json.dumps({"success": True, "job_id": job_id, "settlement": "released"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@update
def deployment_succeeded(job_id: text, caller_principal: text = "") -> text:
    try:
        capture_deployment_hold(job_id, "Deployment completed")
        return json.dumps({"success": True, "job_id": job_id, "settlement": "captured"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
