# @realms/extension-ui

Shared Svelte 5 UI components for **sandboxed Realms extensions**. Host-provided Svelte components cannot cross an iframe boundary, so each extension bundles this package into its own frontend build.

The host never injects these components or styles. Extensions compile Tailwind locally and inherit host theming through CSS custom properties pushed via the bridge (`theme` in `@realms/extension-bridge` state).

## Install

```bash
npm install @realms/extension-ui
```

In a monorepo checkout, depend on the workspace package path or link it while developing.

## Usage

```svelte
<script lang="ts">
  import { PageHeader, Card, Button, EmptyState } from '@realms/extension-ui';
</script>

<PageHeader title="Members" subtitle="Manage realm membership.">
  {#snippet actions()}
    <Button onclick={() => refresh()}>Refresh</Button>
  {/snippet}
</PageHeader>

<Card title="Roster">
  {#snippet children()}
    <!-- content -->
  {/snippet}
</Card>

<EmptyState title="No members yet" message="Invite someone to get started.">
  {#snippet actions()}
    <Button>Invite member</Button>
  {/snippet}
</EmptyState>
```

## Tailwind setup (required)

This package ships Tailwind utility class names only. Your extension build must scan this package so those classes are emitted:

```js
// tailwind.config.js
export default {
  darkMode: 'selector',
  content: [
    './src/**/*.{html,js,svelte,ts}',
    './node_modules/@realms/extension-ui/dist/**/*.{html,js,svelte,ts}'
  ]
};
```

## Page spacing standard

Built-in Realms pages place breadcrumbs in the host shell with a fixed gap to the page title. Extensions previously added their own top padding (`p-4`, `pt-8`, `py-6`, etc.), which stacked with host padding and produced inconsistent breadcrumb-to-title spacing (roughly 56–72px vs 40px on built-in pages).

`PageHeader` owns the standard: **`pt-4` (16px) under the host breadcrumb**, no extra page-level top padding, and a consistent `text-2xl font-bold` title. Do not wrap `PageHeader` in additional top padding.

## Components

| Component | Purpose |
|-----------|---------|
| `PageHeader` | Title, optional subtitle, optional `actions` snippet (right-aligned) |
| `Card` | Bordered content container with optional `title` or `header` snippet |
| `Button` | Primary / secondary / danger actions (`tone`, `size`, `onclick`) |
| `EmptyState` | Centered placeholder with optional `message` and `actions` |

## Design tokens

Components use the host theme CSS custom properties where they exist, with light-mode fallbacks so they render sensibly before bridge state arrives. Dark mode follows the host convention: a `.dark` ancestor (Tailwind `darkMode: 'selector'`).

### Text

| Token | Fallback | Usage |
|-------|----------|--------|
| `--color-text-primary` | `#111827` | Headings, body text |
| `--color-text-secondary` | `#6b7280` | Subtitles, muted copy |
| `--color-text-inverse` | `#ffffff` | Text on filled buttons |

### Background and border

| Token | Fallback | Usage |
|-------|----------|--------|
| `--color-bg-primary` | `#ffffff` | Card surfaces |
| `--color-bg-secondary` | `#f9fafb` | (reserved for future use) |
| `--color-border-primary` | `#e5e7eb` | Card borders, dividers |

### Brand / actions

| Token | Fallback | Usage |
|-------|----------|--------|
| `--color-primary-600` | `#2563eb` | Primary actions (Button also uses Tailwind `blue-600` to match existing extensions) |
| `--color-error-600` | `#dc2626` | Danger actions |

These names match `/src/realm_frontend/src/lib/theme/theme.ts` (`updateCSSVariables`). The host sets them on `document.documentElement`; sandboxed extensions receive the same values when the bridge applies theme state to the iframe document.

## Build

```bash
npm run build   # emits dist/ with typed Svelte components
npm run check   # svelte-check
```

## Bundling note

Extensions must list `@realms/extension-ui` as a dependency and bundle it into `dist/index.html`. The Realms host does not provide or inject this package at runtime.
