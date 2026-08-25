/** Same-origin extension route used by `extensions/[id]/+page.svelte`. */
export function extensionHref(id: string): string {
	return `/extensions/${id}`;
}

export interface SidebarManifestRow {
	id?: string;
	sidebar_label?: string | Record<string, string>;
	is_default?: boolean;
}

export interface SidebarHomeInput {
	manifests?: SidebarManifestRow[] | null;
	welcomeItems?: Array<{
		extensionId?: string;
		extension_id?: string;
		href?: string;
		label?: string;
	}> | null;
	locale?: string;
}

function sidebarLabelText(
	label: string | Record<string, string> | undefined,
	locale = 'en',
): string {
	if (typeof label === 'string') return label.trim();
	if (!label || typeof label !== 'object') return '';
	const localized = label[locale] || label.en || Object.values(label)[0];
	return typeof localized === 'string' ? localized.trim() : '';
}

function navItemExtensionId(item: {
	extensionId?: string;
	extension_id?: string;
	href?: string;
}): string {
	if (typeof item.extensionId === 'string' && item.extensionId) return item.extensionId;
	if (typeof item.extension_id === 'string' && item.extension_id) return item.extension_id;
	const href = item.href || '';
	const match = href.match(/^\/extensions\/([^/?#]+)/);
	return match?.[1] ?? '';
}

function isMyDashboardLabel(label: string): boolean {
	return label.toLowerCase() === 'my dashboard';
}

/**
 * Host-only: pick the MY REALM → My Dashboard row from get_sidebar_manifests()
 * (or the already-painted welcome list) and return `/extensions/[id]`.
 * Extensions must not name this target.
 */
export function resolveMemberHomeHref(input: SidebarHomeInput | null | undefined): string {
	const locale = input?.locale || 'en';
	const manifests = input?.manifests ?? [];
	const dashboard = manifests.find((row) => {
		if (!row?.id) return false;
		if (row.is_default) return true;
		return isMyDashboardLabel(sidebarLabelText(row.sidebar_label, locale));
	});
	if (dashboard?.id) return extensionHref(dashboard.id);

	const welcome = input?.welcomeItems ?? [];
	const labeled = welcome.find((item) => isMyDashboardLabel(item.label || ''));
	const firstRealm = labeled || welcome[0];
	const firstId = firstRealm ? navItemExtensionId(firstRealm) : '';
	if (firstId) return extensionHref(firstId);
	if (firstRealm?.href?.startsWith('/')) return firstRealm.href;
	return '/';
}
