# Changelog

All notable changes to the Vault extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-10-16

### Added
- Initial release of Vault extension
- Embedded vault logic directly in realm_backend canister
- ckBTC balance tracking and management
- Transaction history sync from ICRC ledger
- Admin-controlled token transfers
- Test mode support for development
- Integration with Realms Treasury entity
- Comprehensive documentation and examples

### Architecture
- Migrated from separate vault canister to embedded extension model
- Eliminated inter-canister call overhead
- Direct integration with realm entities for atomic operations

### Dependencies
- kybra>=0.10.0
- kybra-simple-db>=1.0.0
- kybra-simple-logging>=1.0.0

### Security
- ⚠️ WARNING: Not production-ready, use only for testing
- Admin-only transfer restrictions
- Balance validation and tracking

[0.1.0]: https://github.com/smart-social-contracts/realms-extension-vault/releases/tag/v0.1.0
