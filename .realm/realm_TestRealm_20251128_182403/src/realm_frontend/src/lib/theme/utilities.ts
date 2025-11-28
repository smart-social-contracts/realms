/**
 * Theme Utility Functions and CSS Class Generators
 * 
 * This file provides utility functions to generate CSS classes based on the theme configuration.
 * Use these functions in Svelte components instead of hardcoded Tailwind classes.
 */

import { theme } from './theme';

// Button style generators
export const buttonStyles = {
  primary: () => `
    bg-[var(--color-primary-600)] 
    text-white 
    hover:bg-[var(--color-primary-700)] 
    focus:ring-4 
    focus:ring-[var(--color-primary-300)] 
    dark:bg-[var(--color-primary-600)] 
    dark:hover:bg-[var(--color-primary-700)] 
    dark:focus:ring-[var(--color-primary-800)]
    font-medium 
    rounded-[var(--border-radius-lg)] 
    px-[var(--spacing-lg)] 
    py-[var(--spacing-sm)] 
    transition-[var(--transition-fast)]
  `,
  
  secondary: () => `
    border 
    border-[var(--color-border-primary)] 
    text-[var(--color-text-secondary)] 
    bg-[var(--color-bg-primary)] 
    hover:bg-[var(--color-bg-secondary)] 
    focus:ring-4 
    focus:ring-[var(--color-gray-300)] 
    dark:border-[var(--color-gray-600)] 
    dark:text-[var(--color-gray-400)] 
    dark:bg-[var(--color-gray-800)] 
    dark:hover:bg-[var(--color-gray-700)] 
    dark:focus:ring-[var(--color-gray-700)]
    font-medium 
    rounded-[var(--border-radius-lg)] 
    px-[var(--spacing-lg)] 
    py-[var(--spacing-sm)] 
    transition-[var(--transition-fast)]
  `,
  
  success: () => `
    bg-[var(--color-success-600)] 
    text-white 
    hover:bg-[var(--color-success-700)] 
    focus:ring-4 
    focus:ring-[var(--color-success-300)]
    font-medium 
    rounded-[var(--border-radius-lg)] 
    px-[var(--spacing-lg)] 
    py-[var(--spacing-sm)] 
    transition-[var(--transition-fast)]
  `,
  
  warning: () => `
    bg-[var(--color-warning-600)] 
    text-white 
    hover:bg-[var(--color-warning-700)] 
    focus:ring-4 
    focus:ring-[var(--color-warning-300)]
    font-medium 
    rounded-[var(--border-radius-lg)] 
    px-[var(--spacing-lg)] 
    py-[var(--spacing-sm)] 
    transition-[var(--transition-fast)]
  `,
  
  error: () => `
    bg-[var(--color-error-600)] 
    text-white 
    hover:bg-[var(--color-error-700)] 
    focus:ring-4 
    focus:ring-[var(--color-error-300)]
    font-medium 
    rounded-[var(--border-radius-lg)] 
    px-[var(--spacing-lg)] 
    py-[var(--spacing-sm)] 
    transition-[var(--transition-fast)]
  `};

// Text style generators
export const textStyles = {
  heading1: () => `
    text-[var(--font-size-3xl)] 
    font-[var(--font-weight-bold)] 
    text-[var(--color-text-primary)] 
    dark:text-[var(--color-text-inverse)] 
    leading-[var(--line-height-tight)]
  `,
  
  heading2: () => `
    text-[var(--font-size-2xl)] 
    font-[var(--font-weight-bold)] 
    text-[var(--color-text-primary)] 
    dark:text-[var(--color-text-inverse)] 
    leading-[var(--line-height-tight)]
  `,
  
  heading3: () => `
    text-[var(--font-size-xl)] 
    font-[var(--font-weight-semibold)] 
    text-[var(--color-text-primary)] 
    dark:text-[var(--color-text-inverse)] 
    leading-[var(--line-height-normal)]
  `,
  
  body: () => `
    text-[var(--font-size-base)] 
    font-[var(--font-weight-normal)] 
    text-[var(--color-text-primary)] 
    dark:text-[var(--color-text-inverse)] 
    leading-[var(--line-height-normal)]
  `,
  
  bodySecondary: () => `
    text-[var(--font-size-base)] 
    font-[var(--font-weight-normal)] 
    text-[var(--color-text-secondary)] 
    dark:text-[var(--color-gray-400)] 
    leading-[var(--line-height-normal)]
  `,
  
  caption: () => `
    text-[var(--font-size-sm)] 
    font-[var(--font-weight-normal)] 
    text-[var(--color-text-tertiary)] 
    dark:text-[var(--color-gray-400)] 
    leading-[var(--line-height-normal)]
  `,
  
  label: () => `
    text-[var(--font-size-sm)] 
    font-[var(--font-weight-medium)] 
    text-[var(--color-text-primary)] 
    dark:text-[var(--color-text-inverse)] 
    leading-[var(--line-height-normal)]
  `,
  
  success: () => `
    text-[var(--color-success-700)] 
    dark:text-[var(--color-success-300)]
  `,
  
  warning: () => `
    text-[var(--color-warning-700)] 
    dark:text-[var(--color-warning-300)]
  `,
  
  error: () => `
    text-[var(--color-error-700)] 
    dark:text-[var(--color-error-300)]
  `
};

// Card style generators
export const cardStyles = {
  default: () => `
    bg-[var(--color-bg-primary)] 
    border 
    border-[var(--color-border-primary)] 
    rounded-[var(--border-radius-lg)] 
    shadow-[var(--shadow-md)] 
    dark:bg-[var(--color-gray-800)] 
    dark:border-[var(--color-gray-700)]
  `,
  
  elevated: () => `
    bg-[var(--color-bg-primary)] 
    border 
    border-[var(--color-border-primary)] 
    rounded-[var(--border-radius-lg)] 
    shadow-[var(--shadow-lg)] 
    dark:bg-[var(--color-gray-800)] 
    dark:border-[var(--color-gray-700)]
  `,
  
  flat: () => `
    bg-[var(--color-bg-secondary)] 
    border 
    border-[var(--color-border-primary)] 
    rounded-[var(--border-radius-lg)] 
    dark:bg-[var(--color-gray-800)] 
    dark:border-[var(--color-gray-700)]
  `
};

// Input style generators
export const inputStyles = {
  default: () => `
    bg-[var(--color-bg-primary)] 
    border 
    border-[var(--color-border-primary)] 
    text-[var(--color-text-primary)] 
    rounded-[var(--border-radius-lg)] 
    focus:ring-[var(--color-primary-500)] 
    focus:border-[var(--color-primary-500)] 
    dark:bg-[var(--color-gray-700)] 
    dark:border-[var(--color-gray-600)] 
    dark:placeholder-[var(--color-gray-400)] 
    dark:text-[var(--color-text-inverse)] 
    dark:focus:ring-[var(--color-primary-500)] 
    dark:focus:border-[var(--color-primary-500)]
    px-[var(--spacing-md)] 
    py-[var(--spacing-sm)] 
    transition-[var(--transition-fast)]
  `,
  
  error: () => `
    bg-[var(--color-bg-primary)] 
    border 
    border-[var(--color-error-500)] 
    text-[var(--color-text-primary)] 
    rounded-[var(--border-radius-lg)] 
    focus:ring-[var(--color-error-500)] 
    focus:border-[var(--color-error-500)] 
    dark:bg-[var(--color-gray-700)] 
    dark:border-[var(--color-error-500)] 
    dark:text-[var(--color-text-inverse)]
    px-[var(--spacing-md)] 
    py-[var(--spacing-sm)] 
    transition-[var(--transition-fast)]
  `
};

// Sidebar style generators
export const sidebarStyles = {
  container: () => `
    bg-[var(--color-bg-primary)] 
    border-r 
    border-[var(--color-border-primary)] 
    dark:bg-[var(--color-gray-800)] 
    dark:border-[var(--color-gray-700)]
  `,
  
  item: () => `
    flex 
    items-center 
    p-[var(--spacing-sm)] 
    text-[var(--font-size-base)] 
    text-[var(--color-text-primary)] 
    transition-[var(--transition-fast)] 
    rounded-[var(--border-radius-lg)] 
    hover:bg-[var(--color-bg-secondary)] 
    group 
    dark:text-[var(--color-gray-200)] 
    dark:hover:bg-[var(--color-gray-700)]
  `,
  
  itemActive: () => `
    bg-[var(--color-bg-secondary)] 
    dark:bg-[var(--color-gray-700)]
  `,
  
  icon: () => `
    flex-shrink-0 
    w-6 
    h-6 
    text-[var(--color-text-secondary)] 
    transition-[var(--transition-fast)] 
    group-hover:text-[var(--color-text-primary)] 
    dark:text-[var(--color-gray-400)] 
    dark:group-hover:text-[var(--color-text-inverse)]
  `,
  
  categoryHeader: () => `
    text-[var(--font-size-xs)] 
    font-[var(--font-weight-semibold)] 
    text-[var(--color-text-secondary)] 
    uppercase 
    tracking-wider 
    dark:text-[var(--color-gray-400)]
  `
};

// Navbar style generators
export const navbarStyles = {
  container: () => `
    bg-[var(--color-bg-primary)] 
    border-b 
    border-[var(--color-border-primary)] 
    dark:bg-[var(--color-gray-800)] 
    dark:border-[var(--color-gray-700)]
  `,
  
  brand: () => `
    text-[var(--font-size-xl)] 
    font-[var(--font-weight-semibold)] 
    text-[var(--color-text-primary)] 
    dark:text-[var(--color-text-inverse)]
  `
};

// Table style generators
export const tableStyles = {
  container: () => `
    bg-[var(--color-bg-primary)] 
    border 
    border-[var(--color-border-primary)] 
    rounded-[var(--border-radius-lg)] 
    shadow-[var(--shadow-sm)] 
    dark:bg-[var(--color-gray-800)] 
    dark:border-[var(--color-gray-700)]
  `,
  
  header: () => `
    bg-[var(--color-bg-secondary)] 
    text-[var(--color-text-primary)] 
    font-[var(--font-weight-medium)] 
    dark:bg-[var(--color-gray-700)] 
    dark:text-[var(--color-text-inverse)]
  `,
  
  cell: () => `
    text-[var(--color-text-primary)] 
    dark:text-[var(--color-text-inverse)]
  `,
  
  cellSecondary: () => `
    text-[var(--color-text-secondary)] 
    dark:text-[var(--color-gray-400)]
  `
};

// Alert/notification style generators
export const alertStyles = {
  success: () => `
    bg-[var(--color-success-50)] 
    border 
    border-[var(--color-success-200)] 
    text-[var(--color-success-800)] 
    rounded-[var(--border-radius-lg)] 
    dark:bg-[var(--color-success-900)] 
    dark:border-[var(--color-success-700)] 
    dark:text-[var(--color-success-200)]
  `,
  
  warning: () => `
    bg-[var(--color-warning-50)] 
    border 
    border-[var(--color-warning-200)] 
    text-[var(--color-warning-800)] 
    rounded-[var(--border-radius-lg)] 
    dark:bg-[var(--color-warning-900)] 
    dark:border-[var(--color-warning-700)] 
    dark:text-[var(--color-warning-200)]
  `,
  
  error: () => `
    bg-[var(--color-error-50)] 
    border 
    border-[var(--color-error-200)] 
    text-[var(--color-error-800)] 
    rounded-[var(--border-radius-lg)] 
    dark:bg-[var(--color-error-900)] 
    dark:border-[var(--color-error-700)] 
    dark:text-[var(--color-error-200)]
  `,
  
  info: () => `
    bg-[var(--color-primary-50)] 
    border 
    border-[var(--color-primary-200)] 
    text-[var(--color-primary-800)] 
    rounded-[var(--border-radius-lg)] 
    dark:bg-[var(--color-primary-900)] 
    dark:border-[var(--color-primary-700)] 
    dark:text-[var(--color-primary-200)]
  `
};

// Utility function to combine classes
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ').replace(/\s+/g, ' ').trim();
}

// Export all style generators as a single object for easy importing
export const styles = {
  button: buttonStyles,
  text: textStyles,
  card: cardStyles,
  input: inputStyles,
  sidebar: sidebarStyles,
  navbar: navbarStyles,
  table: tableStyles,
  alert: alertStyles
};
