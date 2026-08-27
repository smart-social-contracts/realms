import { writable } from 'svelte/store';
import { applyResolvedLocale } from '$lib/i18n';

/** Personal locale override from user private_data. Empty = use realm primary. */
export const userLocale = writable('');

export function localeFromPrivateData(privateData: unknown): string {
	if (!privateData || typeof privateData !== 'object' || Array.isArray(privateData)) {
		return '';
	}
	const value = (privateData as { locale?: unknown }).locale;
	return typeof value === 'string' ? value.trim() : '';
}

export function applyStoredUserLocale(
	locale: string,
	languages: readonly string[] = ['en'],
	primaryLanguage = 'en'
): void {
	userLocale.set(locale);
	applyResolvedLocale({
		userLocale: locale,
		languages,
		primaryLanguage
	});
}

export async function refreshUserLocale(actor: {
	get_my_user_status?: () => Promise<any>;
}): Promise<void> {
	if (!actor?.get_my_user_status) return;
	try {
		const response = await actor.get_my_user_status();
		const raw = response?.data?.userGet?.private_data;
		let parsed: unknown = {};
		if (typeof raw === 'string' && raw) {
			parsed = JSON.parse(raw);
		} else if (raw && typeof raw === 'object') {
			parsed = raw;
		}
		const locale = localeFromPrivateData(parsed);
		userLocale.set(locale);
		const { get } = await import('svelte/store');
		const { realmInfo } = await import('$lib/stores/realmInfo');
		const realm = get(realmInfo);
		applyResolvedLocale({
			userLocale: locale,
			languages: realm.languages,
			primaryLanguage: realm.primaryLanguage
		});
	} catch {
		// Anonymous or unjoined callers have no personal locale.
	}
}
