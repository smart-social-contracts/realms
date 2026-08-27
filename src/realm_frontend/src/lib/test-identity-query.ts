/** Query keys that select / keep a bypass identity across portal redirects. */
export const TEST_IDENTITY_QUERY_KEYS = ['ti', 'skip_ii', 'test_mode'] as const;

const TEST_IDENTITY_MAX_INDEX = 0xffffffff;

function asSearchParams(search: string | URLSearchParams | null | undefined): URLSearchParams {
	if (search instanceof URLSearchParams) return new URLSearchParams(search);
	const raw = search == null ? '' : String(search);
	return new URLSearchParams(raw.startsWith('?') ? raw.slice(1) : raw);
}

function isTruthyQueryFlag(value: string | null): boolean {
	if (value == null || value === '') return false;
	const normalized = String(value).trim().toLowerCase();
	return normalized === '1' || normalized === 'true' || normalized === 'yes';
}

function normalizeIndex(index: number): number {
	const parsed = Math.floor(Number(index));
	if (!Number.isFinite(parsed)) return 0;
	return Math.max(0, Math.min(TEST_IDENTITY_MAX_INDEX, parsed));
}

export type TestIdentitySearch = {
	identityIndex: number | null;
	skipII: boolean;
	testMode: boolean;
};

/**
 * Parse `?ti=N` (0-based identity index) plus optional `skip_ii` / `test_mode`.
 * `ti=0` is Identity 1 and must not be treated as missing.
 */
export function parseTestIdentitySearch(
	search: string | URLSearchParams | null | undefined
): TestIdentitySearch {
	const params = asSearchParams(search);
	const tiRaw = params.get('ti');
	let identityIndex: number | null = null;
	if (tiRaw != null && tiRaw !== '') {
		const parsed = Number(tiRaw);
		if (Number.isFinite(parsed)) {
			identityIndex = normalizeIndex(parsed);
		}
	}
	return {
		identityIndex,
		skipII: isTruthyQueryFlag(params.get('skip_ii')),
		testMode: isTruthyQueryFlag(params.get('test_mode'))
	};
}

/**
 * Set `ti` on an existing query string without dropping invite / portal / skip_ii.
 */
export function applyTestIdentitySearch(
	search: string | URLSearchParams | null | undefined,
	{ identityIndex }: { identityIndex?: number | null } = {}
): string {
	const params = asSearchParams(search);
	if (identityIndex != null && Number.isFinite(Number(identityIndex))) {
		params.set('ti', String(normalizeIndex(identityIndex)));
	}
	return params.toString();
}

/**
 * Copy `ti` / `skip_ii` / `test_mode` from the current URL onto a goto href.
 */
export function hrefWithPreservedTestIdentityParams(
	currentSearch: string | URLSearchParams | null | undefined,
	href: string
): string {
	const target = new URL(String(href || '/'), 'https://realm.invalid');
	const current = asSearchParams(currentSearch);
	for (const key of TEST_IDENTITY_QUERY_KEYS) {
		if (current.has(key) && !target.searchParams.has(key)) {
			target.searchParams.set(key, current.get(key) ?? '');
		}
	}
	const qs = target.searchParams.toString();
	return `${target.pathname}${qs ? `?${qs}` : ''}${target.hash}`;
}
