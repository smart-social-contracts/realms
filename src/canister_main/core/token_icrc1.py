from typing import Optional

from kybra_simple_db import *

from .icrcledger import ICRCLedger


class TokenICRC1(Entity, TimestampedMixin):

    token_type = String(default="TokenICRC1")
    token_core = OneToOne(["Token"], "token")
    principal = String()
    total_supply = String(default="0")

    @classmethod
    def new(cls, symbol: str, principal: str, name: Optional[str] = None):
        if not principal:
            raise ValueError("Principal is required for ICRC1 tokens")

        return TokenICRC1(id=symbol, name=name, principal=principal)

    def get_fee(self) -> int:
        """Get the actual transfer fee from the ledger.

        Returns:
            int: The transfer fee from the ledger
        """
        try:
            ledger = self.get_ledger(self.principal)
            fee = ledger.icrc1_fee()
            return fee
        except Exception as e:
            ic.print(f"Error getting fee: {e}")
            return 0

    def transfer(
        self, from_address: str, to_address: str, amount: int, fee: Optional[int] = None
    ) -> None:
        """Transfer tokens between addresses following ICRC1 behavior.

        Args:
            from_address: The sender's address
            to_address: The receiver's address
            amount: The amount of tokens to transfer
            fee: Optional fee amount (will use ledger's fee if not specified)

        Raises:
            ValueError: If amount is not positive or sender has insufficient balance
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Get the actual fee from the ledger if not specified
        actual_fee = fee if fee is not None else self.get_fee()

        # Check sender's balance including fee
        sender_balance = self.balances.get(from_address, 0)
        if sender_balance < amount + actual_fee:
            raise ValueError("Insufficient balance including fee")

        # Update balances
        self.balances[from_address] = sender_balance - amount - actual_fee
        self.balances[to_address] = self.balances.get(to_address, 0) + amount
        self.save()

    def get_total_supply(self) -> int:
        """Get the total supply of tokens across all addresses.

        Returns:
            int: The total number of tokens in circulation
        """
        return sum(self.balances.values())

    def mint(self, address: str, amount: int) -> None:
        """Mint new tokens and assign them to an address.

        Args:
            address: The address to receive the tokens
            amount: The amount of tokens to mint

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        self.balances[address] = self.balances.get(address, 0) + amount
        self.save()

    def get_canister_balance(self) -> int:
        """Get the balance of tokens held by the canister itself.

        Returns:
            int: The token balance of the canister's principal
        """
        try:
            account = Account(owner=ic.id(), subaccount=None)
            balance_call = self.get_ledger(self.principal).icrc1_balance_of(account)

            # Wait for the balance call to complete with a maximum number of attempts
            max_attempts = 1000000
            attempts = 0

            last_value = ""
            while attempts < max_attempts:
                try:
                    if attempts % 100 == 0:
                        # ic.print('[%d] balance_call: %s' % (attempts, balance_call))
                        new_value = str(balance_call)
                        if hasattr(balance_call, "notify"):
                            # ic.print("Getting balance using notify()")
                            new_value += str(balance_call.notify())
                        if str(new_value) != last_value:
                            ic.print("new_value = %s" % new_value)
                            last_value = str(new_value)
                    # result = balance_call
                    # if result is not None:
                    #     return match(result, {
                    #         "Ok": lambda ok: ok,
                    #         "Err": lambda err: 0  # Return 0 balance on error
                    #     })
                except Exception as e:
                    ic.print(
                        f"Waiting for balance (attempt {attempts + 1}/{max_attempts}): {e}"
                    )
                attempts += 1

            ic.print("Max attempts reached waiting for balance")
            return 0

        except Exception as e:
            ic.print(f"Error getting balance: {e}")
            return 0


# def get_canister_balance_2() -> Async[int]:
#     # def get_canister_balance_2() -> int:
#     ic.print('get_canister_balance_2')
#     ck_btc = TokenICRC1['ckBTC']
#     ic.print("ck_btc = %s" % ck_btc)
#     ledger = ICRCLedger(Principal.from_str(ck_btc.principal))
#     account = Account(owner=ic.id(), subaccount=None)
#     result: CallResult[int] = yield ledger.icrc1_balance_of(account)
#     return match(result, {
#         "Ok": lambda ok: ok,
#         "Err": lambda err: 0  # Return 0 balance on error
#     })
