"""Top-N rankings — extensions and codices, by installs and likes.

v1 is pure in-memory: load all active listings, sort by the metric,
slice. Hundreds of items at most. If we ever exceed that we'll move to
materialised top-N caches.
"""

from typing import Dict, List

from api.assistants import _to_dict as _assistant_to_dict
from api.codices import _to_dict as _codex_to_dict
from api.extensions import _to_dict as _ext_to_dict
from core.models import (
    AssistantListingEntity,
    CodexListingEntity,
    ExtensionListingEntity,
)


def _clamp_n(n: int) -> int:
    n = int(n or 0)
    if n <= 0:
        n = 20
    return min(n, 100)


def _filter_active_extensions(verified_only: bool) -> List[ExtensionListingEntity]:
    items = [
        e for e in ExtensionListingEntity.instances()
        if (e.is_active if e.is_active is not None else True)
    ]
    if verified_only:
        items = [e for e in items if str(e.verification_status) == "verified"]
    return items


def _filter_active_codices(verified_only: bool) -> List[CodexListingEntity]:
    items = [
        c for c in CodexListingEntity.instances()
        if (c.is_active if c.is_active is not None else True)
    ]
    if verified_only:
        items = [c for c in items if str(c.verification_status) == "verified"]
    return items


def top_extensions_by_downloads(n: int, verified_only: bool = False) -> List[Dict]:
    items = _filter_active_extensions(verified_only)
    items.sort(key=lambda e: (int(e.installs or 0), int(e.likes or 0)), reverse=True)
    return [_ext_to_dict(e) for e in items[: _clamp_n(n)]]


def top_extensions_by_likes(n: int, verified_only: bool = False) -> List[Dict]:
    items = _filter_active_extensions(verified_only)
    items.sort(key=lambda e: (int(e.likes or 0), int(e.installs or 0)), reverse=True)
    return [_ext_to_dict(e) for e in items[: _clamp_n(n)]]


def top_codices_by_downloads(n: int, verified_only: bool = False) -> List[Dict]:
    items = _filter_active_codices(verified_only)
    items.sort(key=lambda c: (int(c.installs or 0), int(c.likes or 0)), reverse=True)
    return [_codex_to_dict(c) for c in items[: _clamp_n(n)]]


def top_codices_by_likes(n: int, verified_only: bool = False) -> List[Dict]:
    items = _filter_active_codices(verified_only)
    items.sort(key=lambda c: (int(c.likes or 0), int(c.installs or 0)), reverse=True)
    return [_codex_to_dict(c) for c in items[: _clamp_n(n)]]


def _filter_active_assistants(verified_only: bool) -> List[AssistantListingEntity]:
    items = [
        a for a in AssistantListingEntity.instances()
        if (a.is_active if a.is_active is not None else True)
    ]
    if verified_only:
        items = [a for a in items if str(a.verification_status) == "verified"]
    return items


def top_assistants_by_downloads(n: int, verified_only: bool = False) -> List[Dict]:
    items = _filter_active_assistants(verified_only)
    items.sort(key=lambda a: (int(a.installs or 0), int(a.likes or 0)), reverse=True)
    return [_assistant_to_dict(a) for a in items[: _clamp_n(n)]]


def top_assistants_by_likes(n: int, verified_only: bool = False) -> List[Dict]:
    items = _filter_active_assistants(verified_only)
    items.sort(key=lambda a: (int(a.likes or 0), int(a.installs or 0)), reverse=True)
    return [_assistant_to_dict(a) for a in items[: _clamp_n(n)]]
