/**
 * Federated membership probe (issue #156).
 *
 * There is no central principal→quarter index. A returning user's quarter is
 * recovered by probing known canisters with get_my_user_status(). Shared by
 * the profiles store (login auto-route) and /join (prevent accidental
 * double-registration).
 */

export type MembershipHit = {
	canisterId: string;
	isCapital: boolean;
	response: any;
	profiles: string[];
};

export type ProbeResult = {
	/** First hit (preferred: valid cache, else first federated match). */
	primary: MembershipHit | null;
	/** All quarters where the caller has profiles. */
	hits: MembershipHit[];
	capitalId: string;
};

export function hasMembership(r: any): boolean {
	return !!(
		r &&
		r.success &&
		r.data &&
		r.data.userGet &&
		(r.data.userGet.profiles || []).length > 0
	);
}

function profilesOf(r: any): string[] {
	return (r?.data?.userGet?.profiles || []) as string[];
}

/**
 * Choose which membership to activate when several exist.
 * Prefers a still-valid localStorage cache; otherwise the first hit.
 */
export function pickPrimaryHit(
	hits: MembershipHit[],
	cachedCanisterId: string = ''
): MembershipHit | null {
	if (!hits.length) return null;
	if (cachedCanisterId) {
		const cached = hits.find((h) => h.canisterId === cachedCanisterId);
		if (cached) return cached;
	}
	return hits[0];
}

/**
 * Activate a membership hit for this browser session (actor + optional cache).
 */
export async function activateMembership(
	hit: MembershipHit,
	capitalId: string,
	options?: { cache?: boolean }
): Promise<void> {
	const cache = options?.cache !== false;
	// @ts-ignore
	const { setActiveQuarter } = await import('$lib/canisters');
	// @ts-ignore
	const { activeQuarterId } = await import('$lib/stores/quarters');

	const cid = hit.canisterId;
	if (cid && !hit.isCapital && cid !== capitalId) {
		activeQuarterId.set(cid);
		await setActiveQuarter(cid);
		if (cache && typeof localStorage !== 'undefined') {
			localStorage.setItem('home_quarter', cid);
		}
	} else {
		activeQuarterId.set(null);
		await setActiveQuarter(null);
		if (cache && typeof localStorage !== 'undefined') {
			localStorage.removeItem('home_quarter');
		}
	}
}

/**
 * Probe capital + every quarter from get_join_targets for the caller's membership.
 * Prefers a valid localStorage home_quarter cache when it still recognizes the caller.
 */
export async function probeFederatedMembership(options?: {
	activate?: boolean;
	cache?: boolean;
}): Promise<ProbeResult> {
	const activate = options?.activate !== false;
	const cache = options?.cache !== false;

	// @ts-ignore
	const { backend, createQuarterActor } = await import('$lib/canisters');

	if (!backend || typeof backend.get_my_user_status !== 'function') {
		throw new Error('Backend canister is not properly initialized');
	}

	const hits: MembershipHit[] = [];
	let capitalId = '';
	let candidates: { canister_id: string; is_capital?: boolean }[] = [];

	try {
		const raw = await backend.get_join_targets();
		const targets = typeof raw === 'string' ? JSON.parse(raw) : raw;
		capitalId = targets?.capital_id || '';
		candidates = (targets?.quarters || []).filter((q: any) => q && q.canister_id);
		if (capitalId && !candidates.some((q) => q.canister_id === capitalId)) {
			candidates.unshift({ canister_id: capitalId, is_capital: true });
		}
	} catch (e) {
		console.warn('get_join_targets failed during membership probe:', e);
		candidates = [{ canister_id: '', is_capital: true }];
	}

	const cached =
		typeof localStorage !== 'undefined' ? localStorage.getItem('home_quarter') || '' : '';

	// Prefer probing the cached quarter first so we short-circuit when possible.
	const ordered = [...candidates];
	if (cached) {
		const idx = ordered.findIndex((q) => q.canister_id === cached);
		if (idx > 0) {
			const [pref] = ordered.splice(idx, 1);
			ordered.unshift(pref);
		} else if (idx < 0) {
			ordered.unshift({ canister_id: cached, is_capital: false });
		}
	}

	for (const q of ordered) {
		const cid = q.canister_id || '';
		const isCapital = !!(q.is_capital || (capitalId && cid === capitalId) || !cid);
		try {
			const actor =
				!cid || cid === capitalId ? backend : await createQuarterActor(cid);
			const r = await actor.get_my_user_status();
			if (hasMembership(r)) {
				hits.push({
					canisterId: cid || capitalId,
					isCapital,
					response: r,
					profiles: profilesOf(r),
				});
			}
		} catch (qe) {
			console.warn('Quarter membership probe failed for', cid || '(capital)', qe);
		}
	}

	const primary = pickPrimaryHit(hits, cached);

	if (primary && activate) {
		await activateMembership(primary, capitalId, { cache });
	}

	return { primary, hits, capitalId };
}
