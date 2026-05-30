/**
 * Sidebar configuration types and constants.
 *
 * The sidebar is resolved by the backend (get_sidebar endpoint) which merges
 * extension manifests, default category ordering, database overrides, and
 * department visibility rules. The frontend simply renders the result.
 */

export interface SidebarNavItem {
	label: string;
	icon: string;
	extensionId: string;
	href: string;
	tooltip?: string;
}

export interface SidebarCategory {
	id: string;
	label: string;
	items: SidebarNavItem[];
}

export interface SidebarConfig {
	welcomeItems: SidebarNavItem[];
	mundusItems: SidebarNavItem[];
	categories: SidebarCategory[];
	defaultPath: string;
}

export interface TopUtilityItem {
	label: string;
	icon: string;
	href: string;
	tooltip?: string;
}

export const topUtilityItems: TopUtilityItem[] = [
	{ label: 'Account', icon: 'ti-user-circle', href: '/identities', tooltip: 'Manage your identity and account settings' },
	{ label: 'Messages', icon: 'ti-mail', href: '/messages', tooltip: 'View and send messages' },
	{ label: 'Settings', icon: 'ti-settings', href: '/settings', tooltip: 'Configure your preferences' },
];

export const SECTION_HEADER_ME = 'ME';
export const SECTION_HEADER_REALM = 'MY REALM';
export const SECTION_HEADER_MUNDUS = 'MY MUNDUS';

/**
 * Determines the effective role from a list of user profiles.
 * Kept for backward compatibility with components that need a single role string.
 */
export function resolveRole(profiles: string[]): string {
	if (profiles.includes('developer')) return 'developer';
	if (profiles.includes('admin')) return 'admin';
	return 'member';
}
