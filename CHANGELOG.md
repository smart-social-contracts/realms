# Changelog

All notable changes to the Realms project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.5] - 2024-12-05

### Added

#### Extension System
- Complete modular extension framework for adding functionality without core modifications
- Extension CLI with `package`, `install`, `uninstall`, and `list` commands
- Auto-route generation for extensions without custom route files
- Category-based sidebar organization (public_services, finances, governance, etc.)
- Profile-based access control for extensions (public, member, admin)
- 13+ built-in extensions: admin_dashboard, vault, citizen_dashboard, public_dashboard, land_registry, llm_chat, notifications, passport_verification, justice_litigation, market_place, demo_loader, welcome, erd_explorer

#### Multi-Realm Deployment (Mundus)
- `realms mundus create` command for deploying multiple realms with shared registry
- Shared dfx instance management across multiple realms
- Unique canister naming per realm preventing conflicts
- Symlinked .dfx directory configuration
- Branch-based port allocation for development
- Accurate port detection for canister URLs

#### Internationalization
- 6-language support: English, Chinese (Simplified), Spanish, French, German, Italian
- Extension-specific translation system with namespacing
- Reactive language switching without page reload
- URL parameter-based locale selection (`?locale=zh-CN`)
- Complete translation coverage for all extensions

#### CLI Enhancements
- `realms realm create` with configurable demo data generation
- `realms import` unified command with auto-detection for JSON/codex files
- `realms ps` task management suite (ls, kill, logs)
- `realms shell` for executing Python code in canisters
- `realms mundus` complete multi-realm operation commands
- Base64 encoding for codex imports eliminating escaping issues

#### Frontend Features
- DUMMY_MODE for fast local development without canister deployment
- Centralized theme system with CSS custom properties
- Institutional grayscale design suitable for government applications
- Category-based sidebar with extension grouping
- Improved logo navigation with fixed z-index handling
- Extension visibility filtering based on authentication

#### Backend Features
- TaskEntity functionality for task-scoped database storage
- Batch processing support for large datasets (avoiding cycle limits)
- Persistent state between task executions
- `realm_generator.py` for realistic demo data generation
- Extension backend integration with direct canister calls
- Structured logging framework with `kybra_simple_logging`

#### Documentation
- Comprehensive extension development guide (`extensions/README.md`)
- CLI reference documentation
- Deployment guide for local, testnet, and mainnet
- Multiple code examples for sync/async operations
- Release notes and changelog

### Changed
- Updated sidebar to use category-based grouping instead of flat list
- Improved extension installation process with better error handling
- Enhanced deployment scripts with SKIP_DFX_START environment variable support
- Refactored authentication to use real Internet Identity (removed dummy principals)
- Simplified `list_transfers` to use `load_paginated` method
- Updated Internet Identity canister ID management with config.js

### Fixed
- JSON double-encoding bug in `realms import` command
- Invisible buttons in PassportVerification.svelte (missing color styling)
- Vault Manager function reference error (`executeTransfer` → `transferTokens`)
- Logo click navigation with z-index conflicts
- Reactive statement execution in Sidebar.svelte
- Translation key display issues across extensions
- dfx instance conflicts in mundus deployments
- Port detection for accurate canister URLs
- TaskEntity namespace conflicts
- Extension visibility filtering for unauthenticated users

### Security
- Enhanced profile-based access control for admin operations
- Improved authentication token handling
- Secure codex import with validation
- Admin-only gate for sensitive operations

## [0.1.4] - 2024-10-XX

### Added
- Initial extension system prototype
- Basic realm deployment workflows
- Task scheduling system
- Core GGG entity framework

## [0.1.3] - 2024-09-XX

### Added
- Frontend with SvelteKit
- Backend with Kybra (Python on IC)
- Internet Identity integration
- Basic ICRC-1 token support

## [0.1.2] - 2024-08-XX

### Added
- Task management system
- Codex execution engine
- Entity relationship framework

## [0.1.1] - 2024-07-XX

### Added
- Initial canister structure
- Basic frontend/backend communication
- Development environment setup

## [0.1.0] - 2024-06-XX

### Added
- Project initialization
- Core architecture design
- dfx configuration
- Initial documentation

---

## Release Types

### Major Release (x.0.0)
- Breaking API changes
- Major architectural changes
- Significant new features

### Minor Release (0.x.0)
- New features
- Non-breaking API additions
- Enhancements

### Patch Release (0.0.x)
- Bug fixes
- Documentation updates
- Minor improvements

---

[0.1.5]: https://github.com/smart-social-contracts/realms/releases/tag/v0.1.5
[0.1.4]: https://github.com/smart-social-contracts/realms/releases/tag/v0.1.4
[0.1.3]: https://github.com/smart-social-contracts/realms/releases/tag/v0.1.3
[0.1.2]: https://github.com/smart-social-contracts/realms/releases/tag/v0.1.2
[0.1.1]: https://github.com/smart-social-contracts/realms/releases/tag/v0.1.1
[0.1.0]: https://github.com/smart-social-contracts/realms/releases/tag/v0.1.0
