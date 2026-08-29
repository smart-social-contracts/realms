NETWORK_INFRA = {
    "test": {
        "file_registry": "uq2mu-kaaaa-aaaah-avqcq-cai",
        "marketplace": "2wldc-niaaa-aaaad-qlxga-cai",
        "installer": "fltjm-tyaaa-aaaap-qunhq-cai",
        "registry": "yhw3g-fyaaa-aaaas-qgorq-cai",
    },
    "demo": {
        "file_registry": "vi64l-3aaaa-aaaae-qj4va-cai",
        "marketplace": "ehyfg-wyaaa-aaaae-qg3qq-cai",
        # Historical GOS IDs plus the live Casals-managed stack. rhw4p is
        # IC0301; demo.gos.earth uses moqmm (installer) / mjrky (registry).
        "installer": (
            "2s4td-daaaa-aaaao-bazmq-cai",
            "moqmm-caaaa-aaaah-qu27q-cai",
        ),
        "registry": (
            "rhw4p-gqaaa-aaaac-qbw7q-cai",
            "mjrky-pyaaa-aaaah-qu27a-cai",
        ),
    },
    "staging": {
        "file_registry": "hacwc-baaaa-aaaac-bfxmq-cai",
        "marketplace": "h3hkh-3yaaa-aaaac-bfxoa-cai",
        "installer": "lusjm-wqaaa-aaaau-ago7q-cai",
        "registry": "7wzxh-wyaaa-aaaau-aggyq-cai",
    },
}


def _principal_ids(value) -> list:
    """Normalize a NETWORK_INFRA installer/registry value to principal strings."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        items = value
    else:
        items = (value,)
    ids = []
    for item in items:
        text = (item or "").strip()
        if text:
            ids.append(text)
    return ids


def known_bootstrap_principals() -> frozenset:
    """GOS installer + registry principals that may first-boot a realm.

    Casals is not a lasting controller. After canister create, the installer
    (fltjm on test, moqmm on live demo) calls enter_setup /
    set_canister_config_json. Those callers must be recognizable without an
    IC-controller check.
    """
    ids = set()
    for entry in NETWORK_INFRA.values():
        for key in ("installer", "registry"):
            ids.update(_principal_ids(entry.get(key)))
    return frozenset(ids)


def is_known_bootstrap_principal(principal: str) -> bool:
    return (principal or "").strip() in known_bootstrap_principals()


def file_registry_id_for(environment: str) -> str:
    entry = NETWORK_INFRA.get((environment or "").strip())
    if not entry:
        return ""
    return entry["file_registry"]


def marketplace_id_for(environment: str) -> str:
    entry = NETWORK_INFRA.get((environment or "").strip())
    if not entry:
        return ""
    return entry["marketplace"]


def apply_network_infra(realm, environment: str):
    """If environment is empty, no-op (return None).
    If unknown, return {"ok": False, "error": "unknown environment: <name>"}.
    If known, set realm.file_registry_canister_id and realm.marketplace_canister_id
    only when the current value is empty/whitespace. Return None on success.
    """
    network = (environment or "").strip()
    if not network:
        return None
    entry = NETWORK_INFRA.get(network)
    if not entry:
        return {"ok": False, "error": f"unknown environment: {network}"}
    if not (getattr(realm, "file_registry_canister_id", "") or "").strip():
        realm.file_registry_canister_id = entry["file_registry"]
    if not (getattr(realm, "marketplace_canister_id", "") or "").strip():
        realm.marketplace_canister_id = entry["marketplace"]
    return None
