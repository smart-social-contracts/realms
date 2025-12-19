# Realms Release Notes

## Version 0.1.5 (December 2024)

### 🎉 Overview

Realms 0.1.5 represents a major milestone in building a comprehensive governance operating system framework on the Internet Computer. This release introduces a powerful extension system, multi-realm deployment capabilities, internationalization support, and numerous developer experience improvements.

---

## 🚀 Major Features

### Extension System Architecture
- **Modular Extension Framework**: Complete plugin architecture allowing developers to extend realm functionality without modifying core code
- **13+ Built-in Extensions**: Including admin dashboard, citizen dashboard, vault manager, land registry, LLM chat, passport verification, and more
- **Extension CLI Tools**: Full lifecycle management with `realms extension` commands for packaging, installation, and distribution
- **Auto-Route Generation**: Automatic creation of frontend routes for extensions without custom route files
- **Category-Based Organization**: Extensions organized by categories (public_services, finances, governance, etc.) in sidebar navigation
- **Profile-Based Access Control**: Granular visibility control based on user authentication and profile permissions

### Multi-Realm Deployment (Mundus)
- **Mundus System**: Deploy multiple realm instances with shared registry on a single dfx instance
- **Unique Canister Management**: Each realm gets unique canister IDs preventing conflicts
- **Shared dfx Instance**: Single dfx process manages all realms efficiently
- **Realm Registry**: Central registry for tracking and managing multiple realms
- **Symlinked Configuration**: Smart symlink management for shared .dfx directories
- **Port-Based Network Isolation**: Branch-based port allocation for development environments

### Internationalization (i18n)
- **6-Language Support**: Complete translations for English, Chinese, Spanish, French, German, and Italian
- **Extension Translation System**: Extensions can provide their own localized content
- **Reactive Language Switching**: Instant language changes without page reload
- **Translation Namespacing**: Organized translation structure with `extensions.{extension_id}.*` pattern
- **URL Parameter Support**: Language selection via `?locale=zh-CN` URL parameter

### CLI Enhancements
- **Unified Import Command**: Single `realms import` handles both JSON data and Python codex files with auto-detection
- **Realm Creation Workflow**: `realms realm create` with configurable demo data generation
- **Task Management**: `realms ps` commands for listing, killing, and monitoring scheduled tasks
- **Shell Execution**: `realms shell` for running Python code directly in realm canisters
- **Mundus Commands**: Complete `realms mundus` suite for multi-realm operations

---

## 🎨 Frontend & UI Improvements

### Theme System
- **Institutional Grayscale Design**: Sophisticated monochrome theme suitable for government applications
- **Centralized Theme Configuration**: Single-file theme management (`theme.ts`)
- **CSS Custom Properties**: Dynamic theming with runtime switching capability
- **Design System Utilities**: Pre-built utility functions for consistent styling
- **Dark Mode Support**: Built-in support for theme variants

### Navigation & UX
- **Category-Based Sidebar**: Logical grouping of extensions by function
- **Improved Logo Navigation**: Fixed logo clickability with proper z-index handling
- **Extension Visibility Logic**: Smart filtering based on authentication status and user profiles
- **Responsive Design**: Consistent experience across mobile, tablet, and desktop

### DUMMY_MODE Development
- **Fast Local Development**: Mock backend for instant HMR without canister deployment
- **Realistic Mock Data**: Complete API mocks matching production structure
- **Auto-Authentication**: Bypass Internet Identity for rapid testing
- **Easy Toggle**: Switch between mock and real modes with environment variable

---

## 🛠️ Backend & Core Improvements

### Task System
- **TaskEntity Functionality**: Task-scoped database storage for batch processing
- **Cycle Limit Management**: Process large datasets in batches to avoid ICP cycle limits
- **Persistent State**: State preservation between task executions
- **Namespace Isolation**: Automatic namespace per task prevents conflicts

### Data Generation & Management
- **Realm Generator**: `realm_generator.py` creates realistic demo data with configurable parameters
- **Bulk Data Loading**: `demo_loader` extension with batch processing support
- **JSON & Codex Import**: Import realm data and Python automation scripts
- **Base64 Encoding**: Codex files use base64 to eliminate escaping issues

### Extension Backend
- **Direct Canister Integration**: Extensions run inside realm_backend with no inter-canister overhead
- **Atomic Operations**: Extensions share stable memory with realm entities
- **Logging Framework**: Structured logging with `kybra_simple_logging`
- **Error Handling**: Comprehensive JSON-based error responses

---

## 🔧 Developer Experience

### Documentation
- **Comprehensive README**: Complete getting started, extension development, and API reference
- **Extension Development Guide**: Step-by-step guide in `extensions/README.md`
- **CLI Reference**: Full documentation of all CLI commands
- **Deployment Guide**: Detailed deployment instructions for local, testnet, and mainnet
- **Code Examples**: Multiple working examples for sync/async operations, batch processing, and extensions

### Testing & CI/CD
- **Integration Test Framework**: Comprehensive testing for realm operations
- **GitHub Actions Workflows**: CI pipelines for branches and main
- **Extension Testing**: Test structure and examples for extension development
- **Manual Deploy Actions**: Staging deployment workflows

### Dev Container
- **VSCode Dev Container**: Pre-configured development environment
- **Python & TypeScript Support**: Extensions for Python, Motoko, and TypeScript development
- **Port Forwarding**: Configured ports for local development

---

## 📦 Extensions

### New Extensions
- **Admin Dashboard**: Complete realm administration interface
- **Vault Manager**: ICRC-1 token and treasury management
- **Citizen Dashboard**: Member-facing dashboard with personal data
- **Public Dashboard**: Public statistics and realm information
- **Land Registry**: Property and land management system
- **LLM Chat**: AI-powered chat assistant
- **Notifications**: Notification system with real-time updates
- **Passport Verification**: Identity verification workflows
- **Justice Litigation**: Legal system management
- **Demo Loader**: Bulk data import and realm initialization
- **Market Place**: Extension marketplace and discovery
- **Welcome**: Onboarding and introduction extension
- **ERD Explorer**: Entity relationship visualization

### Extension Features
- **Manifest System**: Declarative configuration with version compatibility
- **Permission System**: Profile-based access control (admin, member, public)
- **Frontend Components**: Svelte components with TypeScript support
- **Backend Entry Points**: Python functions callable from realm backend
- **Static Assets**: Extension-specific images, icons, and resources

---

## 🐛 Bug Fixes

### Authentication
- Removed dummy principal logic in favor of real Internet Identity integration
- Fixed authentication state management across components
- Improved principal handling in AuthButton component

### Frontend
- Fixed invisible buttons in PassportVerification extension
- Resolved Vault Manager function reference error (`executeTransfer` → `transferTokens`)
- Corrected logo click navigation issues with z-index conflicts
- Fixed reactive statement execution in Sidebar.svelte
- Resolved translation key display issues across all extensions

### Backend
- Fixed JSON double-encoding bug in import command
- Improved pagination in `list_transfers` function
- Enhanced error handling in extension calls
- Resolved TaskEntity namespace conflicts

### Deployment
- Fixed dfx instance conflicts in mundus deployments
- Corrected port detection for accurate canister URLs
- Improved symlink management for .dfx directories
- Enhanced deployment script error handling

---

## 📊 Technical Improvements

### Performance
- Batch processing for large datasets (100 users per batch)
- Optimized extension loading and initialization
- Improved frontend build times with DUMMY_MODE

### Security
- Profile-based access control for extensions
- Admin-only operations properly gated
- Secure codex import with validation
- Authentication token handling improvements

### Code Quality
- TypeScript integration across frontend
- Python type hints and validation
- Comprehensive error handling patterns
- Consistent code style and formatting

---

## 🔄 Migration Guide

### Breaking Changes
None in this release. All changes are backward compatible.

### Recommended Updates
1. **Extensions**: Run `./scripts/install_extensions.sh` to update all extensions
2. **CLI**: Update to latest CLI version: `pip install -e cli/`
3. **Theme**: Components using custom styling may benefit from centralized theme utilities
4. **i18n**: Extensions should add translation files for multilingual support

---

## 📚 API Changes

### New CLI Commands
```bash
realms realm create --random --deploy
realms mundus create --deploy
realms import <file>
realms extension package --extension-id <id>
realms ps ls
realms ps kill <task_id>
realms shell --file <script.py>
```

### New Backend APIs
- `extension_call(extension_id, function_name, args)` - Call extension function
- `extension_async_call(extension_id, function_name, args)` - Async extension call
- `execute_code(code, task_name)` - Execute Python code in canister
- `create_task_entity_class(task_name)` - Create task-scoped entity class

---

## 🎯 Use Cases

### Government & Institutional
- Municipal governance systems
- Institutional decision-making platforms
- Public service delivery systems
- Regulatory compliance frameworks

### Development & Testing
- Multi-realm staging environments
- Extension development and testing
- Integration testing across realms
- Demo and showcase deployments

### Research & Education
- Governance mechanism research
- Blockchain education platforms
- Smart contract prototyping
- Policy simulation systems

---

## 📦 Installation

### Quick Start
```bash
# Install CLI
pip install -e cli/

# Create and deploy a realm
realms realm create --random --citizens 100 --deploy

# Or deploy a multi-realm ecosystem
realms mundus create --deploy
```

### Requirements
- Python 3.10+
- dfx 0.15.0+
- Node.js 18+
- npm 9+

---

## 🔮 What's Next (v0.2.0 Roadmap)

### Planned Features
- **Extension Marketplace**: Public marketplace for discovering and installing extensions
- **Inter-Realm Communication**: Protocols for realms to interact and share data
- **Advanced Governance**: Enhanced voting mechanisms and proposal systems
- **Analytics Dashboard**: Comprehensive analytics and monitoring tools
- **Mobile Apps**: Native mobile applications for iOS and Android
- **Plugin SDK**: Dedicated SDK for third-party extension development

### Under Consideration
- WebAssembly runtime for non-Python languages
- GraphQL API layer
- Real-time collaboration features
- Advanced permission system with role hierarchies
- Blockchain interoperability (Ethereum, Bitcoin)

---

## 🙏 Acknowledgments

Thanks to all contributors who helped make this release possible. Special thanks to the Internet Computer community and the developers who provided feedback and testing.

---

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

---

## 🔗 Resources

- **Documentation**: [docs/](./docs/)
- **Examples**: [examples/](./examples/)
- **Extensions**: [extensions/](./extensions/)
- **CLI Reference**: [docs/CLI_REFERENCE.md](./docs/CLI_REFERENCE.md)
- **Deployment Guide**: [docs/DEPLOYMENT_GUIDE.md](./docs/DEPLOYMENT_GUIDE.md)
- **Sandbox**: https://demo.realmsgos.org
- **Registry**: https://registry.realmsgos.org

---

## 📞 Support

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check docs/ folder for guides
- **Examples**: See examples/ for working code samples

---

**Full Changelog**: https://github.com/smart-social-contracts/realms/compare/v0.1.4...v0.1.5
