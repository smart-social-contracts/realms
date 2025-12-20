import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { supportedLocales } from '../i18n';

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const changeLanguage = (locale) => {
    i18n.changeLanguage(locale);
    localStorage.setItem('preferredLocale', locale);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-slate-600 hover:text-slate-900 transition-colors"
        aria-label="Change language"
      >
        <Globe className="w-5 h-5" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-2 z-50">
            {supportedLocales.map((locale) => (
              <button
                key={locale.id}
                onClick={() => changeLanguage(locale.id)}
                className={`w-full text-left px-4 py-2 hover:bg-slate-50 transition-colors ${
                  i18n.language === locale.id ? 'bg-slate-100 font-semibold' : ''
                }`}
              >
                {locale.name}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
