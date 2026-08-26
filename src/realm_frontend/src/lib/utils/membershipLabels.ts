/** Display helpers for Cedar profiles vs department membership in host chrome. */

export const EMPTY_MEMBERSHIP = '—';
export const GUEST_PROFILE_LABEL = 'Guest';

export function titleCaseProfile(name: string): string {
	return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Profile row value: title-cased, comma-separated; Guest when empty. */
export function formatProfileValues(
	profiles: string[] | null | undefined,
	guest: string = GUEST_PROFILE_LABEL
): string {
	if (!profiles || profiles.length === 0) return guest;
	return profiles.map(titleCaseProfile).join(', ');
}

/** Department row value: names as stored, comma-separated; em dash when empty. */
export function formatDepartmentValues(
	departments: string[] | null | undefined,
	empty: string = EMPTY_MEMBERSHIP
): string {
	if (!departments || departments.length === 0) return empty;
	return departments.join(', ');
}
