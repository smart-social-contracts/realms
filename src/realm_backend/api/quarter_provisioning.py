"""Inter-canister transport for quarter auto-scaling (issue #156).

Holds the ``Service`` handle + async helper the capital uses to ask its
``realm_installer`` broker to mint one more backend-only quarter canister via
Casals. The decision of *whether* to scale lives in ``core.autoscale``; the
broker logic (Casals secrets, stand) lives in the installer. This module is
only the thin yield/generator transport, mirroring ``api/cross_quarter.py``.
"""

import json
from typing import Dict

from _cdk import Async, CallResult, Principal, Service, ic, service_update, text
from ic_python_logging import get_logger

logger = get_logger("api.quarter_provisioning")


class InstallerProvisionService(Service):
    """Remote interface of the realm_installer ``provision_quarter`` broker."""

    @service_update
    def provision_quarter(self, args: text) -> text:
        ...


def request_provision_quarter(installer_canister_id: str, args: Dict) -> Async[Dict]:
    """Ask the installer to provision a new backend-only quarter via Casals.

    ``args`` is forwarded as JSON (``{stand, backend_wasm_key, name?}``).
    Returns the parsed installer response, e.g. ``{"ok": True, "canister_id": ...}``
    or ``{"ok": False, "error": ...}``.
    """
    logger.info(f"Requesting quarter provisioning from installer {installer_canister_id}")
    try:
        service = InstallerProvisionService(Principal.from_str(installer_canister_id))
        result: CallResult[text] = yield service.provision_quarter(json.dumps(args))
        raw = str(result)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"ok": False, "error": f"Unparseable installer response: {raw[:200]}"}
    except Exception as e:
        logger.error(f"Error provisioning quarter via {installer_canister_id}: {e}")
        return {"ok": False, "error": str(e)}
