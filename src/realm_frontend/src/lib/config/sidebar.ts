/**
 * Static sidebar navigation configuration per user role.
 *
 * The sidebar structure is static per role — no dynamic show/hide of individual
 * items based on in-session state. Each role sees exactly the sections and items
 * defined here.
 */

export type UserRole = 'member' | 'admin' | 'developer';

export interface SidebarNavItem {
	label: string;
	icon: string;
	extensionId: string;
	href: string;
	isDefault?: boolean;
}

export interface SidebarCategory {
	id: string;
	label: string;
	items: SidebarNavItem[];
}

export interface SidebarConfig {
	categories: SidebarCategory[];
	defaultPath: string;
}

export interface TopUtilityItem {
	label: string;
	icon: string;
	href: string;
}

export const topUtilityItems: TopUtilityItem[] = [
	{ label: 'Account', icon: 'ti-user-circle', href: '/identities' },
	{ label: 'Messages', icon: 'ti-mail', href: '/messages' },
	{ label: 'Settings', icon: 'ti-settings', href: '/settings' },
];

const memberSidebar: SidebarConfig = {
	defaultPath: '/extensions/member_dashboard',
	categories: [
		{
			id: 'my_realm',
			label: 'MY REALM',
			items: [
				{ label: 'Overview', icon: 'ti-layout-dashboard', extensionId: 'member_dashboard', href: '/extensions/member_dashboard', isDefault: true },
				{ label: 'Passport', icon: 'ti-id-badge', extensionId: 'passport_verification', href: '/extensions/passport_verification' },
			],
		},
		{
			id: 'governance',
			label: 'GOVERNANCE',
			items: [
				{ label: 'Voting', icon: 'ti-ballpen', extensionId: 'voting', href: '/extensions/voting' },
				{ label: 'Justice', icon: 'ti-gavel', extensionId: 'justice_litigation', href: '/extensions/justice_litigation' },
				{ label: 'Land Registry', icon: 'ti-map-2', extensionId: 'land_registry', href: '/extensions/land_registry' },
			],
		},
		{
			id: 'finances',
			label: 'FINANCES',
			items: [
				{ label: 'Taxes', icon: 'ti-receipt', extensionId: 'metrics', href: '/extensions/metrics' },
			],
		},
		{
			id: 'system',
			label: 'SYSTEM',
			items: [
				{ label: 'Codex Viewer', icon: 'ti-file-code', extensionId: 'codex_viewer', href: '/extensions/codex_viewer' },
			],
		},
	],
};

const adminSidebar: SidebarConfig = {
	defaultPath: '/extensions/admin_dashboard',
	categories: [
		{
			id: 'administration',
			label: 'ADMINISTRATION',
			items: [
				{ label: 'Dashboard', icon: 'ti-layout-dashboard', extensionId: 'admin_dashboard', href: '/extensions/admin_dashboard', isDefault: true },
				{ label: 'Onboarding', icon: 'ti-user-plus', extensionId: 'admin_dashboard', href: '/extensions/admin_dashboard?section=onboarding' },
			],
		},
		{
			id: 'governance',
			label: 'GOVERNANCE',
			items: [
				{ label: 'Voting', icon: 'ti-ballpen', extensionId: 'voting', href: '/extensions/voting' },
				{ label: 'Justice', icon: 'ti-gavel', extensionId: 'justice_litigation', href: '/extensions/justice_litigation' },
				{ label: 'Land Registry', icon: 'ti-map-2', extensionId: 'land_registry', href: '/extensions/land_registry' },
				{ label: 'Zone Selector', icon: 'ti-layers-subtract', extensionId: 'zone_selector', href: '/extensions/zone_selector' },
			],
		},
		{
			id: 'finances',
			label: 'FINANCES',
			items: [
				{ label: 'Financial Report', icon: 'ti-chart-bar', extensionId: 'metrics', href: '/extensions/metrics' },
				{ label: 'Vault', icon: 'ti-safe', extensionId: 'vault', href: '/extensions/vault' },
			],
		},
		{
			id: 'system',
			label: 'SYSTEM',
			items: [
				{ label: 'Codex Viewer', icon: 'ti-file-code', extensionId: 'codex_viewer', href: '/extensions/codex_viewer' },
				{ label: 'Market Place', icon: 'ti-building-store', extensionId: 'market_place', href: '/extensions/market_place' },
			],
		},
	],
};

const developerSidebar: SidebarConfig = {
	defaultPath: '/extensions/codex_viewer',
	categories: [
		{
			id: 'system',
			label: 'SYSTEM',
			items: [
				{ label: 'Codex Viewer', icon: 'ti-file-code', extensionId: 'codex_viewer', href: '/extensions/codex_viewer', isDefault: true },
				{ label: 'Market Place', icon: 'ti-building-store', extensionId: 'market_place', href: '/extensions/market_place' },
				{ label: 'Package Manager', icon: 'ti-package', extensionId: 'package_manager', href: '/extensions/package_manager' },
				{ label: 'System Info', icon: 'ti-server', extensionId: 'system_info', href: '/extensions/system_info' },
				{ label: 'Task Monitor', icon: 'ti-activity', extensionId: 'task_monitor', href: '/extensions/task_monitor' },
				{ label: 'ERD Explorer', icon: 'ti-topology-star-3', extensionId: 'erd_explorer', href: '/extensions/erd_explorer' },
				{ label: 'Demo Simulator', icon: 'ti-database', extensionId: 'public_dashboard', href: '/extensions/public_dashboard?mode=demo' },
			],
		},
	],
};

const sidebarConfigs: Record<UserRole, SidebarConfig> = {
	member: memberSidebar,
	admin: adminSidebar,
	developer: developerSidebar,
};

/**
 * Returns the sidebar configuration for the given role.
 * Falls back to member if role is unrecognized.
 */
export function getSidebarConfig(role: UserRole): SidebarConfig {
	return sidebarConfigs[role] ?? memberSidebar;
}

/**
 * Determines the effective role from a list of user profiles.
 * Priority: developer > admin > member (most privileged wins for sidebar display).
 */
export function resolveRole(profiles: string[]): UserRole {
	if (profiles.includes('developer')) return 'developer';
	if (profiles.includes('admin')) return 'admin';
	return 'member';
}
