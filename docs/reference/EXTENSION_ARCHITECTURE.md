# Extension Architecture

## System Overview

```mermaid
graph TB
    subgraph "Extension Development"
        EXT[Extension Source Code]
        MANIFEST[manifest.json]
        BACKEND[backend/entry.py]
        FRONTEND[frontend/components]
        I18N[i18n/translations]
    end

    subgraph "Extension Installation"
        CLI[Realms CLI]
        PACKAGE[Extension Package .zip]
        INSTALL[install_extensions.sh]
    end

    subgraph "Realm Platform"
        subgraph "Backend Canister"
            RB[Realm Backend]
            EXTMGR[Extension Manager]
            ENTITIES[GGG Entities]
            STORAGE[Stable Storage]
        end
        
        subgraph "Frontend Canister"
            RF[Realm Frontend]
            ROUTER[SvelteKit Router]
            SIDEBAR[Sidebar Component]
            EXTCOMP[Extension Components]
        end
    end

    subgraph "Runtime"
        USER[User Browser]
        II[Internet Identity]
    end

    EXT --> MANIFEST
    EXT --> BACKEND
    EXT --> FRONTEND
    EXT --> I18N
    
    MANIFEST --> CLI
    BACKEND --> CLI
    FRONTEND --> CLI
    I18N --> CLI
    
    CLI --> PACKAGE
    PACKAGE --> INSTALL
    
    INSTALL --> |"Deploy Backend"| EXTMGR
    INSTALL --> |"Deploy Frontend"| ROUTER
    INSTALL --> |"Register Routes"| SIDEBAR
    
    EXTMGR --> ENTITIES
    ENTITIES --> STORAGE
    
    USER --> II
    II --> RF
    RF --> ROUTER
    ROUTER --> EXTCOMP
    EXTCOMP --> |"API Calls"| EXTMGR
    EXTMGR --> |"Response"| EXTCOMP
    
    SIDEBAR --> |"Navigation"| ROUTER
    
    style EXT fill:#e1f5ff
    style MANIFEST fill:#fff3e0
    style RB fill:#f3e5f5
    style RF fill:#e8f5e9
    style USER fill:#fce4ec
```

## Extension Lifecycle

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Src as Extension Source
    participant CLI as Realms CLI
    participant BE as Backend Canister
    participant FE as Frontend Canister
    participant User as End User

    Dev->>Src: Create extension files
    Dev->>Src: Define manifest.json
    Dev->>CLI: realms extension package
    CLI->>CLI: Create .zip package
    
    Dev->>CLI: ./install_extensions.sh
    CLI->>BE: Copy backend/entry.py
    CLI->>FE: Copy frontend components
    CLI->>FE: Copy i18n translations
    CLI->>FE: Generate routes
    
    Dev->>CLI: dfx deploy realm_backend
    CLI->>BE: Deploy with extensions
    
    Dev->>CLI: dfx deploy realm_frontend
    CLI->>FE: Deploy with UI
    
    User->>FE: Access realm
    FE->>User: Load sidebar with extensions
    User->>FE: Click extension
    FE->>BE: Call extension function
    BE->>BE: Execute extension code
    BE->>FE: Return result
    FE->>User: Display response
```

## Extension Structure

```mermaid
graph LR
    subgraph "Extension Package"
        M[manifest.json]
        
        subgraph "Backend"
            BE[backend/entry.py]
            BEINIT[backend/__init__.py]
            LIB[backend/lib/]
        end
        
        subgraph "Frontend"
            FE_IDX[frontend/lib/extensions/id/index.ts]
            FE_COMP[frontend/lib/extensions/id/*.svelte]
            FE_ROUTE[frontend/routes/extensions/id/+page.svelte]
            
            subgraph "i18n"
                EN[i18n/en.json]
                ZH[i18n/zh-CN.json]
                ES[i18n/es.json]
            end
        end
        
        subgraph "Optional"
            README[README.md]
            TESTS[tests/]
            STATIC[static/]
        end
    end
    
    M --> BE
    M --> FE_IDX
    BE --> LIB
    FE_IDX --> FE_COMP
    FE_COMP --> FE_ROUTE
    FE_ROUTE --> EN
    FE_ROUTE --> ZH
    FE_ROUTE --> ES
    
    style M fill:#fff3e0
    style BE fill:#e1f5ff
    style FE_IDX fill:#e8f5e9
    style EN fill:#fce4ec
```

## Extension Categories & Routing

```mermaid
graph TD
    MANIFEST[manifest.json]
    
    subgraph "Manifest Configuration"
        CAT[categories: array]
        PROF[profiles: array]
        PATH[path: string/null]
        SHOW[show_in_sidebar: bool]
    end
    
    subgraph "Categories"
        PS[public_services]
        FIN[finances]
        OVS[oversight]
        SYS[system]
        OTH[other]
    end
    
    subgraph "Sidebar Rendering"
        FILT[Filter by auth + profiles]
        GROUP[Group by category]
        RENDER[Render sidebar items]
    end
    
    subgraph "Routing"
        CUSTOM[Custom: /custom_path]
        DEFAULT[Default: /extensions/id]
        HIDDEN[Hidden: path = null]
    end
    
    MANIFEST --> CAT
    MANIFEST --> PROF
    MANIFEST --> PATH
    MANIFEST --> SHOW
    
    CAT --> PS
    CAT --> FIN
    CAT --> OVS
    CAT --> SYS
    CAT --> OTH
    
    PROF --> FILT
    CAT --> GROUP
    FILT --> RENDER
    GROUP --> RENDER
    SHOW --> RENDER
    
    PATH --> CUSTOM
    PATH --> DEFAULT
    PATH --> HIDDEN
    
    style MANIFEST fill:#fff3e0
    style FILT fill:#ffebee
    style RENDER fill:#e8f5e9
```

## Extension API Call Flow

```mermaid
sequenceDiagram
    participant UI as Extension UI
    participant FE as Frontend API
    participant BE as Backend Canister
    participant EXT as Extension Backend
    participant ENT as GGG Entities
    participant DB as Stable Storage

    UI->>FE: Call extension function
    FE->>BE: extension_sync_call(ext_id, fn_name, args)
    BE->>EXT: Route to backend/entry.py
    EXT->>EXT: Parse JSON args
    
    alt Read Operation
        EXT->>ENT: Query entities
        ENT->>DB: Load from storage
        DB->>ENT: Return data
        ENT->>EXT: Return entities
    else Write Operation
        EXT->>ENT: Modify/create entities
        ENT->>DB: Save to storage
        DB->>ENT: Confirm save
        ENT->>EXT: Return result
    end
    
    EXT->>EXT: Format JSON response
    EXT->>BE: Return {"success": true, "data": {...}}
    BE->>FE: Response
    FE->>UI: Update UI
    
    Note over UI,DB: All extension functions use JSON input/output
```

## Method Override System

```mermaid
graph TB
    subgraph "Extension Backend"
        OVERRIDE[Override Function]
        CODE[Custom Logic]
    end
    
    subgraph "Core System"
        ENTITY[Entity Class]
        METHOD[Original Method]
        REGISTRY[Override Registry]
    end
    
    subgraph "Execution Flow"
        CALL[Method Call]
        CHECK[Check Overrides]
        EXEC[Execute]
    end
    
    OVERRIDE --> REGISTRY
    REGISTRY --> CHECK
    
    CALL --> CHECK
    CHECK --> |"Override exists"| CODE
    CHECK --> |"No override"| METHOD
    
    CODE --> |"Call original"| METHOD
    METHOD --> ENTITY
    
    style OVERRIDE fill:#e1f5ff
    style REGISTRY fill:#fff3e0
    style CHECK fill:#ffebee
```

## Extension Permission Model

```mermaid
graph TD
    USER[User Request]
    AUTH{Authenticated?}
    PROF{Has Profile?}
    PERM{Has Permission?}
    
    EXT_PUB[Public Extension]
    EXT_MEM[Member Extension]
    EXT_ADM[Admin Extension]
    
    ALLOW[Allow Access]
    DENY[Deny Access]
    
    USER --> AUTH
    
    AUTH --> |No| EXT_PUB
    AUTH --> |Yes| PROF
    
    EXT_PUB --> ALLOW
    
    PROF --> |profiles: []| ALLOW
    PROF --> |profiles: [member]| PERM
    PROF --> |profiles: [admin]| PERM
    
    PERM --> |Match| ALLOW
    PERM --> |No Match| DENY
    
    style EXT_PUB fill:#e8f5e9
    style EXT_MEM fill:#fff3e0
    style EXT_ADM fill:#ffebee
    style ALLOW fill:#c8e6c9
    style DENY fill:#ffcdd2
```

## Extension Development Workflow

```mermaid
graph LR
    subgraph "1. Create"
        CREATE[Create Extension]
        STRUCT[Setup Structure]
        MANIFEST[Write manifest.json]
    end
    
    subgraph "2. Develop"
        BACKEND[Implement Backend]
        FRONTEND[Build Frontend]
        I18N[Add Translations]
        TEST[Write Tests]
    end
    
    subgraph "3. Test"
        LOCAL[Install Locally]
        DEPLOY[Deploy to Test Realm]
        DEBUG[Debug & Iterate]
    end
    
    subgraph "4. Package"
        PKG[Package Extension]
        DOC[Write Documentation]
        VER[Version & Tag]
    end
    
    subgraph "5. Distribute"
        RELEASE[Create Release]
        PUBLISH[Publish Package]
        MARKET[Add to Marketplace]
    end
    
    CREATE --> STRUCT
    STRUCT --> MANIFEST
    MANIFEST --> BACKEND
    
    BACKEND --> FRONTEND
    FRONTEND --> I18N
    I18N --> TEST
    
    TEST --> LOCAL
    LOCAL --> DEPLOY
    DEPLOY --> DEBUG
    DEBUG --> |Iterate| BACKEND
    
    DEBUG --> |Ready| PKG
    PKG --> DOC
    DOC --> VER
    
    VER --> RELEASE
    RELEASE --> PUBLISH
    PUBLISH --> MARKET
    %% MARKET = src/marketplace_* canister pair (Basilisk + SvelteKit).
    %% Files live in file_registry; the marketplace stores metadata
    %% pointers, likes, ranking, purchases, audit/verification status,
    %% and developer licenses. See docs/reference/MARKETPLACE.md.
    
    style CREATE fill:#e1f5ff
    style BACKEND fill:#f3e5f5
    style LOCAL fill:#fff3e0
    style PKG fill:#e8f5e9
    style MARKET fill:#fce4ec
```

## Key Concepts

### Extension Types
- **Public Extensions**: Accessible to all users (no profiles required)
- **Member Extensions**: Require authentication and specific profiles
- **Admin Extensions**: Restricted to admin profile only
- **System Extensions**: Core platform functionality

### Extension Categories
- **public_services**: Government services, citizen management
- **finances**: Treasury, payments, trading
- **oversight**: Dashboards, metrics, monitoring
- **system**: Admin tools, configuration
- **other**: General utilities

### Integration Points
1. **Backend Integration**: Extension functions callable via `extension_sync_call` or `extension_async_call`
2. **Frontend Integration**: Svelte components with routing and sidebar integration
3. **Entity Access**: Full access to GGG entity system
4. **Method Overrides**: Can intercept and modify entity method behavior
5. **i18n Support**: Multi-language translation system
6. **Storage**: Share realm's stable storage for persistence

### Security Model
- **Profile-based access control**: Extensions declare required profiles
- **Manifest validation**: CLI validates extension structure
- **Sandboxed execution**: Extensions run in canister environment
- **Input validation**: JSON schema validation for API calls

## Package Manager Extension

Realm administrators can install, update and uninstall both runtime
extensions and codex packages directly from the realm's frontend, without
re-deploying the WASM, by using the `package_manager` extension shipped
under `extensions/extensions/package_manager/`.

### What it does

The extension is an admin-only sidebar entry (profiles: `["admin"]`,
category: `other`) that wraps the existing realm_backend endpoints into
a three-tab UI:

| Tab        | What it does                                                                 | Backend calls                                                                 |
|------------|-------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| Installed  | Lists every runtime extension and codex package currently installed on the realm. Marks rows that have a newer version available in a connected registry. Offers Update / Reload (codex) / Uninstall. | `list_runtime_extensions`, `list_codex_packages`, `uninstall_extension`, `uninstall_codex`, `reload_codex`, plus `install_extension_from_registry` / `install_codex_from_registry` for updates |
| Browse     | For each `file_registry` canister this realm is linked to (`status().registries`), fetches `/api/extensions` and `/api/codices` and shows everything publishable. Cross-references with the installed list to show install / update buttons. | HTTP GET to `{registry}/api/extensions` + `{registry}/api/codices` (via `$lib/file-registry-client`), then `install_extension_from_registry` / `install_codex_from_registry` |
| Upload     | Lets the admin pick a folder of files (using `<input webkitdirectory>`) and pushes them in a single update call. Useful for one-off installs or local dev. Warns when the total payload exceeds the ~1.8 MB ICP ingress safe limit. | `install_extension({extension_id, files})` or `install_codex({codex_id, files, run_init})` |

### Permissions

All four mutating endpoints are gated by either `Operations.EXTENSION_INSTALL`
/ `Operations.EXTENSION_UNINSTALL` or `Operations.CODEX_INSTALL` /
`Operations.CODEX_UNINSTALL`. The default `ADMIN` profile (`Profiles.ADMIN`
in `src/realm_backend/ggg/system/user_profile.py`) is granted
`Operations.ALL` and therefore passes those checks. No new role wiring is
required for the package manager to work.

If you want a finer-grained role (e.g. a "package manager" sub-admin who
can install but not configure other parts of the realm), grant
`EXTENSION_INSTALL`, `EXTENSION_UNINSTALL`, `CODEX_INSTALL`, and
`CODEX_UNINSTALL` to a custom profile in `Profiles`.

### Sidebar live-reload

After every successful install / uninstall the extension dispatches a
`window` event (`realms:extensions-changed`). `Sidebar.svelte` listens for
this event and re-runs `get_sidebar_manifests()` so the new entry appears
immediately, without a full page reload.

### Caveats

- **Hot-loading**: backend extensions reload via `_load_module(force=True)`
  in `core/runtime_extensions.py`. Codex `init.py` runs synchronously inside
  the install update call, so a buggy `init.py` surfaces as the install
  response — the UI displays the `init_warning` field returned by the
  install call.
- **Frontend bundle**: a runtime extension's compiled UI is fetched from
  the file_registry the extension was installed from
  (see `extension-loader.ts`). After install the extension routes are
  available immediately, but the user may need to navigate to the new
  sidebar entry to mount the bundle.
- **Trust**: an admin can install arbitrary code from any registry the
  realm is linked to. There is no signature/checksum verification step in
  the runtime install path; if you need a "trusted publishers" gate, add
  it on top of `install_extension_from_registry` (the registry has an ACL
  for *publishing*, not for *consuming*).
- **Ingress limits**: ICP update calls have a ~2 MB ingress limit. The
  Upload tab warns when the total payload exceeds ~1.8 MB; for larger
  payloads, publish the extension to a `file_registry` and use the Browse
  tab instead — the registry-pull path uses inter-canister calls and
  isn't subject to the same limit.
