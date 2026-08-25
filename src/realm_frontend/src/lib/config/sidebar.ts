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
	extensionId?: string;
	/** Backend get_sidebar uses snake_case. */
	extension_id?: string;
	href: string;
	tooltip?: string;
}

/** Slim row from realm_backend.get_sidebar_manifests(). */
export interface SidebarManifest {
	id: string;
	name?: string;
	sidebar_label?: string | Record<string, string>;
	is_default?: boolean;
	show_in_sidebar?: boolean;
	categories?: string[];
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
	/** Same get_sidebar_manifests() list the sidebar paints MY REALM from. */
	manifests?: SidebarManifest[];
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
