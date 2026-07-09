/** @type {import('@sveltejs/kit').HandleClientError} */
export function handleError({ error }) {
	const msg = error instanceof Error ? error.message : String(error ?? '');

	// Chrome reports net::ERR_NETWORK_CHANGED when the interface switches mid-fetch
	// (VPN, Wi‑Fi handoff, sleep/wake). SvelteKit surfaces that as a failed dynamic
	// import of a route/chunk — scary but almost always fixed by one hard refresh.
	if (
		msg.includes('Failed to fetch dynamically imported module') ||
		msg.includes('Importing a module script failed') ||
		msg.includes('error loading dynamically imported module')
	) {
		return {
			message:
				'Loading was interrupted by a network change or an in-progress app update. Hard-refresh this page (Ctrl+Shift+R or Cmd+Shift+R) — that almost always fixes it.'
		};
	}

	return {
		message: msg || 'An unexpected error occurred.'
	};
}
