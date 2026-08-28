/**
 * Guest vs member sidebar chrome.
 *
 * Guest = signed-in principal who is not a realm member (no member/admin
 * profile). Do not treat `$isAuthenticated` or optimistic `hasJoined()` as
 * membership — that is why guests were seeing ME.
 */

export const MEMBER_SIDEBAR_PROFILES = ['member', 'admin'] as const;
export const REALM_MANAGEMENT_CATEGORY = 'realm_management';

export function isRealmMember(profiles: readonly string[] | null | undefined): boolean {
	if (!Array.isArray(profiles)) return false;
	return profiles.some((profile) => profile === 'member' || profile === 'admin');
}

/** ME (Account / Messages / Settings) is member chrome, not auth chrome. */
export function shouldShowMeSection(
	isAuthenticated: boolean,
	profiles: readonly string[] | null | undefined,
): boolean {
	return Boolean(isAuthenticated) && isRealmMember(profiles);
}

/** REALM MANAGEMENT (System and any siblings) is member-only. */
export function visibleSidebarCategories<T extends { id: string }>(
	categories: readonly T[] | null | undefined,
	profiles: readonly string[] | null | undefined,
): T[] {
	if (!Array.isArray(categories)) return [];
	if (isRealmMember(profiles)) return [...categories];
	return categories.filter((category) => category.id !== REALM_MANAGEMENT_CATEGORY);
}
