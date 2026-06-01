import { describe, expect, it } from 'vitest';
import type { SidebarConfig } from '$lib/config/sidebar';
import { resolveBreadcrumb } from './breadcrumb';

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
		expect(resolveBreadcrumb('/settings', config)).toEqual([
			{ label: 'Home', href: '/' },
			{ label: 'Settings' },
		]);
	});

	it('maps welcome items', () => {
		expect(resolveBreadcrumb('/extensions/member_dashboard', config)).toEqual([
			{ label: 'Home', href: '/' },
			{ label: 'My Dashboard' },
		]);
	});

	it('maps category extension items', () => {
		expect(resolveBreadcrumb('/extensions/voting', config)).toEqual([
			{ label: 'Home', href: '/' },
			{ label: 'Governance' },
			{ label: 'Voting' },
		]);
	});

	it('falls back for unknown extensions', () => {
		expect(resolveBreadcrumb('/extensions/package_manager', null)).toEqual([
			{ label: 'Home', href: '/' },
			{ label: 'Package Manager' },
		]);
	});
});
