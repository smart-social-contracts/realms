import { Page, expect } from '@playwright/test';

export class AuthHelper {
	constructor(private page: Page) {}

	async mockInternetIdentity() {
		await this.page.route('**/identity.ic0.app/**', route => {
			route.fulfill({
				status: 200,
				body: JSON.stringify({ success: true })
			});
		});
	}

	async mockBackendCalls() {
		await this.page.route('**/localhost:5000/api/**', route => {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ name: 'Test Realm' })
			});
		});

		await this.page.route('**/api/**', route => {
			route.fulfill({
				status: 200,
				body: JSON.stringify({ success: true })
			});
		});
	}

	async loginAsAdmin() {
		await this.page.addInitScript(() => {
			sessionStorage.setItem('auth_isAuthenticated', 'true');
			sessionStorage.setItem('auth_principal', '"test-principal-123"');
			sessionStorage.setItem('auth_userIdentity', '{"principal": "test-principal-123"}');
		});

		await this.page.goto('/extensions/public_dashboard');
		await this.page.waitForLoadState('networkidle');
	}

	async setupAuthenticatedSession() {
		await this.page.addInitScript(() => {
			sessionStorage.setItem('auth_isAuthenticated', 'true');
			sessionStorage.setItem('auth_principal', '"test-principal-123"');
			sessionStorage.setItem('auth_userIdentity', '{"principal": "test-principal-123"}');
		});

		await this.mockAllAPICalls();
	}

	async mockAllAPICalls() {
		await this.page.route('**/identity.ic0.app/**', route => {
			route.fulfill({
				status: 200,
				body: JSON.stringify({ success: true })
			});
		});

		await this.page.route('**/localhost:5000/api/**', route => {
			route.fulfill({
				status: 200,
				contentType: 'application/json',
				body: JSON.stringify({ name: 'Test Realm' })
			});
		});

		await this.page.route('**/api/**', route => {
			route.fulfill({
				status: 200,
				body: JSON.stringify({ success: true })
			});
		});
	}

	async navigateToAuthenticatedApp() {
		await this.setupAuthenticatedSession();
		
		await this.page.goto('/join');
		await this.page.waitForLoadState('networkidle');
		
		await this.page.locator('input[name="agreement"][value="agree"]').click();
		await this.page.locator('select').selectOption('admin');
		
		await this.page.route('**/join_realm', route => {
			route.fulfill({
				status: 200,
				body: JSON.stringify({ success: true })
			});
		});
		
		await this.page.locator('button[type="submit"]').click();
		
		try {
			await expect(this.page.getByText('Successfully Joined!')).toBeVisible({ timeout: 5000 });
			await this.page.getByRole('link', { name: 'Go to Dashboard' }).click();
		} catch {
			await this.page.goto('/dashboard');
		}
		
		await this.page.waitForLoadState('networkidle');
		await expect(this.page.getByRole('complementary', { name: 'Sidebar' })).toBeVisible({ timeout: 10000 });
	}

	async testJoinFlow() {
		await this.mockAllAPICalls();
		
		await this.page.addInitScript(() => {
			sessionStorage.setItem('auth_isAuthenticated', 'true');
			sessionStorage.setItem('auth_principal', '"test-principal-123"');
			sessionStorage.setItem('auth_userIdentity', '{"principal": "test-principal-123"}');
		});
		
		await this.page.goto('/join');
		await this.page.waitForLoadState('networkidle');
		
		await expect(this.page.getByText('Do you agree to these terms?')).toBeVisible({ timeout: 10000 });
		
		await this.page.locator('input[name="agreement"][value="agree"]').click();
		
		await this.page.locator('select').selectOption('admin');
		
		await this.page.route('**/join_realm', route => {
			route.fulfill({
				status: 200,
				body: JSON.stringify({ success: true })
			});
		});
		
		await this.page.locator('button[type="submit"]').click();
		
		try {
			await expect(this.page.getByText('Successfully Joined!')).toBeVisible({ timeout: 10000 });
		} catch {
			await this.page.waitForURL('**/dashboard', { timeout: 5000 });
		}
	}
}
