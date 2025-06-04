import { browser } from '$app/environment';
import { init, register, getLocaleFromNavigator, locale, dictionary, isLoading } from 'svelte-i18n';

// Register locales
const locales = ['en', 'es', 'de', 'fr', 'it'];

// Define supported locales
export const supportedLocales = [
  { id: 'en', name: 'English' },
  { id: 'es', name: 'Español' },
  { id: 'de', name: 'Deutsch' },
  { id: 'fr', name: 'Français' },
  { id: 'it', name: 'Italiano' }
];

// Register locale loaders
register('en', () => import('./locales/en.json'));
register('es', () => import('./locales/es.json'));
register('de', () => import('./locales/de.json'));
register('fr', () => import('./locales/fr.json'));
register('it', () => import('./locales/it.json'));

// For debugging
if (browser) {
  locale.subscribe((value) => {
    console.log('i18n: Current locale:', value);
  });
  
  dictionary.subscribe((dict) => {
    console.log('i18n: Dictionary loaded:', Object.keys(dict));
  });
}

// Helper function to wait for locale to be ready
export function waitLocale(): Promise<void> {
  return new Promise<void>((resolve) => {
    const unsubscribe = isLoading.subscribe(($isLoading) => {
      if (!$isLoading) {
        unsubscribe();
        resolve();
      }
    });
  });
}

// Initialize i18n
export function initI18n() {
  console.log('Initializing i18n...');
  
  // Set default locale before initialization to prevent errors
  if (browser) {
    locale.set(localStorage.getItem('preferredLocale') || 'en');
  }
  
  init({
    fallbackLocale: 'en',
    initialLocale: browser ? getLocaleFromNavigator() : 'en',
    loadingDelay: 200, // Add small delay for better transitions
  });
  
  // Log the initialization
  console.log('i18n initialized with fallback locale: en');
} 