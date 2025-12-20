import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import es from './locales/es.json';
import de from './locales/de.json';
import fr from './locales/fr.json';
import it from './locales/it.json';
import zhCN from './locales/zh-CN.json';

export const supportedLocales = [
  { id: 'en', name: 'English' },
  { id: 'es', name: 'Español' },
  { id: 'de', name: 'Deutsch' },
  { id: 'fr', name: 'Français' },
  { id: 'zh-CN', name: '中文 (简体)' },
  { id: 'it', name: 'Italiano' }
];

const resources = {
  en: { translation: en },
  es: { translation: es },
  de: { translation: de },
  fr: { translation: fr },
  it: { translation: it },
  'zh-CN': { translation: zhCN }
};

function getPreferredLocale() {
  const targetLanguages = ['en', 'de', 'fr', 'es', 'zh-CN', 'it'];
  
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const urlLocale = urlParams.get('locale');
    if (urlLocale && targetLanguages.includes(urlLocale)) {
      return urlLocale;
    }
  } catch (e) {
    console.error('Error reading URL parameters:', e);
  }
  
  try {
    const storedLocale = localStorage.getItem('preferredLocale');
    if (storedLocale && targetLanguages.includes(storedLocale)) {
      return storedLocale;
    }
  } catch (e) {
    console.error('Error accessing localStorage:', e);
  }
  
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
  
  return 'en';
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: getPreferredLocale(),
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
