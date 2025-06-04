import { browser } from '$app/environment';
import { init, register, getLocaleFromNavigator, locale, dictionary } from 'svelte-i18n';

// Register locales
const locales = ['en', 'es'];

// Define supported locales
export const supportedLocales = [
  { id: 'en', name: 'English' },
  { id: 'es', name: 'Español' }
];

// Register locale loaders
register('en', () => import('./locales/en.json'));
register('es', () => import('./locales/es.json'));

// For debugging
if (browser) {
  locale.subscribe((value) => {
    console.log('i18n: Current locale:', value);
  });
  
  dictionary.subscribe((dict) => {
    console.log('i18n: Dictionary loaded:', Object.keys(dict));
  });
}

// Initialize i18n
export function initI18n() {
  console.log('Initializing i18n...');
  init({
    fallbackLocale: 'en',
    initialLocale: browser ? getLocaleFromNavigator() : 'en',
    loadingDelay: 200, // Add small delay for better transitions
  });
  
  // Log the initialization
  console.log('i18n initialized with fallback locale: en');
} 