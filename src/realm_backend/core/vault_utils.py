import core.candid_types_vault as vault_candids
from core.app_data import app_data
from kybra import CallResult, Principal, ic


def get_realm_balance() -> vault_candids.Response:
    # Get a reference to the vault canister
    vault = vault_candids.Vault(Principal.from_str(app_data().vault_canister_principal))

    # status_result: CallResult[Response] = yield vault.status()

    balance_result: CallResult[vault_candids.Response] = yield vault.get_balance(
        ic.id()
    )

    if not balance_result.Ok:
        raise Exception("Failed to get balance of realm from vault")

    balance_response = balance_result.Ok
    ic.print(f"Balance Ok response: {balance_response}")

    return balance_response
