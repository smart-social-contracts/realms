/**
 * Centralized Theme Configuration for Realms Frontend
 * 
 * This file contains all theme variables including colors, fonts, spacing, and other design tokens.
 * Modify values here to change the entire application's appearance.
 */

export interface ThemeConfig {
  colors: {
    // Primary brand colors
    primary: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
    
    // Semantic colors
    success: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
    
    warning: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
    
    error: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
    
    // Neutral colors
    gray: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
    
    // Text colors
    text: {
      primary: string;
      secondary: string;
      tertiary: string;
      inverse: string;
      disabled: string;
    };
    
    // Background colors
    background: {
      primary: string;
      secondary: string;
      tertiary: string;
      inverse: string;
      overlay: string;
    };
    
    // Border colors
    border: {
      primary: string;
      secondary: string;
      focus: string;
      error: string;
    };
  };
  
  typography: {
    fontFamily: {
      sans: string[];
      serif: string[];
      mono: string[];
    };
    
    fontSize: {
      xs: string;
      sm: string;
      base: string;
      lg: string;
      xl: string;
      '2xl': string;
      '3xl': string;
      '4xl': string;
      '5xl': string;
    };
    
    fontWeight: {
      light: number;
      normal: number;
      medium: number;
      semibold: number;
      bold: number;
      extrabold: number;
    };
    
    lineHeight: {
      tight: number;
      normal: number;
      relaxed: number;
    };
  };
  
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    '2xl': string;
    '3xl': string;
    '4xl': string;
  };
  
  borderRadius: {
    none: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    full: string;
  };
  
  shadows: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  
  transitions: {
    fast: string;
    normal: string;
    slow: string;
  };
}

// Default theme configuration
export const defaultTheme: ThemeConfig = {
  colors: {
    primary: {
      50: '#FAFAFA',
      100: '#F5F5F5',
      200: '#E5E5E5',
      300: '#D4D4D4',
      400: '#A3A3A3',
      500: '#737373',
      600: '#525252',
      700: '#404040',
      800: '#262626',
      900: '#171717'
    },
    
    success: {
      50: '#FAFAFA',
      100: '#F5F5F5',
      200: '#E5E5E5',
      300: '#D4D4D4',
      400: '#A3A3A3',
      500: '#737373',
      600: '#525252',
      700: '#404040',
      800: '#262626',
      900: '#171717'
    },
    
    warning: {
      50: '#FAFAFA',
      100: '#F5F5F5',
      200: '#E5E5E5',
      300: '#D4D4D4',
      400: '#A3A3A3',
      500: '#737373',
      600: '#525252',
      700: '#404040',
      800: '#262626',
      900: '#171717'
    },
    
    error: {
      50: '#FAFAFA',
      100: '#F5F5F5',
      200: '#E5E5E5',
      300: '#D4D4D4',
      400: '#A3A3A3',
      500: '#737373',
      600: '#525252',
      700: '#404040',
      800: '#262626',
      900: '#171717'
    },
    
    gray: {
      50: '#FAFAFA',
      100: '#F5F5F5',
      200: '#E5E5E5',
      300: '#D4D4D4',
      400: '#A3A3A3',
      500: '#737373',
      600: '#525252',
      700: '#404040',
      800: '#262626',
      900: '#171717'
    },
    
    text: {
      primary: '#171717',
      secondary: '#525252',
      tertiary: '#737373',
      inverse: '#FFFFFF',
      disabled: '#D4D4D4'
    },
    
    background: {
      primary: '#FFFFFF',
      secondary: '#FAFAFA',
      tertiary: '#F5F5F5',
      inverse: '#171717',
      overlay: 'rgba(23, 23, 23, 0.5)'
    },
    
    border: {
      primary: '#E5E5E5',
      secondary: '#D4D4D4',
      focus: '#525252',
      error: '#737373'
    }
  },
  
  typography: {
    fontFamily: {
      sans: ['Helvetica Neue', 'Helvetica', 'Arial', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      serif: ['ui-serif', 'Georgia', 'Cambria', 'Times New Roman', 'Times', 'serif'],
      mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace']
    },
    
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
      '5xl': '3rem'
    },
    
    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
      extrabold: 800
    },
    
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75
    }
  },
  
  spacing: {
    xs: '0.5rem',
    sm: '0.75rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
    '3xl': '4rem',
    '4xl': '6rem'
  },
  
  borderRadius: {
    none: '0',
    sm: '0.125rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    full: '9999px'
  },
  
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.08)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.12), 0 4px 6px -2px rgba(0, 0, 0, 0.08)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.15), 0 10px 10px -5px rgba(0, 0, 0, 0.08)'
  },
  
  transitions: {
    fast: '150ms ease-in-out',
    normal: '300ms ease-in-out',
    slow: '500ms ease-in-out'
  }
};

// Current active theme (can be switched dynamically)
export let currentTheme: ThemeConfig = defaultTheme;

// Function to update the theme
export function setTheme(newTheme: Partial<ThemeConfig>): void {
  currentTheme = { ...defaultTheme, ...newTheme };
  updateCSSVariables();
}

// Function to update CSS custom properties
function updateCSSVariables(): void {
  if (typeof document === 'undefined') return;
  
  const root = document.documentElement;
  
  // Update color variables
  Object.entries(currentTheme.colors.primary).forEach(([key, value]) => {
    root.style.setProperty(`--color-primary-${key}`, value);
  });
  
  Object.entries(currentTheme.colors.success).forEach(([key, value]) => {
    root.style.setProperty(`--color-success-${key}`, value);
  });
  
  Object.entries(currentTheme.colors.warning).forEach(([key, value]) => {
    root.style.setProperty(`--color-warning-${key}`, value);
  });
  
  Object.entries(currentTheme.colors.error).forEach(([key, value]) => {
    root.style.setProperty(`--color-error-${key}`, value);
  });
  
  Object.entries(currentTheme.colors.gray).forEach(([key, value]) => {
    root.style.setProperty(`--color-gray-${key}`, value);
  });
  
  Object.entries(currentTheme.colors.text).forEach(([key, value]) => {
    root.style.setProperty(`--color-text-${key}`, value);
  });
  
  Object.entries(currentTheme.colors.background).forEach(([key, value]) => {
    root.style.setProperty(`--color-bg-${key}`, value);
  });
  
  Object.entries(currentTheme.colors.border).forEach(([key, value]) => {
    root.style.setProperty(`--color-border-${key}`, value);
  });
  
  // Update typography variables
  root.style.setProperty('--font-family-sans', currentTheme.typography.fontFamily.sans.join(', '));
  root.style.setProperty('--font-family-serif', currentTheme.typography.fontFamily.serif.join(', '));
  root.style.setProperty('--font-family-mono', currentTheme.typography.fontFamily.mono.join(', '));
  
  Object.entries(currentTheme.typography.fontSize).forEach(([key, value]) => {
    root.style.setProperty(`--font-size-${key}`, value);
  });
  
  Object.entries(currentTheme.typography.fontWeight).forEach(([key, value]) => {
    root.style.setProperty(`--font-weight-${key}`, value.toString());
  });
  
  // Update spacing variables
  Object.entries(currentTheme.spacing).forEach(([key, value]) => {
    root.style.setProperty(`--spacing-${key}`, value);
  });
  
  // Update border radius variables
  Object.entries(currentTheme.borderRadius).forEach(([key, value]) => {
    root.style.setProperty(`--border-radius-${key}`, value);
  });
  
  // Update shadow variables
  Object.entries(currentTheme.shadows).forEach(([key, value]) => {
    root.style.setProperty(`--shadow-${key}`, value);
  });
  
  // Update transition variables
  Object.entries(currentTheme.transitions).forEach(([key, value]) => {
    root.style.setProperty(`--transition-${key}`, value);
  });
}

// Initialize CSS variables on load
if (typeof document !== 'undefined') {
  updateCSSVariables();
}

// Export utility functions for getting theme values
export const theme = {
  get colors() { return currentTheme.colors; },
  get typography() { return currentTheme.typography; },
  get spacing() { return currentTheme.spacing; },
  get borderRadius() { return currentTheme.borderRadius; },
  get shadows() { return currentTheme.shadows; },
  get transitions() { return currentTheme.transitions; }
};
