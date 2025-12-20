# Reference Documentation

Complete reference documentation for the Realms GOS platform.

## Core Documentation

### Platform Fundamentals
- **[Core Entities](./CORE_ENTITIES)** - All 30+ entity types with examples
- **[API Reference](./API_REFERENCE)** - Complete backend API
- **[CLI Reference](./CLI_REFERENCE)** - All command-line tools
- **[Frontend Architecture](./FRONTEND_ARCHITECTURE)** - UI structure and patterns

### Architecture
- **[Extension Architecture](./EXTENSION_ARCHITECTURE)** - Build custom extensions
- **[Method Override System](./METHOD_OVERRIDE_SYSTEM)** - Extension method injection
- **[Frontend Architecture](./FRONTEND_ARCHITECTURE)** - Svelte components and routing

### Advanced Features
- **[Scheduled Tasks](./SCHEDULED_TASKS)** - Task scheduling and automation
- **[Task Entity](./TASK_ENTITY)** - Batch processing for large datasets
- **[Multi-Step Tasks](./MULTI_STEP_TASKS_IMPLEMENTATION)** - Complex workflows

### Deployment & Operations
- **[Deployment Guide](./DEPLOYMENT_GUIDE)** - Local → Staging → Production
- **[Realm Registration](./REALM_REGISTRATION_GUIDE)** - Join the registry
- **[Troubleshooting](./TROUBLESHOOTING)** - Common issues and solutions

## Examples

- **[Demo Example](./EXAMPLE_DEMO)** - Multi-realm ecosystem with registry
- **[File Download](./EXAMPLE_FILE_DOWNLOAD)** - HTTP outcalls to download files

## Quick Links

### By Role

**End Users**
- Citizen Dashboard - Manage your account
- [Governance Tutorial](./GOVERNANCE_TUTORIAL) - Vote on proposals

**Realm Operators**
- [Deployment Guide](./DEPLOYMENT_GUIDE) - Deploy your realm
- [Realm Registration](./REALM_REGISTRATION_GUIDE) - Register with central registry
- [CLI Reference](./CLI_REFERENCE) - All commands

**Extension Developers**
- [Extension Architecture](./EXTENSION_ARCHITECTURE) - Build extensions
- [Method Overrides](./METHOD_OVERRIDE_SYSTEM) - Override entity methods

**Platform Developers**
- [Core Entities](./CORE_ENTITIES) - Data model reference
- [API Reference](./API_REFERENCE) - Backend endpoints
- [Frontend Architecture](./FRONTEND_ARCHITECTURE) - Svelte components

## Data Model Overview

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

See [Core Entities](./CORE_ENTITIES) for complete details.

## CLI Commands Overview

```bash
# Realm Management
realms realm create          # Create new realm
realms realm deploy          # Deploy canisters
realms import                # Import data

# Task Management
realms run                   # Execute code
realms ps ls                 # List tasks
realms ps logs               # View logs

# Extensions
realms extension list        # List extensions
realms extension install     # Install extension

# Registry
realms registry add          # Register realm
realms registry list         # List realms
```

See [CLI Reference](./CLI_REFERENCE) for complete command documentation.
