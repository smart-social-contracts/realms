/**
 * Dynamic sidebar configuration built from installed extension manifests.
 *
 * The sidebar is populated at runtime by querying the backend for all
 * installed extensions, filtering by the user's active profiles, and
 * grouping by the manifest's `categories` field.
 */

export interface SidebarNavItem {
	label: string;
	icon: string;
	extensionId: string;
	href: string;
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

export interface ExtensionManifest {
	name: string;
	version?: string;
	profiles?: string[];
	categories?: string[];
	show_in_sidebar?: boolean;
	sidebar_label?: Record<string, string>;
	icon?: string;
	is_default?: boolean;
	[key: string]: unknown;
}

const categoryMeta: Record<string, { order: number; label: Record<string, string> }> = {
	profile:        { order: 0, label: { en: 'My Realm' } },
	administration: { order: 1, label: { en: 'Administration' } },
	governance:     { order: 2, label: { en: 'Governance' } },
	land_territory: { order: 3, label: { en: 'Land & Territory' } },
	finances:       { order: 4, label: { en: 'Finances' } },
	intelligence:   { order: 5, label: { en: 'AI' } },
	developer:      { order: 6, label: { en: 'Developer' } },
	home:           { order: 7, label: { en: 'Home' } },
	other:          { order: 99, label: { en: 'Other' } },
};

const fallbackDefaultPaths: Record<string, string> = {
	admin: '/extensions/admin_dashboard',
	member: '/extensions/member_dashboard',
	developer: '/extensions/codex_viewer',
};

function titleCase(s: string): string {
	return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function getCategoryLabel(catId: string, locale: string): string {
	const meta = categoryMeta[catId];
	if (meta) return meta.label[locale] ?? meta.label['en'] ?? titleCase(catId);
	return titleCase(catId);
}

function getCategoryOrder(catId: string): number {
	return categoryMeta[catId]?.order ?? 50;
}

/**
 * Build a SidebarConfig from extension manifests filtered by user profiles.
 */
export function buildSidebar(
	manifests: Record<string, ExtensionManifest>,
	userProfiles: string[],
	locale: string = 'en',
): SidebarConfig {
	const visible = Object.values(manifests).filter((m) => {
		if (!m.show_in_sidebar) return false;
		if (!m.profiles || m.profiles.length === 0) return true;
		return m.profiles.some((p) => userProfiles.includes(p));
	});

	const grouped: Record<string, ExtensionManifest[]> = {};
	for (const m of visible) {
		const catId = m.categories?.[0] ?? 'other';
		(grouped[catId] ??= []).push(m);
	}

	const categories: SidebarCategory[] = Object.entries(grouped)
		.map(([catId, items]) => ({
			id: catId,
			label: getCategoryLabel(catId, locale),
			order: getCategoryOrder(catId),
			items: items
				.map((m) => ({
					label: m.sidebar_label?.[locale] ?? m.sidebar_label?.['en'] ?? titleCase(m.name),
					icon: `ti-${m.icon ?? 'layout-dashboard'}`,
					extensionId: m.name,
					href: `/extensions/${m.name}`,
				}))
				.sort((a, b) => a.label.localeCompare(b.label)),
		}))
		.sort((a, b) => a.order - b.order)
		.map(({ id, label, items }) => ({ id, label, items }));

	const defaultManifest = Object.values(manifests).find(
		(m) =>
			m.is_default &&
			m.show_in_sidebar &&
			((!m.profiles || m.profiles.length === 0) || m.profiles.some((p) => userProfiles.includes(p))),
	);
	let defaultPath = defaultManifest ? `/extensions/${defaultManifest.name}` : '';
	if (!defaultPath) {
		for (const role of ['developer', 'admin', 'member']) {
			if (userProfiles.includes(role) && fallbackDefaultPaths[role]) {
				defaultPath = fallbackDefaultPaths[role];
				break;
			}
		}
	}

	return { categories, defaultPath: defaultPath || '/extensions/member_dashboard' };
}

/**
 * Determines the effective role from a list of user profiles.
 * Kept for backward compatibility with components that need a single role string.
 */
export function resolveRole(profiles: string[]): string {
	if (profiles.includes('developer')) return 'developer';
	if (profiles.includes('admin')) return 'admin';
	return 'member';
}
