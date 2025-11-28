# Contributing to Vault Manager Extension

Thank you for your interest in contributing to the Vault Manager extension for Realms!

## Development Setup

### Prerequisites
- Python 3.10.7
- dfx (Internet Computer SDK)
- Realms CLI (installed via pip or from source)

### Setup Steps

1. **Clone Realms Repository**
   ```bash
   git clone https://github.com/smart-social-contracts/realms.git
   cd realms
   git checkout v1.2.3  # Use specific version for compatibility
   ```

2. **Install Realms CLI in Development Mode**
   ```bash
   pip install -e cli/
   ```

3. **Clone This Extension Repository**
   ```bash
   cd ..
   git clone https://github.com/smart-social-contracts/realms-extension-vault.git
   cd realms-extension-vault
   ```

4. **Install Extension Locally**
   ```bash
   cd ../realms
   realms extension install --source ../realms-extension-vault/
   ```

5. **Start Local Network**
   ```bash
   dfx start --clean --background
   ```

6. **Deploy for Testing**
   ```bash
   realms realm deploy --network local
   ```

## Project Structure

```
realms-extension-vault/
├── backend/              # Extension backend code
│   ├── vault_lib/       # Core vault logic (reusable library)
│   │   ├── candid_types.py
│   │   ├── constants.py
│   │   ├── entities.py
│   │   └── ic_util_calls.py
│   └── entry.py         # Extension API entry point
├── frontend/            # Frontend components
│   ├── lib/
│   ├── routes/
│   └── i18n/
├── tests/               # Test suite
├── manifest.json        # Extension metadata
├── requirements.txt     # Python dependencies
├── README.md
├── CHANGELOG.md
└── LICENSE
```

## Making Changes

### Backend Changes

1. Edit files in `backend/` directory
2. Test locally:
   ```bash
   cd ../realms
   realms extension install --source ../realms-extension-vault/
   realms realm deploy --network local
   ```

3. Verify changes:
   ```bash
   dfx canister call realm_backend extension_call '("vault", "get_status", "{}")'
   ```

### Frontend Changes

1. Edit Svelte components in `frontend/`
2. Rebuild frontend:
   ```bash
   cd realms/src/realm_frontend
   npm run build
   ```
3. Test in browser

### Testing

```bash
cd realms-extension-vault
pytest tests/ -v
```

## Code Style

- **Python**: Follow PEP 8
- **Logging**: Use `kybra_simple_logging` for all logging
- **Error Handling**: Always catch exceptions and return JSON errors
- **Documentation**: Add docstrings to all public functions

### Example Function

```python
def get_balance(args: str) -> str:
    """
    Get balance for a principal.
    
    Args:
        args: JSON string with {"principal_id": "xxx"}
    
    Returns:
        JSON string with {"success": bool, "data": {...}}
    
    Raises:
        No exceptions - errors are returned in JSON response
    """
    logger.info(f"get_balance called with args: {args}")
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### Examples

```
feat: add balance caching for improved performance
fix: correct transaction timestamp handling
docs: update README with new installation steps
test: add integration tests for transfer function
```

## Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feat/my-feature
   ```

3. **Make your changes**
   - Write tests for new functionality
   - Update documentation
   - Follow code style guidelines

4. **Run tests**
   ```bash
   pytest tests/ -v
   ```

5. **Commit your changes**
   ```bash
   git commit -m "feat: add new feature"
   ```

6. **Push to your fork**
   ```bash
   git push origin feat/my-feature
   ```

7. **Open a Pull Request**
   - Describe what changed and why
   - Reference any related issues
   - Wait for review

## Release Process

1. **Update version** in `manifest.json` and `CHANGELOG.md`
2. **Tag release**
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

3. **Package extension**
   ```bash
   realms extension package .
   ```

4. **Create GitHub release**
   - Upload `vault-0.2.0.zip`
   - Copy changelog entry to release notes

## Questions?

- Open an issue for bugs or feature requests
- Join discussions for general questions
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
