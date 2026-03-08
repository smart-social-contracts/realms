# ============================================================================
# WASI stdlib compatibility patches
# Must run BEFORE any imports that trigger lazy module loads.
# These fix stub modules created by basilisk's _wasi_safe_import hook.
# TODO: move these into basilisk frozen_stdlib_preamble.py in a future release.
# ============================================================================
import sys as _wsys

# -- 0a. builtins.open: not available in WASI (no filesystem) --
import builtins as _bi
if not hasattr(_bi, 'open'):
    def _stub_open(*a, **kw):
        raise OSError("open() not available in WASI (no filesystem)")
    _bi.open = _stub_open
del _bi

# -- 0b. os / os.path: create stub BEFORE real os.py loads (it crashes in WASI) --
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
    if not hasattr(_os, 'sep'):
        _os.sep = '/'
    if not hasattr(_os, 'getcwd'):
        _os.getcwd = lambda: '/'
    if not hasattr(_os, 'environ'):
        _os.environ = {}
    if not hasattr(_os, 'listdir'):
        _os.listdir = lambda p='/': []
    if not hasattr(_os, 'makedirs'):
        _os.makedirs = lambda p, exist_ok=False: None
    if not hasattr(_os, 'remove'):
        _os.remove = lambda p: None
    if not hasattr(_os, 'urandom'):
        import random as _osrnd
        _os.urandom = lambda n: bytes(_osrnd.getrandbits(8) for _ in range(n))
        del _osrnd
del _os

# -- 1. dataclasses: stub is a no-op, must generate __init__/__repr__ --
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
                            if i < len(args):
                                object.__setattr__(self, f, args[i])
                            elif f in kwargs:
                                object.__setattr__(self, f, kwargs[f])
                            elif f in ds:
                                v = ds[f]
                                object.__setattr__(self, f, v() if callable(v) else v)
                            else:
                                raise TypeError(f"{c.__name__}() missing required argument: '{f}'")
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

# -- 2. traceback: stub has no format_exc/format_exception/print_exc --
import traceback as _tb
if not hasattr(_tb, 'format_exc'):
    def _format_exc(limit=None, chain=True, _s=_wsys):
        ei = _s.exc_info()
        if ei[1] is None:
            return ''
        parts = [f'{type(ei[1]).__name__}: {ei[1]}']
        tb = ei[2]
        frames = []
        while tb:
            f = tb.tb_frame
            frames.append(f'  File "{f.f_code.co_filename}", line {tb.tb_lineno}, in {f.f_code.co_name}')
            tb = tb.tb_next
        if frames:
            parts.insert(0, 'Traceback (most recent call last):')
            for fr in frames:
                parts.insert(-1, fr)
        return '\n'.join(parts)
    _tb.format_exc = _format_exc
    _tb.format_exception = lambda tp, val, tb, **kw: [_format_exc()]
    _tb.print_exc = lambda **kw: print(_format_exc())
del _tb

# -- 3. random: frozen module may lack getrandbits (C ext _random missing) --
import random as _rnd
if not hasattr(_rnd, 'getrandbits'):
    _rnd_counter = [0]
    def _getrandbits(k, _c=_rnd_counter):
        _c[0] += 1
        v = hash((_c[0], id(_c))) & ((1 << k) - 1)
        return v
    _rnd.getrandbits = _getrandbits
    if not hasattr(_rnd, 'randint'):
        _rnd.randint = lambda a, b: a + (_getrandbits(32) % (b - a + 1))
del _rnd

# -- 4. hashlib: stub has no sha256 -- pure Python SHA-256 --
import hashlib as _hl
if not hasattr(_hl, 'sha256'):
    _K256 = [
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
    ]
    class _Sha256:
        def __init__(self, data=b''):
            self._h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
            self._buf = b''
            self._count = 0
            if data:
                self.update(data)
        def _rr(self, x, n):
            return ((x >> n) | (x << (32 - n))) & 0xffffffff
        def _compress(self, block):
            w = [int.from_bytes(block[i:i+4], 'big') for i in range(0, 64, 4)]
            for i in range(16, 64):
                s0 = self._rr(w[i-15], 7) ^ self._rr(w[i-15], 18) ^ (w[i-15] >> 3)
                s1 = self._rr(w[i-2], 17) ^ self._rr(w[i-2], 19) ^ (w[i-2] >> 10)
                w.append((w[i-16] + s0 + w[i-7] + s1) & 0xffffffff)
            a,b,c,d,e,f,g,h = self._h
            for i in range(64):
                S1 = self._rr(e,6) ^ self._rr(e,11) ^ self._rr(e,25)
                ch = (e & f) ^ ((~e) & g)
                t1 = (h + S1 + ch + _K256[i] + w[i]) & 0xffffffff
                S0 = self._rr(a,2) ^ self._rr(a,13) ^ self._rr(a,22)
                mj = (a & b) ^ (a & c) ^ (b & c)
                t2 = (S0 + mj) & 0xffffffff
                h,g,f,e,d,c,b,a = g,f,e,(d+t1)&0xffffffff,c,b,a,(t1+t2)&0xffffffff
            for i,v in enumerate([a,b,c,d,e,f,g,h]):
                self._h[i] = (self._h[i] + v) & 0xffffffff
        def update(self, data):
            if isinstance(data, str):
                data = data.encode('utf-8')
            self._buf += data
            self._count += len(data)
            while len(self._buf) >= 64:
                self._compress(self._buf[:64])
                self._buf = self._buf[64:]
        def digest(self):
            buf = self._buf + b'\x80'
            buf += b'\x00' * ((55 - len(self._buf)) % 64)
            buf += (self._count * 8).to_bytes(8, 'big')
            h = list(self._h)
            _tmp = _Sha256.__new__(_Sha256)
            _tmp._h = h; _tmp._buf = b''; _tmp._count = 0
            for i in range(0, len(buf), 64):
                _tmp._compress(buf[i:i+64])
            return b''.join(v.to_bytes(4, 'big') for v in _tmp._h)
        def hexdigest(self):
            return self.digest().hex()
        def copy(self):
            c = _Sha256.__new__(_Sha256)
            c._h = list(self._h); c._buf = self._buf; c._count = self._count
            return c
    def _sha256(data=b''):
        return _Sha256(data)
    _hl.sha256 = _sha256
    _hl.new = lambda name, data=b'': _sha256(data) if name == 'sha256' else None
del _hl

# -- 4. math: stub has no ceil/floor/log/sqrt --
import math as _ma
if not hasattr(_ma, 'ceil'):
    _ma.ceil = lambda x: int(x) if x == int(x) else int(x) + (1 if x > 0 else 0)
    _ma.floor = lambda x: int(x) if x >= 0 or x == int(x) else int(x) - 1
    _ma.fabs = lambda x: x if x >= 0 else -x
    _ma.sqrt = lambda x: x ** 0.5
    _ma.pow = lambda x, y: x ** y
    _ma.pi = 3.141592653589793
    _ma.e = 2.718281828459045
    _ma.inf = float('inf')
    _ma.nan = float('nan')
del _ma

del _wsys
# ============================================================================
# End WASI stdlib compatibility patches
# ============================================================================

import json
import traceback
from typing import Optional

from api.credits import (
    add_user_credits,
    deduct_user_credits,
    get_billing_status,
    get_user_credits,
    get_user_transactions,
)
from api.registry import (
    count_registered_realms,
    get_registered_realm,
    list_registered_realms,
    register_realm_by_caller,
    remove_registered_realm,
    search_registered_realms,
)
from api.status import get_status
from _cdk import (
    Async,
    CallResult,
    Func,
    Opt,
    Principal,
    Query,
    Record,
    StableBTreeMap,
    Variant,
    Vec,
    blob,
    float64,
    ic,
    init,
    match,
    nat,
    nat64,
    post_upgrade,
    query,
    text,
    update,
    void,
)
from ic_python_db import Database
from ic_python_logging import get_logger

# NOTE: Record/Variant types MUST be defined in this file (not imported from
# another module) because basilisk's Candid .did generator only parses main.py's
# AST for type definitions.  Duplicated from core/candid_types_registry.py.

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


class AddRealmResult(Variant, total=False):
    Ok: text
    Err: text


class GetRealmResult(Variant, total=False):
    Ok: RealmRecord
    Err: text


class RealmsListRecord(Record):
    realms: Vec[RealmRecord]
    total_count: nat64


class SearchRealmsResult(Record):
    realms: Vec[RealmRecord]
    query: text
    count: nat64


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

# Storage for the ORM (used internally by Database class)
# Direct storage access is not needed - use Entity classes instead
storage = StableBTreeMap[str, str](memory_id=1, max_key_size=200, max_value_size=2000)
Database.init(db_storage=storage, audit_enabled=True)

logger = get_logger("main")


@init
def init_canister() -> void:
    """Initialize the realm registry canister"""
    logger.info("Realm Registry canister initialized")


@query
def status() -> GetStatusResult:
    """Get the status of the registry backend canister"""
    try:
        status_data = get_status()
        return {
            "Ok": StatusRecord(
                version=status_data["version"],
                commit=status_data["commit"],
                commit_datetime=status_data["commit_datetime"],
                status=status_data["status"],
                realms_count=status_data["realms_count"],
                dependencies=status_data["dependencies"],
                python_version=status_data["python_version"],
            )
        }
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def list_realms() -> Vec[RealmRecord]:
    """List all registered realms"""
    try:
        realms_data = list_registered_realms()
        return realms_data
    except Exception as e:
        logger.error(f"Error in list_realms: {str(e)}")
        return []


@update
def register_realm(
    name: text,
    url: text,
    logo: text,
    backend_url: text = "",
    canister_ids_json: text = "{}",
) -> AddRealmResult:
    """Register calling realm (uses caller principal as ID, upsert logic)
    
    Note: Basilisk limits canister methods to 5 params, so canister IDs are passed as JSON.
    """
    try:
        # Parse canister IDs — pipe-delimited format: frontend_id|token_id|nft_id
        # (JSON format triggers basilisk Candid encoder bug, so we use pipe-delimited)
        frontend_canister_id = ""
        token_canister_id = ""
        nft_canister_id = ""
        if canister_ids_json and "|" in canister_ids_json:
            parts = canister_ids_json.split("|")
            frontend_canister_id = parts[0] if len(parts) > 0 else ""
            token_canister_id = parts[1] if len(parts) > 1 else ""
            nft_canister_id = parts[2] if len(parts) > 2 else ""
        elif canister_ids_json and canister_ids_json.startswith("{"):
            # Fallback: JSON format (for direct dfx calls)
            canister_ids = json.loads(canister_ids_json)
            frontend_canister_id = canister_ids.get("frontend_canister_id", "")
            token_canister_id = canister_ids.get("token_canister_id", "")
            nft_canister_id = canister_ids.get("nft_canister_id", "")
        
        result = register_realm_by_caller(
            name, url, logo, backend_url,
            frontend_canister_id=frontend_canister_id,
            token_canister_id=token_canister_id,
            nft_canister_id=nft_canister_id,
        )
        if result["success"]:
            return {"Ok": result["message"]}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in register_realm: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def get_realm(realm_id: text) -> GetRealmResult:
    """Get a specific realm by ID"""
    try:
        result = get_registered_realm(realm_id)
        if result["success"]:
            return {"Ok": result["realm"]}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in get_realm: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@update
def remove_realm(realm_id: text) -> AddRealmResult:
    """Remove a realm from the registry"""
    try:
        result = remove_registered_realm(realm_id)
        if result["success"]:
            return {"Ok": result["message"]}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in remove_realm: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def search_realms(query: text) -> Vec[RealmRecord]:
    """Search realms by name or ID"""
    try:
        results = search_registered_realms(query)
        return results
    except Exception as e:
        logger.error(f"Error in search_realms: {str(e)}")
        return []


@query
def realm_count() -> nat64:
    """Get the total number of registered realms"""
    try:
        count = count_registered_realms()
        return nat64(count)
    except Exception as e:
        logger.error(f"Error in realm_count: {str(e)}")
        return nat64(0)


@query
def greet(name: str) -> str:
    """Simple greeting function for testing"""
    return f"Hello, {name}!"


# ============== Credits Endpoints ==============

@query
def get_credits(principal_id: text) -> GetCreditsResult:
    """Get a user's credit balance"""
    try:
        result = get_user_credits(principal_id)
        if result["success"]:
            credits = result["credits"]
            return {
                "Ok": {
                    "principal_id": credits["principal_id"],
                    "balance": nat64(credits["balance"]),
                    "total_purchased": nat64(credits["total_purchased"]),
                    "total_spent": nat64(credits["total_spent"]),
                }
            }
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in get_credits: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@update
def add_credits(principal_id: text, amount: nat64, stripe_session_id: text = "", description: text = "Credit top-up") -> AddCreditsResult:
    """
    Add credits to a user's balance.
    Called by the billing service after successful payment.
    
    - **principal_id**: User's Internet Identity principal
    - **amount**: Number of credits to add (1 credit = $1)
    - **stripe_session_id**: Stripe checkout session ID (for tracking)
    - **description**: Transaction description
    """
    try:
        result = add_user_credits(
            principal_id=principal_id,
            amount=int(amount),
            stripe_session_id=stripe_session_id,
            description=description,
        )
        if result["success"]:
            credits = result["credits"]
            return {
                "Ok": {
                    "principal_id": credits["principal_id"],
                    "balance": nat64(credits["balance"]),
                    "total_purchased": nat64(credits["total_purchased"]),
                    "total_spent": nat64(credits["total_spent"]),
                }
            }
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in add_credits: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@update
def deduct_credits(principal_id: text, amount: nat64, description: text = "Credit spend") -> DeductCreditsResult:
    """
    Deduct credits from a user's balance.
    Used when user deploys a realm or uses credits for other services.
    
    - **principal_id**: User's Internet Identity principal
    - **amount**: Number of credits to deduct
    - **description**: Transaction description
    """
    try:
        result = deduct_user_credits(
            principal_id=principal_id,
            amount=int(amount),
            description=description,
        )
        if result["success"]:
            credits = result["credits"]
            return {
                "Ok": {
                    "principal_id": credits["principal_id"],
                    "balance": nat64(credits["balance"]),
                    "total_purchased": nat64(credits["total_purchased"]),
                    "total_spent": nat64(credits["total_spent"]),
                }
            }
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in deduct_credits: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def get_transactions(principal_id: text, limit: nat64 = nat64(50)) -> TransactionHistoryResult:
    """Get a user's transaction history"""
    try:
        result = get_user_transactions(principal_id, int(limit))
        if result["success"]:
            transactions = [
                {
                    "id": tx["id"],
                    "principal_id": tx["principal_id"],
                    "amount": nat64(abs(tx["amount"])),
                    "transaction_type": tx["transaction_type"],
                    "description": tx["description"],
                    "stripe_session_id": tx["stripe_session_id"],
                    "timestamp": float(tx["timestamp"]),
                }
                for tx in result["transactions"]
            ]
            return {"Ok": transactions}
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}


@query
def billing_status() -> GetBillingStatusResult:
    """Get overall billing status across all users"""
    try:
        result = get_billing_status()
        if result["success"]:
            billing = result["billing"]
            return {
                "Ok": BillingStatusRecord(
                    users_count=nat64(billing["users_count"]),
                    total_balance=nat64(billing["total_balance"]),
                    total_purchased=nat64(billing["total_purchased"]),
                    total_spent=nat64(billing["total_spent"]),
                )
            }
        else:
            return {"Err": result["error"]}
    except Exception as e:
        logger.error(f"Error in billing_status: {str(e)}")
        return {"Err": f"Internal error: {str(e)}"}
