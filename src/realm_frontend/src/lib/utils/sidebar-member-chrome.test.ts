import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
	isRealmMember,
	shouldShowMeSection,
	visibleSidebarCategories,
} from './sidebar-member-chrome';

const here = dirname(fileURLToPath(import.meta.url));
const sidebar = readFileSync(resolve(here, '../../routes/(sidebar)/Sidebar.svelte'), 'utf8');
const layout = readFileSync(resolve(here, '../../routes/(sidebar)/+layout.svelte'), 'utf8');
const navbar = readFileSync(resolve(here, '../../routes/(sidebar)/Navbar.svelte'), 'utf8');
const sidebarConfig = readFileSync(resolve(here, '../config/sidebar.ts'), 'utf8');
const gggRoute = resolve(here, '../../routes/(sidebar)/ggg/+page.svelte');

const guestProfiles = [] as const;
const visitorProfiles = ['visitor'] as const;
const memberProfiles = ['member'] as const;
const adminProfiles = ['admin'] as const;
const founderProfiles = ['admin', 'member'] as const;

const categories = [
	{ id: 'governance', label: 'Governance' },
	{ id: 'realm_management', label: 'Realm Management' },
	{ id: 'finances', label: 'Finances' },
];

describe('isRealmMember', () => {
	it('is false for guests (signed-in, no membership profiles)', () => {
		expect(isRealmMember(guestProfiles)).toBe(false);
		expect(isRealmMember(visitorProfiles)).toBe(false);
		expect(isRealmMember(null)).toBe(false);
		expect(isRealmMember(undefined)).toBe(false);
	});

	it('is true for members, admins, and founder-in-setup (admin)', () => {
		expect(isRealmMember(memberProfiles)).toBe(true);
		expect(isRealmMember(adminProfiles)).toBe(true);
		expect(isRealmMember(founderProfiles)).toBe(true);
	});
});

describe('shouldShowMeSection', () => {
	it('hides ME for anonymous and for authenticated guests', () => {
		expect(shouldShowMeSection(false, guestProfiles)).toBe(false);
		expect(shouldShowMeSection(false, memberProfiles)).toBe(false);
		expect(shouldShowMeSection(true, guestProfiles)).toBe(false);
		expect(shouldShowMeSection(true, visitorProfiles)).toBe(false);
	});

	it('shows ME for authenticated members and admins', () => {
		expect(shouldShowMeSection(true, memberProfiles)).toBe(true);
		expect(shouldShowMeSection(true, adminProfiles)).toBe(true);
		expect(shouldShowMeSection(true, founderProfiles)).toBe(true);
	});
});

describe('visibleSidebarCategories', () => {
	it('strips REALM MANAGEMENT for guests and leaves other groups', () => {
		expect(visibleSidebarCategories(categories, guestProfiles).map((c) => c.id)).toEqual([
			'governance',
			'finances',
		]);
		expect(visibleSidebarCategories(categories, visitorProfiles).map((c) => c.id)).toEqual([
			'governance',
			'finances',
		]);
	});

	it('keeps REALM MANAGEMENT for members', () => {
		expect(visibleSidebarCategories(categories, memberProfiles).map((c) => c.id)).toEqual([
			'governance',
			'realm_management',
			'finances',
		]);
		expect(visibleSidebarCategories(categories, adminProfiles).map((c) => c.id)).toEqual([
			'governance',
			'realm_management',
			'finances',
		]);
	});
});

describe('Sidebar.svelte membership gate', () => {
	it('does not treat $isAuthenticated as membership for ME', () => {
		expect(sidebar).toContain('shouldShowMeSection');
		expect(sidebar).toContain('visibleSidebarCategories');
		expect(sidebar).toContain('userProfiles');
		expect(sidebar).toContain('{#if showMeSection}');
		expect(sidebar).not.toContain('hasJoined()');
		expect(sidebar.match(/\{#if showMeSection\}/g)?.length).toBe(2);
	});

	it('keeps the host brain FAB wiring (not chrome cleanup)', () => {
		expect(layout).toContain("event.action.type === 'assistant.open'");
		expect(layout).toContain('portalAssistantOpen');
	});
});

describe('leftover /ggg Admin Dashboard is gone', () => {
	it('does not serve a /ggg host route', () => {
		expect(existsSync(gggRoute)).toBe(false);
	});

	it('has no /ggg nav links in host chrome for guest, member, or admin', () => {
		for (const chrome of [sidebar, layout, navbar, sidebarConfig]) {
			expect(chrome).not.toContain('/ggg');
			expect(chrome).not.toContain('_core_system');
		}
	});
});
