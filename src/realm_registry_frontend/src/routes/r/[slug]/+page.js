import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import { isAuthenticated } from '$lib/auth.js';

/** Require portal II session before embedding a realm iframe. */
export async function load({ url }) {
	if (!browser) return {};

	const match = url.pathname.match(/^\/r\/([^/]+)/);
	const slug = match?.[1];
	if (!slug) return {};

	if (!(await isAuthenticated())) {
		const returnTo = `/r/${encodeURIComponent(slug)}`;
		throw redirect(302, `/join?returnTo=${encodeURIComponent(returnTo)}`);
	}

	return {};
}
