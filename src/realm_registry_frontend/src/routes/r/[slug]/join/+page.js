import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import { isAuthenticated } from '$lib/auth.js';

/** Require portal II session before loading the realm join iframe. */
export async function load({ url }) {
	if (!browser) return {};

	const match = url.pathname.match(/^\/r\/([^/]+)\/join\/?$/);
	const slug = match?.[1];
	if (!slug) return {};

	if (!(await isAuthenticated())) {
		const returnTo = `/r/${encodeURIComponent(slug)}/join`;
		throw redirect(302, `/join?returnTo=${encodeURIComponent(returnTo)}`);
	}

	return {};
}
