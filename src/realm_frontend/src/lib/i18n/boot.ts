import { addMessages, init, locale, _ } from 'svelte-i18n';
import { get } from 'svelte/store';
import en from './locales/en.json';

/**
 * Seed English and set the locale in the same turn as import.
 *
 * `register(() => import(...))` loaders are async. svelte-i18n leaves
 * `locale` as `null` until that fetch resolves, and `$_()` then throws:
 *   [svelte-i18n] Cannot format a message without first setting the initial locale.
 * That exception aborts SvelteKit start() — root `onMount` never runs, so
 * `#app-splash` (the loading globe) stays up on every remount/reload.
 */
export function bootI18n(initialLocale = 'en'): string {
	addMessages('en', en);
	const next = initialLocale || 'en';
	locale.set(next);
	init({
		fallbackLocale: 'en',
		initialLocale: next
	});
	if (get(locale) == null) {
		locale.set('en');
	}
	return get(locale) || 'en';
}

/** Format a message after `bootI18n()` — must not throw. */
export function formatBootedMessage(id: string): string {
	return get(_)(id);
}
