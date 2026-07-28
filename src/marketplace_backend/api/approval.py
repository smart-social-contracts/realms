"""Stamping a review decision onto the file registry (issue #267).

A listing's ``verification_status`` is a label the marketplace keeps for
itself; no realm reads it. What a realm checks before installing is an
approval recorded against the namespace in the file registry, bound to the
hashes of the exact files that were reviewed. This module is the bridge that
turns a reviewer's decision into that record.

Order matters: the registry is written first and the listing is only updated
if that succeeded. The failure a user can understand is "the approval did not
go through"; the one they cannot is a marketplace that says approved while
realms keep refusing the package.
"""

import json

from _cdk import Async, CallResult, Principal, Service, ic, service_update, text
from api.config import get_file_registry_canister_id, is_reviewer
from api.verification import VALID_KINDS, _get_listing
from ic_python_logging import get_logger

logger = get_logger("api.approval")


class FileRegistryService(Service):
    @service_update
    def set_namespace_approval(self, args: text) -> text: ...


def _unwrap_call_result(result) -> str:
    """Normalize a basilisk inter-canister call result to its text payload."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("Ok", result.get("ok", str(result)))
    if hasattr(result, "Ok"):
        return result.Ok
    return str(result)


def _is_controller() -> bool:
    try:
        return bool(ic.is_controller(ic.caller()))
    except Exception:
        return False


def admin_approve_namespace(*, namespace: str, notes: str = "") -> Async[dict]:
    """Approve a registry namespace directly, without going through a listing.

    For first-party packages that predate the marketplace pipeline: they have
    no listing to review, but realms still refuse them unapproved. Routing the
    write through this canister (rather than having an operator call the
    registry themselves) means the approval is attributed to the marketplace,
    which is who realms trust by default.

    Controller-only — this is a migration tool, not part of the review flow.
    """
    if not _is_controller():
        return {"success": False, "error": "Unauthorized: controller-only"}

    namespace = (namespace or "").strip()
    if not namespace:
        return {"success": False, "error": "namespace is required"}

    registry_id = get_file_registry_canister_id()
    if not registry_id:
        return {"success": False, "error": "No file registry configured"}

    registry = FileRegistryService(Principal.from_str(registry_id))
    try:
        raw: CallResult = yield registry.set_namespace_approval(
            json.dumps(
                {"namespace": namespace, "status": "approved", "notes": notes or ""}
            )
        )
        response = json.loads(_unwrap_call_result(raw))
    except Exception as e:
        logger.error(f"admin approval of {namespace} failed: {e}")
        return {"success": False, "error": f"File registry call failed: {e}"}

    if not isinstance(response, dict) or response.get("error"):
        detail = (
            response.get("error")
            if isinstance(response, dict)
            else "unexpected response"
        )
        return {"success": False, "error": f"File registry refused: {detail}"}

    logger.info(f"admin-approved {namespace} on {registry_id}")
    return {"success": True, "namespace": namespace, "file_count": response.get("file_count", 0)}


def review_listing(
    *, caller: str, item_kind: str, item_id: str, approve: bool, notes: str = ""
) -> Async[dict]:
    """Record a review decision and mirror it into the file registry.

    Requires the caller to be a marketplace reviewer, and requires the
    marketplace canister itself to hold approver rights on the registry —
    without that the registry rejects the write and nothing is changed here
    either.
    """
    if not is_reviewer(caller):
        return {"success": False, "error": "Unauthorized: reviewers only"}
    if item_kind not in VALID_KINDS:
        return {"success": False, "error": f"item_kind must be one of {VALID_KINDS}"}

    listing = _get_listing(item_kind, item_id)
    if listing is None:
        return {"success": False, "error": "Listing not found"}

    namespace = str(getattr(listing, "file_registry_namespace", "") or "").strip()
    if not namespace:
        return {
            "success": False,
            "error": (
                f"{item_kind}:{item_id} has no file_registry_namespace — there is "
                f"nothing to approve. Republish it with its registry location set."
            ),
        }

    registry_id = str(
        getattr(listing, "file_registry_canister_id", "") or ""
    ).strip() or get_file_registry_canister_id()
    if not registry_id:
        return {
            "success": False,
            "error": "No file registry configured for this listing or marketplace",
        }

    status = "approved" if approve else "rejected"
    registry = FileRegistryService(Principal.from_str(registry_id))

    try:
        raw: CallResult = yield registry.set_namespace_approval(
            json.dumps({"namespace": namespace, "status": status, "notes": notes or ""})
        )
        response = json.loads(_unwrap_call_result(raw))
    except Exception as e:
        logger.error(f"approval call to {registry_id} failed for {namespace}: {e}")
        return {
            "success": False,
            "error": f"File registry did not accept the decision: {e}",
        }

    if not isinstance(response, dict) or response.get("error"):
        detail = (
            response.get("error")
            if isinstance(response, dict)
            else "unexpected response"
        )
        return {
            "success": False,
            "error": f"File registry refused the decision: {detail}",
        }

    listing.verification_status = "verified" if approve else "rejected"
    listing.verification_notes = notes or ""
    logger.info(
        f"{item_kind}:{item_id} {status} by {caller}; stamped on "
        f"{registry_id}/{namespace}"
    )
    return {
        "success": True,
        "verification_status": listing.verification_status,
        "namespace": namespace,
        "file_registry_canister_id": registry_id,
        "file_count": response.get("file_count", 0),
    }
