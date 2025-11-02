import { browser } from "$app/environment";
import { init, register, getLocaleFromNavigator, isLoading, addMessages } from "svelte-i18n";

export const supportedLocales = [
  { id: "en", name: "English" },
  { id: "es", name: "Español" },
  { id: "de", name: "Deutsch" },
  { id: "fr", name: "Français" },
  { id: "zh-CN", name: "中文 (简体)" },
  { id: "it", name: "Italiano" }
];

// Use the correct path for imports in realm_frontend
register("en", () => import("./locales/en.json"));
register("es", () => import("./locales/es.json"));
register("de", () => import("./locales/de.json"));
register("fr", () => import("./locales/fr.json"));
register("zh-CN", () => import("./locales/zh-CN.json"));
register("it", () => import("./locales/it.json"));

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

function getPreferredLocale(): string {
  if (!browser) return "en";
  
  const targetLanguages = ["en", "de", "fr", "es", "zh-CN"];
  
  // Check URL parameters first
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const urlLocale = urlParams.get('locale');
    if (urlLocale && targetLanguages.includes(urlLocale)) {
      console.log('Using locale from URL parameter:', urlLocale);
      return urlLocale;
    }
  } catch (e) {
    console.error('Error reading URL parameters:', e);
  }
  
  // Check localStorage
  try {
    const storedLocale = localStorage.getItem('preferredLocale');
    if (storedLocale && targetLanguages.includes(storedLocale)) {
      console.log('Using locale from localStorage:', storedLocale);
      return storedLocale;
    }
  } catch (e) {
    console.error('Error accessing localStorage:', e);
  }
  
  // Fall back to browser language preferences
  const browserLanguages = navigator.languages || [navigator.language];
  
  for (const browserLang of browserLanguages) {
    if (targetLanguages.includes(browserLang)) {
      return browserLang;
    }
    
    const langCode = browserLang.split('-')[0];
    if (langCode === 'zh') return 'zh-CN';
    if (targetLanguages.includes(langCode)) {
      return langCode;
    }
  }
  
  return "en";
}

// Find and register all extension translations
export async function loadExtensionTranslations() {
  // Define type for module imports
  type JsonModule = { default: Record<string, any> };
  
  try {
    // Define supported locales for extension translations
    const supportedExtensionLocales = [
      { code: 'en', modules: import.meta.glob('./locales/extensions/*/en.json') },
      { code: 'es', modules: import.meta.glob('./locales/extensions/*/es.json') },
      { code: 'de', modules: import.meta.glob('./locales/extensions/*/de.json') },
      { code: 'fr', modules: import.meta.glob('./locales/extensions/*/fr.json') },
      { code: 'it', modules: import.meta.glob('./locales/extensions/*/it.json') },
      { code: 'zh-CN', modules: import.meta.glob('./locales/extensions/*/zh-CN.json') }
    ];

    // Process all locales
    await Promise.all(supportedExtensionLocales.map(async ({ code, modules }) => {
      for (const path of Object.keys(modules)) {
        try {
          // Extract extension ID from path
          const extensionId = path.split('/').slice(-2)[0];
          const module = await modules[path]();
          const translations = (module as JsonModule).default;
          
          addMessages(code, {
            extensions: {
              [extensionId]: translations
            }
          });
          
          // console.log(`Loaded translations for extension: ${extensionId}, locale: ${code}, translations: ${JSON.stringify(translations)}`);
        } catch (err) {
          console.error(`Failed to load extension translation: ${path} for locale: ${code}`, err);
        }
      }
    }));
    
    console.log('All extension translations loaded successfully');
  } catch (error) {
    console.error('Error loading extension translations:', error);
  }
}

export async function initI18n() {
  init({
    fallbackLocale: "en",
    initialLocale: browser ? getPreferredLocale() : "en"
  });

  console.log('i18n initialized in realm_frontend');
  
  // Load all extension translations and wait for them
  await loadExtensionTranslations();
  
  console.log('All translations (core + extensions) loaded');
}
