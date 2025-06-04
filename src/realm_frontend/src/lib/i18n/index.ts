import { browser } from "$app/environment";
import { init, register, getLocaleFromNavigator, isLoading, addMessages } from "svelte-i18n";

export const supportedLocales = [
  { id: "en", name: "English" },
  { id: "es", name: "Español" }
];

// Use the correct path for imports in realm_frontend
register("en", () => import("$lib/i18n/locales/en.json"));
register("es", () => import("$lib/i18n/locales/es.json"));

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

// Find and register all extension translations
export async function loadExtensionTranslations() {
  // Define type for module imports
  type JsonModule = { default: Record<string, any> };
  
  try {
    // Import all extension translation files using static patterns
    const enModules = import.meta.glob('./locales/extensions/*/en.json');
    const esModules = import.meta.glob('./locales/extensions/*/es.json');
    
    // Process English translations
    for (const path of Object.keys(enModules)) {
      try {
        // Extract extension ID from path
        const extensionId = path.split('/').slice(-2)[0];
        const module = await enModules[path]();
        const translations = (module as JsonModule).default;
        
        addMessages('en', {
          extensions: {
            [extensionId]: translations
          }
        });
        
        console.log(`Loaded translations for extension: ${extensionId}, locale: en`);
      } catch (err) {
        console.error(`Failed to load extension translation: ${path}`, err);
      }
    }
    
    // Process Spanish translations
    for (const path of Object.keys(esModules)) {
      try {
        // Extract extension ID from path
        const extensionId = path.split('/').slice(-2)[0];
        const module = await esModules[path]();
        const translations = (module as JsonModule).default;
        
        addMessages('es', {
          extensions: {
            [extensionId]: translations
          }
        });
        
        console.log(`Loaded translations for extension: ${extensionId}, locale: es`);
      } catch (err) {
        console.error(`Failed to load extension translation: ${path}`, err);
      }
    }
  } catch (err) {
    console.error("Error loading extension translations:", err);
  }
}

export function initI18n() {
  // Set default locale before initialization to prevent errors
  if (browser) {
    try {
      const storedLocale = localStorage.getItem('preferredLocale');
      if (storedLocale) {
        console.log('Setting initial locale from localStorage:', storedLocale);
      }
    } catch (e) {
      console.error('Error accessing localStorage:', e);
    }
  }
  init({
    fallbackLocale: "en",
    initialLocale: browser ? getLocaleFromNavigator() : "en"
  });

  console.log('i18n initialized in realm_frontend');
  
  // Load all extension translations
  loadExtensionTranslations();
}
