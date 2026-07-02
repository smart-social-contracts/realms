import { browser } from '$app/environment';

/** Realm join iframe handles its own II login. */
export async function load() {
	if (!browser) return {};
	return {};
}
