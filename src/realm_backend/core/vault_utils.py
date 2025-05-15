

from kybra import Principal, CallResult, ic

from candid_types_vault import (
    Response,
    Vault,
)


def get_realm_balance() -> Response:
    # Get a reference to the vault canister
    vault = Vault(Principal.from_str(app_data().vault_canister_principal))

    # status_result: CallResult[Response] = yield vault.status()

    balance_result: CallResult[Response] = yield vault.get_balance(ic.id())

    if not balance_result.Ok:
        raise Exception("Failed to get balance of realm from vault")

    balance_response = balance_result.Ok
    ic.print(f"Balance Ok response: {balance_response}")
    
    return balance_response
        