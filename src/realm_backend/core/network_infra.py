NETWORK_INFRA = {
    "test": {
        "file_registry": "uq2mu-kaaaa-aaaah-avqcq-cai",
        "marketplace": "2wldc-niaaa-aaaad-qlxga-cai",
    },
    "demo": {
        "file_registry": "vi64l-3aaaa-aaaae-qj4va-cai",
        "marketplace": "ehyfg-wyaaa-aaaae-qg3qq-cai",
    },
    "staging": {
        "file_registry": "hacwc-baaaa-aaaac-bfxmq-cai",
        "marketplace": "l5qpy-wqaaa-aaaah-qu2mq-cai",
    },
}


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
