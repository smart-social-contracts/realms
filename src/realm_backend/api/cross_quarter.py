"""Inter-canister transport for cross-quarter gossip.

Holds the ``Service`` handle + async helper used by ``sync_quarters`` to pull a
peer quarter's coarse directory. Kept here (mirroring ``api/messaging.py``) so
``main.py`` only carries a thin endpoint wrapper and the generator/yield
inter-canister pattern lives in one place.

The directory exchanged is **coarse** — quarter list + populations, never
per-entity rows (see issue #156).

Also carries the quarter→capital population push used on join so the capital's
cached counts stay fresh without relying on the recurring sync task.
"""

import json
from typing import Dict

from _cdk import Async, CallResult, Principal, Service, ic, nat, service_query, service_update, text
from ic_python_logging import get_logger

logger = get_logger("api.cross_quarter")


class QuarterDirectoryService(Service):
    """Remote interface of a peer quarter's coarse directory endpoint."""

    @service_query
    def get_quarter_directory(self) -> text:
        ...


class CapitalPopulationService(Service):
    """Remote interface of the capital's population-report endpoint."""

    @service_update
    def report_quarter_population(self, population: nat) -> text:
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
        # Basilisk returns a CallResult variant; str() yields its repr (invalid
        # JSON). Unwrap the Ok text first (mirrors api/file_registry.py).
        if isinstance(result, str):
            raw = result
        elif isinstance(result, dict):
            raw = result.get("Ok", result.get("ok", str(result)))
        elif hasattr(result, "Ok") and result.Ok is not None:
            raw = result.Ok
        else:
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


def report_population_to_capital(capital_canister_id: str, population: int) -> Async[Dict]:
    """Push this quarter's live population to the capital (issue #156).

    Called from ``join_realm`` after a *new* member lands on a quarter so the
    capital's ``Quarter.population`` (and therefore ``get_join_targets`` /
    least-populated assignment) updates immediately — no timer wait.

    Returns ``{"success": bool, ...}`` parsed from the capital response, or
    ``{"success": False, "error": ...}`` on transport failure.
    """
    logger.info(
        f"Reporting population {population} to capital {capital_canister_id}"
    )
    try:
        service = CapitalPopulationService(Principal.from_str(capital_canister_id))
        result: CallResult[text] = yield service.report_quarter_population(
            int(population)
        )
        if isinstance(result, str):
            raw = result
        elif isinstance(result, dict):
            raw = result.get("Ok", result.get("ok", str(result)))
        elif hasattr(result, "Ok") and result.Ok is not None:
            raw = result.Ok
        else:
            raw = str(result)
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": f"Unparseable capital response: {raw[:200]}"}
        if isinstance(parsed, dict):
            return parsed
        return {"success": True, "result": parsed}
    except Exception as e:
        logger.error(
            f"Error reporting population to capital {capital_canister_id}: {e}"
        )
        return {"success": False, "error": str(e)}
