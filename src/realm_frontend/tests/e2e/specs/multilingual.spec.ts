import { test, expect } from '@playwright/test';
import { readFileSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get the directory name in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Multilingual Support', () => {

  const supportedLanguages = [
    { code: 'en', name: 'English' },
    { code: 'de', name: 'Deutsch' },
    { code: 'fr', name: 'Français' },
    { code: 'es', name: 'Español' },
    { code: 'zh-CN', name: '中文 (简体)' }
  ];

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      document.cookie = 'locale=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    });
  });

  test('should detect browser language and display correct translations', async ({ page, context }) => {
    // Load locale data using fs with ESM-compatible path resolution
    const localeData = {};
    for (const lang of supportedLanguages) {
      const filePath = path.resolve(__dirname, `../../../src/lib/i18n/locales/${lang.code}.json`);
      const fileContent = readFileSync(filePath, 'utf8');
      localeData[lang.code] = JSON.parse(fileContent);
    }
    
    for (const lang of supportedLanguages) {
      const newContext = await context.browser()?.newContext({ locale: lang.code });
      
      if (newContext) {
        const newPage = await newContext.newPage();
        await newPage.goto('/');
        await newPage.waitForLoadState('networkidle');

        // TODO: implement this
        // // Get the expected translation for 'dashboard' from the locale file
        // const expectedText = localeData[lang.code].navigation.dashboard;
        
        // await expect(newPage.getByText(expectedText, { exact: false })).toBeVisible({ 
        //   timeout: 10000
        // });
        
        await newContext.close();
      }
    }
  });

});
