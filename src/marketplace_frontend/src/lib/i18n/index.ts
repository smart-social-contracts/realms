import { browser } from '$app/environment';
import { init, register, isLoading, locale } from 'svelte-i18n';

export const supportedLocales = [
  { id: 'en', name: 'English' },
  { id: 'es', name: 'Español' },
  { id: 'de', name: 'Deutsch' },
  { id: 'fr', name: 'Français' },
  { id: 'zh-CN', name: '中文 (简体)' },
  { id: 'it', name: 'Italiano' },
];

register('en', () => import('./locales/en.json'));
register('es', () => import('./locales/es.json'));
register('de', () => import('./locales/de.json'));
register('fr', () => import('./locales/fr.json'));
register('zh-CN', () => import('./locales/zh-CN.json'));
register('it', () => import('./locales/it.json'));

const TARGET_LANGUAGES = supportedLocales.map((l) => l.id);
const STORAGE_KEY = 'marketplacePreferredLocale';

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
  if (!browser) return 'en';

  // 1) Explicit URL parameter wins (shareable links).
  try {
    const urlLocale = new URLSearchParams(window.location.search).get('locale');
    if (urlLocale && TARGET_LANGUAGES.includes(urlLocale)) return urlLocale;
  } catch (e) {
    console.error('Error reading URL parameters:', e);
  }

  // 2) Previously stored preference.
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && TARGET_LANGUAGES.includes(stored)) return stored;
  } catch (e) {
    console.error('Error accessing localStorage:', e);
  }

  // 3) Browser language preferences.
  const browserLanguages = navigator.languages || [navigator.language];
  for (const lang of browserLanguages) {
    if (TARGET_LANGUAGES.includes(lang)) return lang;
    const code = lang.split('-')[0];
    if (code === 'zh') return 'zh-CN';
    if (TARGET_LANGUAGES.includes(code)) return code;
  }

  return 'en';
}

export function setLocale(newLocale: string) {
  if (browser) {
    try {
      localStorage.setItem(STORAGE_KEY, newLocale);
    } catch (e) {
      console.error('Error saving locale to localStorage:', e);
    }
  }
  locale.set(newLocale);
}

export async function initI18n() {
  init({
    fallbackLocale: 'en',
    initialLocale: browser ? getPreferredLocale() : 'en',
  });
  await waitLocale();
}
