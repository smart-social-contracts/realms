import { browser } from "$app/environment";
import { init, register, getLocaleFromNavigator, isLoading } from "svelte-i18n";

export const supportedLocales = [
  { id: "en", name: "English" },
  { id: "es", name: "Español" },
  { id: "de", name: "Deutsch" },
  { id: "fr", name: "Français" },
  { id: "it", name: "Italiano" }
];

// Use the correct path for imports in realm_frontend
register("en", () => import("./locales/en.json"));
register("es", () => import("./locales/es.json"));
register("de", () => import("./locales/de.json"));
register("fr", () => import("./locales/fr.json"));
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
}
