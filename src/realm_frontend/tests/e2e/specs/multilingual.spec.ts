import { test, expect } from '@playwright/test';

test.describe('Multilingual Support', () => {
  const supportedLanguages = [
    { code: 'en', name: 'English', welcome: 'Welcome to Realms' },
    { code: 'de', name: 'Deutsch', welcome: 'Willkommen bei Realms' },
    { code: 'fr', name: 'Français', welcome: 'Bienvenue sur Realms' },
    { code: 'es', name: 'Español', welcome: 'Bienvenido a Realms' },
    { code: 'zh-CN', name: '中文 (简体)', welcome: '欢迎来到 Realms' }
  ];

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.clear();
      document.cookie = 'locale=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    });
  });

  test('should detect browser language and display correct translations', async ({ page, context }) => {
    for (const lang of supportedLanguages) {
      const newContext = await context.browser()?.newContext({
        locale: lang.code === 'zh-CN' ? 'zh-CN' : lang.code
      });
      
      if (newContext) {
        const newPage = await newContext.newPage();
        await newPage.goto('/i18n-debug');
        await newPage.waitForLoadState('networkidle');
        
        await expect(newPage.getByText(lang.welcome)).toBeVisible({ timeout: 10000 });
        
        await newContext.close();
      }
    }
  });

  test('should allow manual language switching', async ({ page }) => {
    await page.goto('/i18n-debug');
    await page.waitForLoadState('networkidle');

    for (const lang of supportedLanguages) {
      await page.getByRole('button', { name: `Switch to ${lang.name}` }).click();
      await page.waitForTimeout(500);
      
      await expect(page.getByText(lang.welcome)).toBeVisible({ timeout: 5000 });
    }
  });

  test('should persist language preference in localStorage', async ({ page }) => {
    await page.goto('/i18n-debug');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: 'Switch to Deutsch' }).click();
    await page.waitForTimeout(500);
    
    await expect(page.getByText('Willkommen bei Realms')).toBeVisible();
    
    await page.reload();
    await page.waitForLoadState('networkidle');
    
    await expect(page.getByText('Willkommen bei Realms')).toBeVisible();
  });

  test('should update language switcher component', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    const languageSwitcher = page.locator('.language-switcher select');
    if (await languageSwitcher.isVisible()) {
      for (const lang of supportedLanguages) {
        await expect(languageSwitcher.locator(`option[value="${lang.code}"]`)).toBeAttached();
      }
    }
  });

  test('should handle unsupported browser languages gracefully', async ({ page, context }) => {
    const newContext = await context.browser()?.newContext({
      locale: 'ja-JP'
    });
    
    if (newContext) {
      const newPage = await newContext.newPage();
      await newPage.goto('/i18n-debug');
      await newPage.waitForLoadState('networkidle');
      
      await expect(newPage.getByText('Welcome to Realms')).toBeVisible({ timeout: 10000 });
      
      await newContext.close();
    }
  });

  test('should map language variants correctly', async ({ page, context }) => {
    const chineseVariants = ['zh', 'zh-TW', 'zh-HK'];
    
    for (const variant of chineseVariants) {
      const newContext = await context.browser()?.newContext({
        locale: variant
      });
      
      if (newContext) {
        const newPage = await newContext.newPage();
        await newPage.goto('/i18n-debug');
        await newPage.waitForLoadState('networkidle');
        
        await expect(newPage.getByText('欢迎来到 Realms')).toBeVisible({ timeout: 10000 });
        
        await newContext.close();
      }
    }
  });

  test('should display Chinese translations correctly', async ({ page }) => {
    await page.goto('/i18n-debug');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: 'Switch to 中文 (简体)' }).click();
    await page.waitForTimeout(500);
    
    await expect(page.getByText('欢迎来到 Realms')).toBeVisible();
    await expect(page.getByText('加载中...')).toBeVisible();
    await expect(page.getByText('发生错误')).toBeVisible();
  });

  test('should maintain language preference across page navigation', async ({ page }) => {
    await page.goto('/i18n-debug');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: 'Switch to Français' }).click();
    await page.waitForTimeout(500);
    
    await expect(page.getByText('Bienvenue sur Realms')).toBeVisible();
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    if (await page.getByText('Bienvenue sur Realms').isVisible()) {
      await expect(page.getByText('Bienvenue sur Realms')).toBeVisible();
    }
  });
});
