"""Inter-canister transport for cross-quarter gossip.

Holds the ``Service`` handle + async helper used by ``sync_quarters`` to pull a
peer quarter's coarse directory. Kept here (mirroring ``api/messaging.py``) so
``main.py`` only carries a thin endpoint wrapper and the generator/yield
inter-canister pattern lives in one place.

The directory exchanged is **coarse** — quarter list + populations, never
per-entity rows (see issue #156).
"""

import json
from typing import Dict

from _cdk import Async, CallResult, Principal, Service, ic, service_query, text
from ic_python_logging import get_logger

logger = get_logger("api.cross_quarter")


class QuarterDirectoryService(Service):
    """Remote interface of a peer quarter's coarse directory endpoint."""

    @service_query
    def get_quarter_directory(self) -> text:
        ...


def fetch_peer_directory(peer_canister_id: str) -> Async[Dict]:
    """Query a peer quarter's ``get_quarter_directory`` and return parsed data.

    Returns ``{"success": bool, "quarters": [...]}`` or ``{"success": False,
    "error": ...}``.
    """
    logger.info(f"Fetching quarter directory from peer {peer_canister_id}")
    try:
        service = QuarterDirectoryService(Principal.from_str(peer_canister_id))
        result: CallResult[text] = yield service.get_quarter_directory()
        raw = str(result)
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": f"Unparseable peer response: {raw[:200]}"}
        quarters = parsed.get("quarters", parsed) if isinstance(parsed, dict) else parsed
        return {"success": True, "quarters": quarters or []}
    except Exception as e:
        logger.error(f"Error fetching peer directory from {peer_canister_id}: {e}")
        return {"success": False, "error": str(e)}
