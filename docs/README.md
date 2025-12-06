# Realms Platform Documentation

<p align="center">
  <img src="img/logo_horizontal.svg" alt="Realms Logo" width="400"/>
</p>

Complete documentation for building and deploying governance systems on the Internet Computer.

---

## 📖 Start Here

**New to Realms?** Choose your path:
- **[Non-Technical Introduction](./NON_TECHNICAL_INTRO.md)** - Understand what Realms is and why it exists
- **[Technical Introduction](./TECHNICAL_INTRO.md)** - Architecture, APIs, and development guide

---

## 🚀 Quick Start by Role

### 👤 End Users
- [Citizen Dashboard](../extensions/citizen_dashboard/README.md) - Manage your account
- [Governance Tutorial](./GOVERNANCE_TUTORIAL.md) - Vote on proposals

### 👨‍💼 Realm Operators  
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Deploy your realm
- [Realm Registration](./REALM_REGISTRATION_GUIDE.md) - Register with central registry
- [CLI Reference](./CLI_REFERENCE.md) - All commands

### 🔧 Extension Developers
- [Extension Guide](../extensions/README.md) - Build extensions
- [Method Overrides](./METHOD_OVERRIDE_SYSTEM.md) - Override entity methods
- [Testing Guide](../extensions/_shared/testing/README.md) - Test your extensions

### 💻 Platform Developers
- [Core Entities](./CORE_ENTITIES.md) - Data model reference
- [API Reference](./API_REFERENCE.md) - Backend endpoints
- [Frontend Architecture](./FRONTEND_ARCHITECTURE.md) - Svelte components

---

## 📚 Core Documentation

### Platform Fundamentals
- **[Core Entities](./CORE_ENTITIES.md)** - All 30+ entity types with examples
- **[API Reference](./API_REFERENCE.md)** - Complete backend API
- **[CLI Reference](./CLI_REFERENCE.md)** - All command-line tools
- **[Frontend Architecture](./FRONTEND_ARCHITECTURE.md)** - UI structure and patterns

### Deployment & Operations
- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Local → Staging → Production
- **[Realm Registration](./REALM_REGISTRATION_GUIDE.md)** - Join the registry
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Common issues

### Advanced Features
- **[Task System](./TASK_ENTITY.md)** - Batch processing with TaskEntity
- **[Multi-Step Tasks](./MULTI_STEP_TASKS_IMPLEMENTATION.md)** - Complex workflows
- **[Method Override System](./METHOD_OVERRIDE_SYSTEM.md)** - Extension method injection
- **[Governance Tutorial](./GOVERNANCE_TUTORIAL.md)** - Proposals and voting

### Extension Development
- **[Extension Guide](../extensions/README.md)** - Complete development guide
- **[Available Extensions](../extensions/)** - 15+ built-in extensions
- **[Testing Extensions](../extensions/_shared/testing/README.md)** - Test patterns

---

## 📖 By Topic

### Entities & Data Model
```
Users & Identity          Governance              Finance
├─ User                   ├─ Proposal             ├─ Treasury
├─ Member                 ├─ Vote                 ├─ Instrument
├─ Human                  ├─ Mandate              ├─ Balance
├─ Identity               └─ Codex                ├─ Transfer
└─ Organization                                   └─ Trade

Tasks & Automation        Services                Registry
├─ Task                   ├─ Service              ├─ Realm
├─ TaskSchedule           ├─ License              └─ Registry
├─ Codex                  ├─ Dispute
└─ TaskEntity             └─ Permission
```
→ [Full Entity Reference](./CORE_ENTITIES.md)

### Key APIs
- **Entity Management** - CRUD operations for all entities
- **Extension System** - Call extension functions  
- **Task Scheduling** - Automated workflows
- **User Management** - Authentication & profiles
- **Registry** - Realm discovery

→ [Complete API Docs](./API_REFERENCE.md)

### CLI Commands
```bash
# Realm Management
realms realm create          # Create new realm
realms realm deploy          # Deploy canisters
realms import          # Import data

# Task Management  
realms run             # Execute code
realms ps ls           # List tasks
realms ps logs         # View logs

# Extensions
realms extension list      # List extensions
realms extension install   # Install extension

# Registry
realms registry add    # Register realm
realms registry list   # List realms
```
→ [Full CLI Reference](./CLI_REFERENCE.md)

---

## 🎯 Common Tasks

### Deploy a Realm
```bash
# 1. Create with demo data
realms realm create --random --citizens 100 --organizations 10

# 2. Deploy locally
cd generated_realm
./scripts/2-deploy-canisters.sh

# 3. Upload data
./scripts/3-upload-data.sh
```
→ [Deployment Guide](./DEPLOYMENT_GUIDE.md)

### Create a Governance Proposal
```python
from ggg import Proposal, User

proposal = Proposal(
    proposal_id="tax_reform_2024",
    title="Reduce Tax Rate to 10%",
    description="Proposal to reduce realm tax rate",
    proposer=User["admin"],
    status="voting",
    required_threshold=0.51
)
```
→ [Governance Tutorial](./GOVERNANCE_TUTORIAL.md)

### Build an Extension
```bash
# 1. Create extension structure
mkdir -p extensions/my_extension/backend
mkdir -p extensions/my_extension/frontend

# 2. Add manifest.json
# 3. Implement backend/entry.py
# 4. Create frontend components

# 5. Install
realms extension install-from-source
```
→ [Extension Guide](../extensions/README.md)

---

## 📋 Implementation Guides

| Guide | Description | Status |
|-------|-------------|--------|
| [TASK_ENTITY.md](./TASK_ENTITY.md) | Batch processing for large datasets | ✅ Complete |
| [METHOD_OVERRIDE_SYSTEM.md](./METHOD_OVERRIDE_SYSTEM.md) | Extension method injection | ✅ Complete |
| [MULTI_STEP_TASKS_IMPLEMENTATION.md](./MULTI_STEP_TASKS_IMPLEMENTATION.md) | Complex task workflows | ✅ Complete |
| [REALM_REGISTRATION_GUIDE.md](./REALM_REGISTRATION_GUIDE.md) | Registry integration | ✅ Complete |

---

## 📝 Examples

| Example | Description | Documentation |
|---------|-------------|---------------|
| **Demo Mundus** | Multi-realm ecosystem with 3 realms and registry | [EXAMPLE_DEMO.md](./EXAMPLE_DEMO.md) |
| **File Download** | HTTP outcalls to download files from the internet | [EXAMPLE_FILE_DOWNLOAD.md](./EXAMPLE_FILE_DOWNLOAD.md) |

See the [examples/](../examples/) directory for code samples.

---

## 🔗 External Resources

- **Main Repository** - [GitHub](https://github.com/smart-social-contracts/realms)
- **Realm Registry** - [registry.realmsgos.org](https://registry.realmsgos.org)
- **Sandbox Realm** - [sandbox.realmsgos.org](https://sandbox.realmsgos.org)
- **Internet Computer** - [internetcomputer.org](https://internetcomputer.org)

---

## 🆘 Need Help?

- **Troubleshooting** - [Common issues and solutions](./TROUBLESHOOTING.md)
- **Examples** - [Code examples](../examples/)
- **Extensions** - [Extension examples](../extensions/)
