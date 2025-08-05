# Realms Extension Development Guide

Welcome to the Realms extension development ecosystem! This guide will help you create powerful extensions for the Smart Social Contracts platform.

## 🚀 Quick Start

1. **Clone this repository** or create your own extension repository
2. **Create your extension** following the structure below
3. **Test locally** using the provided CLI tools
4. **Package and distribute** your extension

## 📁 Extension Structure

Each extension follows a standardized directory structure:

```
extensions/{your_extension_id}/
├── manifest.json              # Extension metadata
├── backend/                   # Python backend code
│   ├── __init__.py
│   ├── entry.py              # Main backend entry point
│   └── manifest.json         # Backend-specific manifest
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
  "categories": ["public_services", "finances", "other"],
  "icon": "table",
  "url": "https://github.com/yourname/your-extension"
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
- `icon`: Icon name (from Flowbite icons)
- `url`: Repository or documentation URL

**Available Categories:**
- `public_services`: Government and public sector functionality
- `finances`: Financial and economic tools
- `other`: General purpose extensions

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

### Backend Manifest (`backend/manifest.json`)

```json
{
  "name": "your_extension_name",
  "version": "1.0.0",
  "description": "Backend component description",
  "author": "Your Name",
  "permissions": ["read", "write"]
}
```

## 🎨 Frontend Development

### TypeScript Entry Point (`frontend/lib/extensions/{extension_id}/index.ts`)

```typescript
import { default as YourMainComponent } from './YourMainComponent.svelte';
import { YourIcon } from 'flowbite-svelte-icons';

export default YourMainComponent;

export const metadata = {
  name: "Your Extension Display Name",
  description: "User-facing description",
  icon: YourIcon,
  author: "Your Name",
  permissions: ["read"],
  subComponents: {
    // Export additional components if needed
  }
};
```

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
python scripts/realm-extension-cli.py list

# Package your extension
python scripts/realm-extension-cli.py package --extension-id your_extension_name

# Install an extension package
python scripts/realm-extension-cli.py install --package-path your_extension.zip

# Install all extensions from source
./scripts/install_extensions.sh

# Uninstall an extension
python scripts/realm-extension-cli.py uninstall --extension-id your_extension_name
```

### Local Development Workflow

1. **Create your extension** in `extensions/your_extension_name/`
2. **Install locally** using `./scripts/install_extensions.sh`
3. **Test in browser** at `http://localhost:8080`
4. **Iterate** by editing source files and re-running install script

## 📦 Distribution

### Packaging

```bash
# Package your extension for distribution
python scripts/realm-extension-cli.py package --extension-id your_extension_name --output-dir ./dist
```

This creates a `your_extension_name.zip` file containing:
- `manifest.json`
- `backend/` folder with Python files
- `frontend/` folder with TypeScript/Svelte files

### Installation by End Users

Users can install your extension:

```bash
# Download your extension package
python scripts/realm-extension-cli.py install --package-path your_extension_name.zip
```

## 🎯 Best Practices

### Code Organization
- Keep backend logic in `backend/entry.py`
- Create focused, reusable Svelte components
- Use TypeScript for better development experience
- Follow the existing code style and patterns

### Security
- Validate all input parameters in backend functions
- Use appropriate permission levels
- Sanitize user input before database operations
- Follow principle of least privilege

### Performance
- Minimize backend function complexity
- Use efficient database queries
- Implement proper error handling
- Consider caching for expensive operations

### User Experience
- Provide clear loading states
- Handle errors gracefully
- Use consistent UI patterns
- Support internationalization

## 🔧 API Reference

### Backend API

Extensions can access the platform's core functionality:

```python
# Example backend function with platform integration
def get_user_data(args):
    from core.database import get_user_by_id
    
    user_id = args.get('user_id')
    if not user_id:
        return {"error": "user_id required"}
    
    user = get_user_by_id(user_id)
    return {"user": user.to_dict()} if user else {"error": "User not found"}
```

### Frontend API

Call backend functions from your Svelte components:

```typescript
import { callExtension } from '$lib/api/extensions';

// Call your backend function
const result = await callExtension('extension_name', 'function_name', {
  param1: 'value1',
  param2: 'value2'
});
```

## 📚 Examples

Check out the existing extensions in this directory for examples:
- `citizen_dashboard`: User dashboard with multiple components
- `vault_manager`: Financial management interface
- `land_registry`: Geographic data visualization
- `llm_chat`: AI chat integration
- `notifications`: Real-time notification system

## 🤝 Contributing

1. **Fork** the repository
2. **Create** your extension following this guide
3. **Test** thoroughly in local environment
4. **Submit** a pull request with your extension
5. **Document** any special requirements or dependencies

## 📞 Support

- **Documentation**: Check existing extensions for examples
- **Issues**: Report bugs or request features via GitHub issues
- **Community**: Join our developer community discussions

## 📄 License

Extensions should be compatible with the main project license. Please include appropriate license information in your extension repository.

---

Happy coding! 🚀 Build amazing extensions for the Realms platform!
