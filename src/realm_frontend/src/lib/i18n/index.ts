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

// ---------------------------------------------------------------------------
// Runtime extension translations (Issue #168, Layered Realm)
// ---------------------------------------------------------------------------
// `loadExtensionTranslations()` below is the legacy, build-time path: it uses
// `import.meta.glob` to register every JSON file shipped under
// `./locales/extensions/*/<lang>.json` at the moment realm_frontend was
// compiled. With the Layered Realm transition, extensions are no longer baked
// into the WASM and their i18n JSON lives in `file_registry`. The
// `loadExtensionTranslationsFromRegistry(...)` function below fetches them
// over HTTP at runtime and feeds them to the same `addMessages(...)` API, so
// the rest of the app does not need to know whether a given extension is
// "bundled" or "runtime".
//
// The contract for an extension's i18n in `file_registry` is:
//
//     ext/<extension_id>/<version>/frontend/i18n/<locale>.json
//
// (this matches what `realms extension publish` uploads, see
// `cli/realms/cli/commands/extension.py::_publish_extension_command`).
//
// 404s are silent — an extension is allowed to omit a locale; we will fall
// back to the manifest's `sidebar_label` (rendered by Sidebar.svelte) and to
// raw key strings for missing translations, exactly like svelte-i18n does for
// any missing key.
// ---------------------------------------------------------------------------

import { fileRegistryBaseUrlFor } from "$lib/extension-loader";

interface RuntimeExtensionSource {
  registry_canister_id: string;
  version: string;
}

interface RuntimeExtensionsResponse {
  success: boolean;
  runtime_extensions?: string[];
  sources?: Record<string, RuntimeExtensionSource | null>;
}

/**
 * Fetch a single locale's translation file for one extension and merge it
 * into svelte-i18n. Resolves to `true` on success, `false` if the file is
 * missing or invalid (which is *not* an error — many extensions don't have
 * translations for every locale).
 */
async function fetchAndRegisterExtensionLocale(
  baseUrl: string,
  extensionId: string,
  version: string,
  locale: string,
): Promise<boolean> {
  const url = `${baseUrl}/ext/${extensionId}/${version}/frontend/i18n/${locale}.json`;
  try {
    const res = await fetch(url, { credentials: "omit" });
    if (!res.ok) {
      return false;
    }
    const translations = await res.json();
    if (!translations || typeof translations !== "object") {
      return false;
    }
    addMessages(locale, {
      extensions: {
        [extensionId]: translations,
      },
    });
    return true;
  } catch (err) {
    // Networking issues are not fatal — extension i18n is best-effort.
    console.warn(
      `[i18n] Failed to fetch ${locale}.json for runtime extension '${extensionId}@${version}':`,
      err,
    );
    return false;
  }
}

/**
 * Discover every runtime-installed extension via realm_backend and load its
 * locales from file_registry. Safe to call multiple times: addMessages merges
 * by key and svelte-i18n re-evaluates when the locale changes.
 *
 * @param backend  An actor with `list_runtime_extensions(): Promise<string>`
 *                 (i.e. a realm_backend agent).
 * @param locales  Locale codes to fetch. Defaults to `supportedLocales`.
 */
export async function loadExtensionTranslationsFromRegistry(
  backend: { list_runtime_extensions: () => Promise<string> } | null | undefined,
  locales: readonly string[] = supportedLocales.map((l) => l.id),
): Promise<void> {
  if (!backend || typeof backend.list_runtime_extensions !== "function") {
    console.warn(
      "[i18n] loadExtensionTranslationsFromRegistry: no backend with list_runtime_extensions; skipping.",
    );
    return;
  }

  let parsed: RuntimeExtensionsResponse;
  try {
    const raw = await backend.list_runtime_extensions();
    parsed = JSON.parse(raw) as RuntimeExtensionsResponse;
  } catch (err) {
    console.warn("[i18n] list_runtime_extensions failed; skipping registry i18n load:", err);
    return;
  }

  if (!parsed?.success || !Array.isArray(parsed.runtime_extensions)) {
    return;
  }

  const sources = parsed.sources ?? {};
  const tasks: Array<Promise<boolean>> = [];
  let registeredCount = 0;
  let extensionCount = 0;

  for (const extId of parsed.runtime_extensions) {
    const src = sources[extId];
    if (!src?.registry_canister_id || !src?.version) {
      // Bundled or manually-installed extensions don't have registry coords.
      continue;
    }
    extensionCount++;
    const baseUrl = fileRegistryBaseUrlFor(src.registry_canister_id);
    for (const locale of locales) {
      const t = fetchAndRegisterExtensionLocale(baseUrl, extId, src.version, locale).then(
        (ok) => {
          if (ok) registeredCount++;
          return ok;
        },
      );
      tasks.push(t);
    }
  }

  await Promise.all(tasks);
  console.log(
    `[i18n] Runtime extension translations loaded: ${registeredCount} file(s) ` +
      `across ${extensionCount} extension(s) and ${locales.length} locale(s).`,
  );
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

export interface InitI18nOptions {
  /**
   * Optional realm_backend agent. When provided, runtime extension
   * translations will be loaded from `file_registry` (Layered Realm /
   * Issue #168) in addition to any build-time bundled translations.
   * If omitted, only build-time translations are loaded.
   */
  backend?: { list_runtime_extensions: () => Promise<string> } | null;
}

export async function initI18n(options: InitI18nOptions = {}) {
  init({
    fallbackLocale: "en",
    initialLocale: browser ? getPreferredLocale() : "en"
  });

  console.log('i18n initialized in realm_frontend');

  // 1) Build-time bundled extension translations (legacy path; will be empty
  //    in fully layered deployments because no extension code is shipped in
  //    the realm_frontend WASM).
  await loadExtensionTranslations();

  // 2) Runtime extension translations from file_registry (Layered Realm).
  //    This is best-effort and never throws — a failure here just means some
  //    extension labels fall back to manifest sidebar_label / raw keys.
  if (options.backend) {
    try {
      await loadExtensionTranslationsFromRegistry(options.backend);
    } catch (err) {
      console.warn('[i18n] runtime extension translations failed (non-fatal):', err);
    }
  }

  console.log('All translations (core + extensions) loaded');
}
