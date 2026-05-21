# Access Control Architecture

This document describes the entity relationship model for role-based access control (RBAC), department management, and dynamic extension visibility in Realms.

## Entity Relationship Diagram

```mermaid
erDiagram
    User ||--o{ UserProfile : "holds (M2M)"
    User ||--o{ Department : "member of (M2M)"
    User ||--o{ Extension : "direct grant (M2M)"
    User ||--o| Department : "heads"

    Department ||--o{ Extension : "grants access (M2M)"
    Department ||--o{ Permission : "holds (M2M)"
    Department ||--o| Department : "parent/child"

    UserProfile ||--o{ Extension : "baseline access (M2M)"
    UserProfile ||--o{ Permission : "holds (M2M)"

    Extension {
        string name PK "e.g. voting, vault"
        string description
    }

    Department {
        string name PK
        string description
        ref head "User (FK)"
        ref parent "Department (FK)"
    }

    User {
        string id PK "Internet Identity principal"
        string nickname
        string avatar
    }

    UserProfile {
        string name PK "e.g. admin, member, developer"
        string allowed_to "comma-separated Operations"
    }

    Permission {
        string name PK
        string category
        string scope
    }
```

## Extension Visibility Resolution

A user can see an extension if **any** of the following is true:

```mermaid
flowchart TD
    Start[User requests sidebar] --> Query[get_my_extensions]
    Query --> DirectCheck{Direct grant?}
    DirectCheck -->|Yes| Visible[Extension visible]
    DirectCheck -->|No| DeptCheck{Member of a dept<br/>with this extension?}
    DeptCheck -->|Yes| Visible
    DeptCheck -->|No| ProfileCheck{Holds a profile<br/>linked to this extension?}
    ProfileCheck -->|Yes| Visible
    ProfileCheck -->|No| Hidden[Extension hidden]
```

The formula is:

```
visible_extensions =
    user.extensions
    ∪ union(dept.extensions for dept in user.departments)
    ∪ union(profile.extensions for profile in user.profiles)
```

## Department Hierarchy & Scoped Delegation

```mermaid
flowchart TD
    RealmAdmin["Realm Admin<br/>(Operations.ALL)"]
    RealmAdmin -->|creates| Dept[Department]
    Dept -->|has| Head[Department Head]
    Head -->|can assign members| Members[Department Members]
    Head -->|scoped delegation| Assign["Assign delegated profiles<br/>within their department"]

    Dept -->|child of| ParentDept[Parent Department]
    Dept -->|contains| SubDept[Sub-Departments]
```

Department heads can assign/revoke roles **only** if:
1. They are the `head` of the department, AND
2. The department has a `delegate:<profile_name>` permission

This enables scoped delegation without granting global `ROLE_ASSIGN`.

## Data Flow: Extension Installation

```mermaid
sequenceDiagram
    participant CLI as Realms CLI
    participant Registry as File Registry
    participant Installer as Installer Canister
    participant Backend as Realm Backend

    CLI->>Registry: publish extension files
    CLI->>Installer: submit deploy job
    Installer->>Registry: fetch extension files
    Installer->>Backend: install_extension(files)
    Backend->>Backend: write files to /extensions/
    Backend->>Backend: load manifest.json
    Backend->>Backend: _seed_extension_entity()
    Note over Backend: Create Extension entity<br/>Link to UserProfile baselines
    Backend->>Backend: load entry.py (if exists)
```

## Access Manager Extension

The `access_manager` extension provides a UI for managing all these relationships:

| Tab | Purpose |
|-----|---------|
| **Departments** | Create/delete departments, assign heads, manage members |
| **Extensions** | View/edit access grants per user, department, or profile |
| **Users** | View user access summary, assign/revoke profiles |

Accessible to users with `admin` or `user_manager` profiles.
