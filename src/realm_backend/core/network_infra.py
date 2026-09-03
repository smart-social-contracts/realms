NETWORK_INFRA = {
    "test": {
        "file_registry": "bbwyi-raaaa-aaaas-amxfa-cai",
        "marketplace": "btqpr-5qaaa-aaaas-amxga-cai",
        # Historical GOS IDs plus the 2026-09-03 gaas new stack.
        "installer": (
            "fltjm-tyaaa-aaaap-qunhq-cai",
            "jmgc7-2aaaa-aaaai-ax5qa-cai",
        ),
        "registry": (
            "yhw3g-fyaaa-aaaas-qgorq-cai",
            "mq5y2-riaaa-aaaai-ax5pq-cai",
        ),
    },
    "demo": {
        "file_registry": "krch6-ryaaa-aaaas-amw3q-cai",
        "marketplace": "l3nfe-tiaaa-aaaas-amw4q-cai",
        # Historical GOS IDs plus later stacks. rhw4p / moqmm / mjrky may be
        # IC0301 after a gaas new; current demo installer/registry are tzip5 / tmp6q.
        "installer": (
            "2s4td-daaaa-aaaao-bazmq-cai",
            "moqmm-caaaa-aaaah-qu27q-cai",
            "tzip5-vaaaa-aaaah-av3ca-cai",
        ),
        "registry": (
            "rhw4p-gqaaa-aaaac-qbw7q-cai",
            "mjrky-pyaaa-aaaah-qu27a-cai",
            "tmp6q-uiaaa-aaaah-av3bq-cai",
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
    (fltjm / jmgc7 on test, moqmm / tzip5 on demo, …) calls enter_setup /
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
