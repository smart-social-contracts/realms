# Centralized Theme System

This document explains how to use the new centralized theme system in the Realms frontend application.

## Overview

The theme system provides a single source of truth for all design tokens including colors, typography, spacing, and other visual properties. Instead of hardcoding Tailwind classes throughout components, you can now use theme utilities that automatically adapt to theme changes.

## Files Structure

```
src/lib/theme/
├── theme.ts          # Main theme configuration
├── utilities.ts      # CSS class generators and utilities
├── init.ts          # Theme initialization script
└── README.md        # This documentation
```

## Quick Start

### 1. Using Theme Utilities in Components

Instead of hardcoded classes:
```svelte
<!-- ❌ Old way - hardcoded classes -->
<button class="bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded-lg">
  Click me
</button>
```

Use theme utilities:
```svelte
<!-- ✅ New way - theme utilities -->
<script>
  import { styles } from '$lib/theme/utilities';
</script>

<button class={styles.button.primary()}>
  Click me
</button>
```

### 2. Using CSS Custom Properties

You can also use CSS custom properties directly:
```svelte
<style>
  .my-component {
    background-color: var(--color-primary-600);
    color: var(--color-text-inverse);
    padding: var(--spacing-md);
    border-radius: var(--border-radius-lg);
    font-family: var(--font-family-sans);
  }
</style>
```

### 3. Accessing Theme Values in JavaScript

```svelte
<script>
  import { theme } from '$lib/theme/theme';
  
  // Access theme values programmatically
  $: primaryColor = theme.colors.primary[600];
  $: fontSize = theme.typography.fontSize.lg;
</script>
```

## Available Style Utilities

### Buttons
```javascript
import { styles } from '$lib/theme/utilities';

styles.button.primary()    // Primary button
styles.button.secondary()  // Secondary button
styles.button.success()    // Success button
styles.button.warning()    // Warning button
styles.button.error()      // Error button
```

### Typography
```javascript
styles.text.heading1()     // Large heading
styles.text.heading2()     // Medium heading
styles.text.heading3()     // Small heading
styles.text.body()         // Body text
styles.text.bodySecondary() // Secondary body text
styles.text.caption()      // Small caption text
styles.text.label()        // Form labels
```

### Cards
```javascript
styles.card.default()      // Standard card
styles.card.elevated()     // Card with more shadow
styles.card.flat()         // Flat card without shadow
```

### Inputs
```javascript
styles.input.default()     // Standard input
styles.input.error()       // Error state input
```

### Alerts
```javascript
styles.alert.success()     // Success alert
styles.alert.warning()     // Warning alert
styles.alert.error()       // Error alert
styles.alert.info()        // Info alert
```

### Sidebar
```javascript
styles.sidebar.container() // Sidebar container
styles.sidebar.item()      // Sidebar item
styles.sidebar.itemActive() // Active sidebar item
styles.sidebar.icon()      // Sidebar icon
styles.sidebar.categoryHeader() // Category header
```

### Tables
```javascript
styles.table.container()   // Table container
styles.table.header()      // Table header
styles.table.cell()        // Table cell
styles.table.cellSecondary() // Secondary table cell
```

## Customizing the Theme

### 1. Modifying the Default Theme

Edit `/src/lib/theme/theme.ts` to change the default theme:

```typescript
export const defaultTheme: ThemeConfig = {
  colors: {
    primary: {
      50: '#FFF5F2',   // Lightest
      100: '#FFF1EE',
      // ... modify these values
      900: '#A5371B'   // Darkest
    },
    // ... other color scales
  },
  typography: {
    fontFamily: {
      sans: ['Your Font', 'Inter', 'sans-serif'], // Change font family
    },
    fontSize: {
      base: '1.125rem', // Change base font size
      // ... other sizes
    }
  }
  // ... other theme properties
};
```

### 2. Creating Theme Variants

You can create different theme variants:

```typescript
// In your component or theme file
import { setTheme, type ThemeConfig } from '$lib/theme/theme';

const darkTheme: Partial<ThemeConfig> = {
  colors: {
    text: {
      primary: '#FFFFFF',
      secondary: '#D1D5DB',
      // ... other overrides
    },
    background: {
      primary: '#111827',
      secondary: '#1F2937',
      // ... other overrides
    }
  }
};

// Apply the theme
setTheme(darkTheme);
```

### 3. Runtime Theme Switching

```svelte
<script>
  import { switchToLightTheme, switchToDarkTheme, applyCustomTheme } from '$lib/theme/init';
  
  function handleThemeChange(themeName) {
    switch (themeName) {
      case 'light':
        switchToLightTheme();
        break;
      case 'dark':
        switchToDarkTheme();
        break;
      case 'custom':
        applyCustomTheme({
          colors: {
            primary: {
              600: '#8B5CF6', // Purple primary
              // ... other overrides
            }
          }
        });
        break;
    }
  }
</script>

<select on:change={(e) => handleThemeChange(e.target.value)}>
  <option value="light">Light Theme</option>
  <option value="dark">Dark Theme</option>
  <option value="custom">Custom Theme</option>
</select>
```

## Migration Guide

### Converting Existing Components

1. **Replace hardcoded button classes:**
   ```svelte
   <!-- Before -->
   <button class="bg-blue-600 text-white hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 font-medium rounded-lg px-5 py-2.5">
     Submit
   </button>
   
   <!-- After -->
   <script>
     import { styles } from '$lib/theme/utilities';
   </script>
   
   <button class={styles.button.primary()}>
     Submit
   </button>
   ```

2. **Replace hardcoded text classes:**
   ```svelte
   <!-- Before -->
   <h2 class="text-2xl font-bold text-gray-900 dark:text-white">
     Title
   </h2>
   
   <!-- After -->
   <h2 class={styles.text.heading2()}>
     Title
   </h2>
   ```

3. **Replace hardcoded color classes:**
   ```svelte
   <!-- Before -->
   <div class="bg-white border border-gray-200 rounded-lg shadow-md dark:bg-gray-800 dark:border-gray-700">
     Content
   </div>
   
   <!-- After -->
   <div class={styles.card.default()}>
     Content
   </div>
   ```

### Combining with Existing Classes

Use the `cn` utility to combine theme classes with other classes:

```svelte
<script>
  import { styles, cn } from '$lib/theme/utilities';
</script>

<button class={cn(styles.button.primary(), 'w-full mt-4')}>
  Full Width Button
</button>
```

## CSS Custom Properties Reference

All theme values are available as CSS custom properties:

### Colors
- `--color-primary-{50-900}`
- `--color-success-{50-900}`
- `--color-warning-{50-900}`
- `--color-error-{50-900}`
- `--color-gray-{50-900}`
- `--color-text-{primary|secondary|tertiary|inverse|disabled}`
- `--color-bg-{primary|secondary|tertiary|inverse|overlay}`
- `--color-border-{primary|secondary|focus|error}`

### Typography
- `--font-family-{sans|serif|mono}`
- `--font-size-{xs|sm|base|lg|xl|2xl|3xl|4xl|5xl}`
- `--font-weight-{light|normal|medium|semibold|bold|extrabold}`

### Spacing
- `--spacing-{xs|sm|md|lg|xl|2xl|3xl|4xl}`

### Border Radius
- `--border-radius-{none|sm|md|lg|xl|full}`

### Shadows
- `--shadow-{sm|md|lg|xl}`

### Transitions
- `--transition-{fast|normal|slow}`

## Best Practices

1. **Always use theme utilities for consistent styling**
2. **Avoid hardcoding colors, fonts, or spacing values**
3. **Use semantic color names (primary, success, error) instead of specific colors (blue, green, red)**
4. **Test your components with different themes to ensure they work correctly**
5. **Use the `cn` utility to combine classes cleanly**
6. **Prefer theme utilities over CSS custom properties in templates for better maintainability**

## Troubleshooting

### Theme not applying
- Make sure `initializeTheme()` is called in your main layout
- Check that CSS custom properties are defined in `app.pcss`
- Verify Tailwind config includes the theme extensions

### Classes not working
- Ensure you're importing utilities correctly: `import { styles } from '$lib/theme/utilities'`
- Check that Tailwind is processing your files correctly
- Verify the utility function returns a string

### TypeScript errors
- Make sure you're using the correct theme interfaces
- Check that your theme configuration matches the `ThemeConfig` interface

## Example Component

See `/src/lib/components/ThemeExample.svelte` for a complete example of how to use the theme system.
