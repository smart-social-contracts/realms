"""
Governance Proposal: Transfer 1 Satoshi (ckBTC)

This proposal demonstrates the governance execution pipeline by:
1. Registering the ckBTC token in the canister's wallet (if not already)
2. Querying the canister's ckBTC balance
3. Transferring 1 satoshi to the Dominion canister

If the canister has no ckBTC balance, the transfer will fail gracefully
and the attempt is logged.

Requires: async execution via main() generator pattern.
"""

CKBTC_LEDGER = "mxzaz-hqaaa-aaaar-qaada-cai"
CKBTC_INDEXER = "n5wcd-faaaa-aaaar-qaaea-cai"
RECIPIENT = "h5vpp-qyaaa-aaaac-qai3a-cai"  # Dominion canister
AMOUNT = 1  # 1 satoshi


def main():
    from basilisk.os.wallet import Wallet

    wallet = Wallet()

    # Ensure ckBTC is registered
    wallet.register_token(
        name="ckBTC",
        ledger=CKBTC_LEDGER,
        indexer=CKBTC_INDEXER,
        decimals=8,
        fee=10,
    )
    logger.info("ckBTC token registered in wallet")

    # Check balance
    balance = yield wallet.balance_of("ckBTC")
    logger.info(f"Canister ckBTC balance: {balance} satoshis")

    if balance < AMOUNT + 10:  # amount + fee
        logger.warning(
            f"Insufficient ckBTC balance ({balance}) for transfer of "
            f"{AMOUNT} + 10 fee. Fund the canister to enable transfers."
        )
        return

    # Execute the transfer
    logger.info(f"Transferring {AMOUNT} satoshi ckBTC to {RECIPIENT}")
    result = yield wallet.transfer(
        token_name="ckBTC",
        to_principal=RECIPIENT,
        amount=AMOUNT,
    )
    logger.info(f"Transfer result: {result}")
