# Vault Extension for Realms

A secure digital asset and token management extension that provides treasury functionality for Realms.

## Features

- **ckBTC Balance Tracking**: Monitor user deposits and withdrawals
- **Vault Balance Queries**: Query the vault's total ckBTC balance directly from the ledger
- **Transaction History**: Complete audit trail of all vault operations
- **Admin-Controlled Transfers**: Only realm admins can transfer tokens out
- **ICRC Integration**: Direct integration with ICRC-1 ledger and indexer canisters
- **Test Mode Support**: Mock transactions for development and testing
- **Treasury Integration**: Seamlessly works with Realms Treasury entity

## Architecture

This extension embeds the full vault logic directly in the realm_backend canister, eliminating inter-canister call overhead and providing atomic operations with realm data.

```
realm_backend canister
├── vault extension
│   ├── vault_lib/ (core logic)
│   │   ├── candid_types.py
│   │   ├── constants.py
│   │   ├── entities.py
│   │   ├── ic_util_calls.py
│   │   └── core.py
│   └── entry.py (extension API)
└── ggg/Treasury (integrates with vault)
```

## Installation

### As an Extension Developer (Testing)

```bash
# Clone realms repo at specific version
git clone https://github.com/smart-social-contracts/realms.git
cd realms
git checkout v1.2.3  # or specific commit

# Install realms CLI in dev mode
pip install -e cli/

# Install your extension from local path
realms extension install --source /path/to/realms-extension-vault/

# Deploy locally for testing
dfx start --clean --background
realms realm deploy --network local

# Run tests
cd /path/to/realms-extension-vault/
pytest tests/
```

### As a Realm Operator (Production)

```bash
# Install from GitHub release
realms extension install vault \
  --from https://github.com/smart-social-contracts/realms-extension-vault/releases/download/v0.1.0/vault-0.1.0.zip

# Or from extension registry (future)
realms extension install vault@0.1.0

# Deploy
realms realm deploy
```

## Usage

### Initialize Treasury

```python
from ggg import Treasury

# Create treasury linked to your realm
treasury = Treasury(_id="main_treasury", name="Main Treasury")
treasury.vault_principal_id = ic.id().to_str()  # Extension runs in same canister
```

### Check Balance

```python
balance = yield treasury.get_balance()
# Returns: {"principal_id": "xxx", "amount": 1000}
```

### Transfer Tokens

```python
result = yield treasury.send(
    to_principal="recipient-principal-id",
    amount=100
)
# Returns: {"transaction_id": 42}
```

### Sync Transaction History

```python
yield treasury.refresh()
# Updates Treasury with latest transactions from ICRC ledger
```

### Check Vault's Total Balance

```python
# Get the vault's actual ckBTC balance from the ledger
result = yield get_vault_balance({})
# Returns: {
#   "vault_principal": "h5vpp-qyaaa-aaaac-qai3a-cai",
#   "balance": 100000000,  # in satoshis
#   "balance_btc": "1.00000000"  # in BTC
# }
```

#### Using dfx command line:

```bash
# Get vault canister ID
VAULT_ID=$(dfx canister id realm_backend)

# Query balance from ckBTC ledger
dfx canister call mxzaz-hqaaa-aaaar-qaada-cai icrc1_balance_of \
  "(record { owner = principal \"$VAULT_ID\"; subaccount = null })"

# For staging network
dfx canister --network staging call mxzaz-hqaaa-aaaar-qaada-cai icrc1_balance_of \
  "(record { owner = principal \"h5vpp-qyaaa-aaaac-qai3a-cai\"; subaccount = null })"
```

## Extension API

The extension exposes the following functions:

- `get_balance(args)` - Get user balance for a specific principal
- `get_vault_balance(args)` - Get the vault's total ckBTC balance from the ledger
- `get_status(args)` - Get vault status and stats
- `get_transactions(args)` - Get transaction history for a principal
- `transfer(args)` - Transfer tokens to a principal (admin only)
- `refresh(args)` - Sync transaction history from ICRC ledger

## Compatibility

- **Realms Version**: >=0.1.0, <0.2.x
- **Python**: 3.10.7
- **Required Dependencies**:
  - kybra>=0.10.0
  - kybra-simple-db>=1.0.0
  - kybra-simple-logging>=1.0.0

## Development

### Project Structure

```
realms-extension-vault/
├── backend/
│   ├── vault_lib/
│   │   ├── __init__.py
│   │   ├── candid_types.py
│   │   ├── constants.py
│   │   ├── entities.py
│   │   ├── ic_util_calls.py
│   │   └── core.py
│   ├── __init__.py
│   └── entry.py
├── frontend/
│   ├── lib/extensions/vault/
│   └── routes/(sidebar)/extensions/vault/
├── tests/
│   └── test_vault.py
├── manifest.json
├── README.md
└── CHANGELOG.md
```

### Running Tests

See [TESTING.md](./TESTING.md) for complete testing guide.

Quick start:
```bash
# Run all tests (local development)
../_shared/testing/scripts/test_entrypoint.sh

# Run linters
../_shared/testing/scripts/run_linters.sh --config .flake8

# Run E2E tests
cd tests/e2e && ./run-e2e-tests.sh
```

### Packaging for Distribution

```bash
realms extension package .
# Creates: vault-0.1.0.zip
```

### Publishing a Release

```bash
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0

# Create GitHub release with package
gh release create v0.1.0 vault-0.1.0.zip \
  --title "Vault v0.1.0" \
  --notes "Initial release"
```

## Security Considerations

**⚠️ WARNING: This extension is in early development and not production-ready.**

- Funds stored via this extension could be lost
- Only tested on local and staging networks
- Admin controls are critical - protect admin principals
- Test thoroughly before mainnet deployment
- Use test mode for development

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: https://github.com/smart-social-contracts/realms-extension-vault/issues
- **Documentation**: https://github.com/smart-social-contracts/realms-extension-vault
- **Realms Docs**: https://realmsgos.org/docs
