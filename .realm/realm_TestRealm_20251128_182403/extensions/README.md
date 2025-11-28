# Realms Extensions Repository

Welcome to the consolidated Realms extensions repository! This repository contains all official extensions for the Smart Social Contracts platform.

## 📦 Available Extensions

This repository includes the following extensions:

- **admin_dashboard** - Administrative dashboard for realm management
- **member_dashboard** - Member-facing dashboard for personal account management
- **erd_explorer** - Entity Relationship Diagram explorer for the realm database
- **justice_litigation** - Justice and litigation management system
- **land_registry** - Land registry and property management
- **llm_chat** - AI-powered chat assistant
- **market_place** - Marketplace for goods and services
- **metrics** - Analytics and metrics dashboard
- **notifications** - Notification system for realm events
- **passport_verification** - Identity verification and passport services
- **public_dashboard** - Public-facing dashboard for realm statistics
- **test_bench** - Testing and development utilities
- **vault** - Secure vault for digital assets and credentials
- **voting** - Voting and governance system
- **welcome** - Welcome screen and onboarding

## 🚀 Quick Start

1. **Clone this repository** to get all extensions
2. **Navigate to an extension** folder to view its specific implementation
3. **Create your own extension** following the structure below
4. **Test locally** using the provided CLI tools
5. **Package and distribute** your extension

## 📁 Extension Structure

Each extension follows a standardized directory structure:

```
extensions/{your_extension_id}/
├── manifest.json              # Extension metadata
├── backend/                   # Python backend code
│   ├── __init__.py
│   └── entry.py              # Main backend entry point
│   
└── frontend/                 # Frontend components
    ├── lib/extensions/{extension_id}/
    │   ├── index.ts          # TypeScript entry point
    │   └── *.svelte          # Svelte components
    ├── i18n/                 # Internationalization files
    │   ├── en.json
    │   ├── zh-CN.json
    │   └── ...
    └── static/               # Static assets (images, videos, etc.)
```

## 📋 Manifest Configuration

### Root Manifest (`manifest.json`)

```json
{
  "name": "your_extension_name",
  "version": "1.0.0",
  "description": "Brief description of your extension",
  "author": "Your Name",
  "permissions": ["read", "write"],
  "profiles": ["member", "admin"],
  "categories": ["public_services", "finances", "oversight", "system", "other"],
  "icon": "table",
  "doc_url": "https://github.com/yourname/your-extension",
  "url_path": null,
  "show_in_sidebar": true
}
```

**Fields:**
- `name`: Extension identifier (use underscores, no hyphens)
- `version`: Semantic version (x.y.z)
- `description`: User-facing description
- `author`: Your name or organization
- `permissions`: Array of required permissions
- `profiles`: User profiles that can access this extension
- `categories`: Grouping categories for sidebar organization
- `icon`: Icon name (from Flowbite icons) (optional) (default: a default icon will be used)
- `doc_url`: Documentation URL (optional)
- `url_path`: Custom path for the extension (optional) (default: the extension name, e.g. `/welcome`)
- `show_in_sidebar`: Whether to show the extension in the sidebar (optional) (default: true)


**Available Categories:**
- `public_services`: Government and public sector functionality (member services, land registry, justice, identity verification)
- `finances`: Financial and economic tools (vault management, treasury, payments)
- `oversight`: Monitoring, analytics, and intelligence tools (dashboards, metrics, AI assistants)
- `system`: Platform administration and management (marketplace, configuration, deployment)
- `other`: General purpose extensions and utilities

## 🐍 Backend Development

### Entry Point (`backend/entry.py`)

```python
"""
Your Extension Backend Entry Point
"""

def your_function_name(args):
    """
    Main extension function that can be called from frontend
    
    Args:
        args: Dictionary containing function parameters
        
    Returns:
        Any serializable result (string, dict, list, etc.)
    """
    # Your backend logic here
    return "Success message or data"

# Additional helper functions
def helper_function():
    pass
```


## 🎨 Frontend Development

### Svelte Components

Create your main component and any sub-components:

```svelte
<!-- YourMainComponent.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { callExtension } from '$lib/api/extensions';
  
  let data = null;
  let loading = false;
  
  async function loadData() {
    loading = true;
    try {
      const result = await callExtension('your_extension_name', 'your_function_name', {
        // Parameters for your backend function
      });
      data = result;
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      loading = false;
    }
  }
  
  onMount(() => {
    loadData();
  });
</script>

<div class="p-6">
  <h1 class="text-2xl font-bold mb-4">Your Extension</h1>
  
  {#if loading}
    <p>Loading...</p>
  {:else if data}
    <p>Data: {JSON.stringify(data)}</p>
  {:else}
    <p>No data available</p>
  {/if}
</div>
```

## 🌍 Internationalization

Create translation files in `frontend/i18n/`:

### English (`en.json`)
```json
{
  "title": "Your Extension",
  "description": "Extension description",
  "buttons": {
    "save": "Save",
    "cancel": "Cancel"
  }
}
```

### Chinese (`zh-CN.json`)
```json
{
  "title": "您的扩展",
  "description": "扩展描述",
  "buttons": {
    "save": "保存",
    "cancel": "取消"
  }
}
```

Use translations in your Svelte components:
```svelte
<script>
  import { t } from '$lib/i18n';
</script>

<h1>{$t('extensions.your_extension_name.title')}</h1>
```

## 🛠️ Development Tools

### CLI Commands

From the project root directory:

```bash
# List all installed extensions
realms-cli extension list

# Install all extensions from source
realms-cli extension install-from-source

# Create a new realm with demo data for testing
realms-cli create --members 25 --organizations 3 --transactions 50
```
