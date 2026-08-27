/**
 * Drop the static `#app-splash` globe from `app.html`.
 *
 * Root layout `onMount` used to be the only caller. If hydration throws
 * (i18n locale race, chunk error), `onMount` never runs and the globe
 * spins forever with an empty `document.body.innerText`. Call this from
 * the layout module body as well as `onMount`.
 */
export function dismissAppSplash(root: { getElementById?: typeof document.getElementById } | null = typeof document === 'undefined' ? null : document): boolean {
	const el = root?.getElementById?.('app-splash');
	if (!el) return false;
	el.remove();
	return true;
}
