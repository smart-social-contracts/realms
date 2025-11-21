# Frontend Architecture

Realms frontend built with SvelteKit, TypeScript, and TailwindCSS.

---

## Technology Stack

- **SvelteKit** - Web framework
- **TypeScript** - Type safety
- **TailwindCSS** - Styling
- **Flowbite Svelte** - UI components
- **svelte-i18n** - Internationalization
- **Internet Identity** - Authentication

---

## Project Structure

```
src/realm_frontend/
├── src/
│   ├── routes/                      # SvelteKit routes
│   │   ├── (sidebar)/               # Authenticated routes
│   │   │   ├── extensions/          # Extension pages
│   │   │   ├── +layout.svelte       # Sidebar layout
│   │   │   └── +page.svelte         # Home page
│   │   └── +layout.svelte           # Root layout
│   │
│   ├── lib/
│   │   ├── api/                     # API clients
│   │   │   ├── backend.ts           # Backend calls
│   │   │   ├── canisters.js         # Canister setup
│   │   │   └── extensions.ts        # Extension calls
│   │   │
│   │   ├── components/              # Shared components
│   │   │   ├── AuthButton.svelte
│   │   │   ├── EntityTable.svelte
│   │   │   └── LoadingSpinner.svelte
│   │   │
│   │   ├── stores/                  # State management
│   │   │   ├── auth.js              # Authentication
│   │   │   └── profiles.ts          # User profiles
│   │   │
│   │   ├── i18n/                    # Internationalization
│   │   │   ├── index.ts
│   │   │   └── locales/             # Translations
│   │   │
│   │   ├── theme/                   # Theme system
│   │   │   ├── theme.ts
│   │   │   └── utilities.ts
│   │   │
│   │   └── extensions/              # Extension components (installed)
│   │
│   ├── app.pcss                     # Global styles
│   └── app.html                     # HTML template
│
├── static/                          # Static assets
│   ├── images/
│   └── favicon.png
│
├── svelte.config.js                 # SvelteKit config
├── tailwind.config.js               # TailwindCSS config
└── package.json
```

---

## Routing

### Route Structure

```
/                          # Public home (welcome extension)
├── (sidebar)              # Authenticated layout with sidebar
│   ├── extensions/
│   │   ├── admin/         # Admin dashboard
│   │   ├── vault/         # Vault manager
│   │   ├── citizen/       # Citizen dashboard
│   │   └── [id]/          # Dynamic extension routes
│   └── settings           # User settings
```

### Route Example

```svelte
<!-- src/routes/(sidebar)/extensions/admin/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { callBackend } from '$lib/api/backend';
  
  let users = [];
  
  onMount(async () => {
    const response = await callBackend('get_objects_paginated', [
      'User', 0, 10, 'desc'
    ]);
    users = response.data.objectsListPaginated.objects;
  });
</script>

<div class="p-6">
  <h1>Admin Dashboard</h1>
  {#each users as user}
    <div>{user.id}</div>
  {/each}
</div>
```

---

## API Integration

### Backend Calls

```typescript
// lib/api/backend.ts
import { backendCanister } from './canisters';

export async function callBackend(method: string, args: any[]) {
  try {
    const response = await backendCanister[method](...args);
    return response;
  } catch (error) {
    console.error(`Backend call failed: ${method}`, error);
    throw error;
  }
}
```

**Usage:**
```typescript
// Get paginated entities
const response = await callBackend('get_objects_paginated', [
  'User', 0, 10, 'desc'
]);

// Get user status
const status = await callBackend('get_my_user_status', []);
```

---

### Extension Calls

```typescript
// lib/api/extensions.ts
export async function callExtension(
  extensionName: string,
  functionName: string,
  args: any
) {
  const response = await callBackend('extension_sync_call', [{
    extension_name: extensionName,
    function_name: functionName,
    args: JSON.stringify(args)
  }]);
  
  return JSON.parse(response.data.extensionCall.response);
}
```

**Usage:**
```typescript
// Call vault extension
const balance = await callExtension('vault', 'get_balance', {
  user_id: 'alice_2024'
});
```

---

## State Management

### Authentication Store

```typescript
// lib/stores/auth.js
import { writable } from 'svelte/store';
import { AuthClient } from '@dfinity/auth-client';

export const isAuthenticated = writable(false);
export const principal = writable(null);

export async function login() {
  const authClient = await AuthClient.create();
  await authClient.login({
    identityProvider: IDENTITY_PROVIDER_URL,
    onSuccess: () => {
      isAuthenticated.set(true);
      principal.set(authClient.getIdentity().getPrincipal());
    }
  });
}

export async function logout() {
  const authClient = await AuthClient.create();
  await authClient.logout();
  isAuthenticated.set(false);
  principal.set(null);
}
```

**Usage:**
```svelte
<script>
  import { isAuthenticated } from '$lib/stores/auth';
</script>

{#if $isAuthenticated}
  <p>Welcome!</p>
{:else}
  <button on:click={login}>Login</button>
{/if}
```

---

### User Profiles Store

```typescript
// lib/stores/profiles.ts
import { writable } from 'svelte/store';

export const userProfiles = writable<string[]>([]);

export function hasProfile(profile: string): boolean {
  let profiles: string[] = [];
  userProfiles.subscribe(p => profiles = p)();
  return profiles.includes(profile);
}
```

---

## Internationalization

### Setup

```typescript
// lib/i18n/index.ts
import { init, register } from 'svelte-i18n';

register('en', () => import('./locales/en.json'));
register('zh-CN', () => import('./locales/zh-CN.json'));

init({
  fallbackLocale: 'en',
  initialLocale: 'en'
});
```

### Translations

```json
// lib/i18n/locales/en.json
{
  "welcome": "Welcome",
  "login": "Login",
  "logout": "Logout"
}
```

```json
// lib/i18n/locales/zh-CN.json
{
  "welcome": "欢迎",
  "login": "登录",
  "logout": "登出"
}
```

### Usage

```svelte
<script>
  import { _ } from 'svelte-i18n';
</script>

<h1>{$_('welcome')}</h1>
<button>{$_('login')}</button>
```

---

## Extension System

### Extension Component

```svelte
<!-- lib/extensions/my_extension/MyExtension.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { callExtension } from '$lib/api/extensions';
  
  let data = null;
  
  onMount(async () => {
    data = await callExtension('my_extension', 'get_data', {});
  });
</script>

<div class="p-6">
  <h1>My Extension</h1>
  {#if data}
    <pre>{JSON.stringify(data, null, 2)}</pre>
  {/if}
</div>
```

### Extension Route

```svelte
<!-- routes/(sidebar)/extensions/my_extension/+page.svelte -->
<script>
  import MyExtension from '$lib/extensions/my_extension/MyExtension.svelte';
</script>

<MyExtension />
```

### Extension i18n

```json
// lib/i18n/locales/extensions/my_extension/en.json
{
  "title": "My Extension",
  "description": "Extension description"
}
```

**Usage:**
```svelte
<script>
  import { _ } from 'svelte-i18n';
</script>

<h1>{$_('extensions.my_extension.title')}</h1>
```

---

## Theme System

### Theme Configuration

```typescript
// lib/theme/theme.ts
export const theme = {
  colors: {
    primary: {
      50: '#fafafa',
      500: '#737373',
      900: '#171717'
    },
    // ... more colors
  },
  spacing: {
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem'
  }
};
```

### Theme Utilities

```typescript
// lib/theme/utilities.ts
export const styles = {
  button: {
    primary: () => 'bg-gray-900 text-white hover:bg-gray-800',
    secondary: () => 'bg-gray-100 text-gray-900 hover:bg-gray-200'
  },
  card: () => 'bg-white rounded-lg shadow p-6'
};
```

**Usage:**
```svelte
<script>
  import { styles } from '$lib/theme/utilities';
</script>

<button class={styles.button.primary()}>Click</button>
<div class={styles.card()}>Content</div>
```

---

## Common Components

### EntityTable

```svelte
<!-- lib/components/EntityTable.svelte -->
<script lang="ts">
  export let entities = [];
  export let columns = [];
  export let onRowClick = (entity) => {};
</script>

<table class="w-full">
  <thead>
    <tr>
      {#each columns as col}
        <th>{col.label}</th>
      {/each}
    </tr>
  </thead>
  <tbody>
    {#each entities as entity}
      <tr on:click={() => onRowClick(entity)}>
        {#each columns as col}
          <td>{entity[col.field]}</td>
        {/each}
      </tr>
    {/each}
  </tbody>
</table>
```

---

### LoadingSpinner

```svelte
<!-- lib/components/LoadingSpinner.svelte -->
<script>
  export let size = 'md';
</script>

<div class="flex justify-center">
  <div class="animate-spin rounded-full border-4 border-gray-300 border-t-gray-900 
              {size === 'sm' ? 'h-8 w-8' : 'h-16 w-16'}">
  </div>
</div>
```

---

## Authentication Flow

### 1. User Clicks Login
```svelte
<AuthButton />
```

### 2. Internet Identity Auth
```typescript
await authClient.login({
  identityProvider: II_URL,
  onSuccess: async () => {
    // Get principal
    const identity = authClient.getIdentity();
    const principal = identity.getPrincipal();
    
    // Check if registered
    const status = await callBackend('get_my_user_status', []);
    
    if (!status.success) {
      // Register new user
      await callBackend('join_realm', ['member']);
    }
    
    // Update stores
    isAuthenticated.set(true);
    userProfiles.set(status.data.userGet.profiles);
  }
});
```

### 3. Authenticated Routes
```svelte
<!-- routes/(sidebar)/+layout.svelte -->
<script>
  import { isAuthenticated } from '$lib/stores/auth';
  import { goto } from '$app/navigation';
  
  $: if (!$isAuthenticated) {
    goto('/');
  }
</script>

<Sidebar />
<slot />
```

---

## Development

### Run Dev Server

```bash
cd src/realm_frontend
npm install
npm run dev
```

Access at `http://localhost:5173`

### Build

```bash
npm run build
```

### Preview

```bash
npm run preview
```

---

## Extension Development

### 1. Create Component

```svelte
<!-- extensions/my_ext/frontend/lib/extensions/my_ext/MyExt.svelte -->
<script lang="ts">
  import { callExtension } from '$lib/api/extensions';
  
  let data = null;
  
  async function loadData() {
    data = await callExtension('my_ext', 'get_data', {});
  }
</script>

<button on:click={loadData}>Load</button>
{#if data}
  <pre>{JSON.stringify(data)}</pre>
{/if}
```

### 2. Add Translations

```json
// extensions/my_ext/frontend/i18n/en.json
{
  "title": "My Extension",
  "load_button": "Load Data"
}
```

### 3. Install Extension

```bash
realms extension install-from-source
```

Routes automatically created at `/extensions/my_ext`

---

## Best Practices

### Component Structure
- Keep components small and focused
- Use TypeScript for type safety
- Extract reusable logic to composables

### State Management
- Use stores for global state
- Component state for local UI
- Reactive statements for derived values

### Performance
- Lazy load extensions
- Paginate large lists
- Cache API responses
- Use `onMount` for data fetching

### Accessibility
- Semantic HTML
- ARIA labels
- Keyboard navigation
- Color contrast

### Internationalization
- Extract all user-facing strings
- Use namespaces for organization
- Test with multiple locales

---

## See Also

- [Extension Guide](../extensions/README.md) - Extension development
- [API Reference](./API_REFERENCE.md) - Backend integration
- [Theme System](../src/lib/theme/README.md) - Styling guide
- [i18n Guide](../src/lib/i18n/README.md) - Translations
