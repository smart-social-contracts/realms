# Realms Frontend Design System

## Overview
This document outlines the design system guidelines for the Realms frontend application to ensure consistency across all components and pages.

## Colors

### Primary Palette
- **Primary 50**: `#FFF5F2` - Lightest accent
- **Primary 500**: `#FE795D` - Main brand color
- **Primary 600**: `#EF562F` - Hover states
- **Primary 700**: `#EB4F27` - Active states

### Semantic Colors
- **Success**: `text-success-600`, `bg-success-50`
- **Warning**: `text-warning-600`, `bg-warning-50`
- **Danger**: `text-danger-600`, `bg-danger-50`

## Components

### Buttons

#### Standard Usage
Always use the `StandardButton` component or Flowbite `Button` with proper color props:

```svelte
<!-- ✅ Correct -->
<StandardButton variant="primary">Primary Action</StandardButton>
<StandardButton variant="secondary">Secondary Action</StandardButton>
<StandardButton variant="alternative">Alternative Action</StandardButton>

<!-- ✅ Also correct -->
<Button color="primary">Primary Action</Button>
<Button color="alternative">Alternative Action</Button>

<!-- ❌ Avoid -->
<Button class="bg-blue-600 text-white hover:bg-blue-700...">Hardcoded Styles</Button>
```

#### Button Variants
- **Primary**: Main actions (save, submit, create)
- **Secondary**: Important but not primary actions
- **Alternative**: Cancel, back, neutral actions
- **Success**: Confirm, complete actions
- **Warning**: Caution actions
- **Danger**: Delete, destructive actions

### Tables

#### Standard Usage
Always use Flowbite Table components for consistency:

```svelte
<!-- ✅ Correct -->
<Table hoverable={true} striped={true}>
  <TableHead>
    <TableHeadCell>Header</TableHeadCell>
  </TableHead>
  <TableBody>
    <TableBodyRow>
      <TableBodyCell>Data</TableBodyCell>
    </TableBodyRow>
  </TableBody>
</Table>

<!-- ❌ Avoid -->
<table class="basic-table">
  <thead>
    <tr><th>Header</th></tr>
  </thead>
</table>
```

## Spacing

### Standard Spacing Scale
- **xs**: `0.25rem` (4px)
- **sm**: `0.5rem` (8px)
- **md**: `1rem` (16px)
- **lg**: `1.5rem` (24px)
- **xl**: `2rem` (32px)

### Component Spacing
- **Card padding**: `p-6` (24px)
- **Button padding**: Use size props (`sm`, `md`, `lg`)
- **Section margins**: `mb-6` or `mb-8`

## Typography

### Headings
```svelte
<Heading tag="h1" class="mb-4">Page Title</Heading>
<Heading tag="h2" class="mb-3">Section Title</Heading>
<Heading tag="h3" class="mb-2">Subsection Title</Heading>
```

### Text
```svelte
<P class="text-gray-600 dark:text-gray-400">Body text</P>
<P class="text-sm text-gray-500 dark:text-gray-400">Small text</P>
```

## Dark Mode

### Guidelines
- Always include dark mode variants: `dark:text-white`, `dark:bg-gray-800`
- Use semantic color classes that work in both modes
- Test components in both light and dark themes

## Accessibility

### Requirements
- Include `aria-label` for icon-only buttons
- Use semantic HTML elements
- Maintain proper color contrast ratios
- Support keyboard navigation

### Examples
```svelte
<Button aria-label="Close dialog" color="alternative">
  <CloseOutline class="w-4 h-4" />
</Button>
```

## Migration Guide

### From Hardcoded Classes
Replace hardcoded Tailwind classes with Flowbite components:

```svelte
<!-- Before -->
<button class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
  Click me
</button>

<!-- After -->
<Button color="primary">Click me</Button>
```

### From Basic HTML Tables
Replace basic HTML tables with Flowbite Table components (see Tables section above).

## Best Practices

1. **Always use design system components** instead of custom CSS
2. **Consistent naming**: Use semantic color names (primary, success, danger)
3. **Responsive design**: Ensure components work on all screen sizes
4. **Dark mode support**: Always include dark mode variants
5. **Accessibility first**: Include proper ARIA labels and semantic HTML
6. **Performance**: Use Flowbite components for optimal bundle size
