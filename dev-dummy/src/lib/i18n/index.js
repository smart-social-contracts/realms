import { register, init, getLocaleFromNavigator } from 'svelte-i18n';

const defaultLocale = 'en';

register('en', () => import('./locales/en.json'));
register('es', () => import('./locales/es.json'));

export function initI18n() {
  init({
    fallbackLocale: defaultLocale,
    initialLocale: getLocaleFromNavigator() || defaultLocale,
  });
}

export { waitLocale } from 'svelte-i18n';
