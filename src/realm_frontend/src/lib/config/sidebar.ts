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
	/** Codex extension overrides: base system extension id -> replacement id. */
	extensionOverrides?: Record<string, string>;
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
