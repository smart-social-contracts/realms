import { describe, expect, it } from 'vitest';
import type { SidebarConfig } from '$lib/config/sidebar';
import { extensionLoadingMessage, resolveBreadcrumb, resolveExtensionLabel } from './breadcrumb';

const config: SidebarConfig = {
	welcomeItems: [
		{
			label: 'My Dashboard',
			icon: 'ti-home',
			extensionId: 'member_dashboard',
			href: '/extensions/member_dashboard',
		},
	],
	mundusItems: [],
	categories: [
		{
			id: 'governance',
			label: 'Governance',
			items: [
				{
					label: 'Voting',
					icon: 'ti-checkbox',
					extensionId: 'voting',
					href: '/extensions/voting',
				},
			],
		},
	],
	defaultPath: '/extensions/member_dashboard',
};

describe('resolveBreadcrumb', () => {
	it('maps utility routes', () => {
		expect(resolveBreadcrumb('/settings', config)).toEqual([{ label: 'Settings' }]);
	});

	it('maps welcome items', () => {
		expect(resolveBreadcrumb('/extensions/member_dashboard', config)).toEqual([
			{ label: 'My Dashboard' },
		]);
	});

	it('maps category extension items', () => {
		expect(resolveBreadcrumb('/extensions/voting', config)).toEqual([
			{ label: 'Governance' },
			{ label: 'Voting' },
		]);
	});

	it('falls back for unknown extensions', () => {
		expect(resolveBreadcrumb('/extensions/package_manager', null)).toEqual([
			{ label: 'Package Manager' },
		]);
	});

	it('resolves extension label from sidebar config', () => {
		expect(resolveExtensionLabel('member_dashboard', config)).toBe('My Dashboard');
		expect(resolveExtensionLabel('voting', config)).toBe('Voting');
	});

	it('falls back extension label from slug', () => {
		expect(resolveExtensionLabel('package_manager', null)).toBe('Package Manager');
	});

	it('builds user-facing loading message', () => {
		expect(extensionLoadingMessage('member_dashboard', config)).toBe('Loading My Dashboard...');
		expect(extensionLoadingMessage('public_dashboard', null)).toBe('Loading Public Dashboard...');
	});
});
