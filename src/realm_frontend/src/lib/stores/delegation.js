import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';

const STORAGE_KEY = 'realm_acting_on_behalf_of';

function readStored() {
	if (!browser) return null;
	try {
		return sessionStorage.getItem(STORAGE_KEY) || null;
	} catch {
		return null;
	}
}

/** Grantor principal when acting on behalf of another user; null = self. */
export const actingOnBehalfOf = writable(readStored());

/** Cached delegation lists from list_delegations_json. */
export const delegationsAsDelegate = writable([]);
export const delegationsAsGrantor = writable([]);
export const pendingDelegations = writable([]);

actingOnBehalfOf.subscribe((value) => {
	if (!browser) return;
	try {
		if (value) sessionStorage.setItem(STORAGE_KEY, value);
		else sessionStorage.removeItem(STORAGE_KEY);
	} catch {
		/* ignore */
	}
});

export function clearActingContext() {
	actingOnBehalfOf.set(null);
}

export function setActingOnBehalfOf(grantorPrincipal) {
	const v = (grantorPrincipal || '').trim();
	actingOnBehalfOf.set(v || null);
}

export function withDelegationArgs(args = {}) {
	const grantor = get(actingOnBehalfOf);
	if (grantor) {
		return { ...args, on_behalf_of: grantor };
	}
	return args;
}

export function withDelegationJson(args = {}) {
	return JSON.stringify(withDelegationArgs(args));
}

export async function loadDelegations(backend) {
	if (!backend?.list_delegations_json) return;
	try {
		const raw = await backend.list_delegations_json();
		const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
		if (!parsed?.success) return;
		const data = parsed.data || {};
		delegationsAsDelegate.set(data.as_delegate || []);
		delegationsAsGrantor.set(data.as_grantor || []);
		pendingDelegations.set(data.pending_inbox || []);
	} catch (e) {
		console.warn('Failed to load delegations:', e);
	}
}

/** Active delegations the caller may act under (status active, not expired). */
export function activeDelegationsAsDelegate(list) {
	const now = Math.floor(Date.now() / 1000);
	return (list || []).filter(
		(d) => d.status === 'active' && (!d.expires_at || d.expires_at > now)
	);
}
