import { Page, expect } from '@playwright/test';

export class JoinPage {
	constructor(private page: Page) {}

	async goto() {
		await this.page.goto('/join');
	}

	async agreeToTerms() {
		await this.page.getByRole('radio', { name: 'I agree to the terms' }).click();
	}

	async selectProfile(profile: 'admin' | 'member') {
		await this.page.getByRole('combobox').selectOption(profile);
	}

	async submitJoin() {
		await this.page.getByRole('button', { name: /Join Realm/ }).click();
	}

	async verifySuccessfulJoin() {
		await expect(this.page.getByText('Successfully Joined!')).toBeVisible();
		await expect(this.page.getByRole('link', { name: 'Go to Dashboard' })).toBeVisible();
	}

	async goToDashboard() {
		await this.page.getByRole('link', { name: 'Go to Dashboard' }).click();
	}
}

export class DashboardPage {
	constructor(private page: Page) {}

	async verifyLoaded() {
		await expect(this.page.locator('main')).toBeVisible();
		await this.page.waitForLoadState('networkidle');
	}
}

export class ExtensionsMarketplacePage {
	constructor(private page: Page) {}

	async verifyLoaded() {
		await expect(this.page.getByText('Extensions Marketplace')).toBeVisible();
		await expect(this.page.getByText('Browse and install extensions')).toBeVisible();
	}
}
