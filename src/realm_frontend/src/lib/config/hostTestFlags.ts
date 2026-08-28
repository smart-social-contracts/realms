export type DemoNoticeBodies = Record<string, string>;

export const CUSTOM_TOKEN_CHOICE_ID = 'custom';

export const NOTICE_LOCALE_SLOTS = [
	'en',
	'es',
	'de',
	'fr',
	'it',
	'zh-CN',
	'ca-valencia'
] as const;

export const REALMS_TOKEN_ID = 'REALMS';

export function defaultDisableMonetaryTokens(network?: string | null): boolean {
	const n = (network || '').trim().toLowerCase();
	return n === 'staging' || n === 'demo' || n === 'test';
}

export function defaultDemoNotice(network?: string | null): boolean {
	const n = (network || '').trim().toLowerCase();
	return n === 'staging' || n === 'demo';
}

export function resolveDisableMonetaryTokens(
	explicit: boolean | null | undefined,
	network?: string | null
): boolean {
	if (typeof explicit === 'boolean') return explicit;
	return defaultDisableMonetaryTokens(network);
}

export function resolveDemoNoticeEnabled(
	explicit: boolean | null | undefined,
	network?: string | null
): boolean {
	if (typeof explicit === 'boolean') return explicit;
	return defaultDemoNotice(network);
}

/** Join shows the notice unless skip_terms. II bypass does not skip it. */
export function shouldShowJoinNotice(
	demoNotice: boolean,
	skipTerms: boolean
): boolean {
	return demoNotice && !skipTerms;
}

export function isMonetaryTokenChoice(choiceId: string): boolean {
	return (choiceId || '').trim().toUpperCase() !== REALMS_TOKEN_ID;
}

export function isTokenChoiceSelectable(
	choiceId: string,
	monetaryDisabled: boolean
): boolean {
	if (!monetaryDisabled) return true;
	return !isMonetaryTokenChoice(choiceId);
}

export function monetaryUnavailableLabel(locale: string): string {
	const id = (locale || '').trim().toLowerCase();
	if (id === 'es' || id.startsWith('es-')) {
		return 'No disponible en esta demo';
	}
	return 'Not available in this demo';
}

export function resolveDemoNoticeView(
	bodies: DemoNoticeBodies | null | undefined,
	primaryLanguage: string
): {
	english: string;
	primary: string;
	primaryLanguage: string;
	showPrimary: boolean;
} {
	const map = bodies && typeof bodies === 'object' ? bodies : {};
	const english = String(map.en || '').trim();
	const primary = (primaryLanguage || 'en').trim() || 'en';
	const primaryBody = primary === 'en' ? '' : String(map[primary] || '').trim();
	return {
		english,
		primary: primaryBody,
		primaryLanguage: primary,
		showPrimary: Boolean(primaryBody) && primary !== 'en'
	};
}

export function catalogChoiceFromLedger(input: {
	symbol?: string;
	token_canister_id?: string;
	match?: { id?: string } | undefined;
}): string {
	if (input.match?.id) return input.match.id;
	const symbol = (input.symbol || '').trim();
	if (symbol && symbol.toUpperCase() === REALMS_TOKEN_ID) return REALMS_TOKEN_ID;
	if (input.token_canister_id || symbol) return CUSTOM_TOKEN_CHOICE_ID;
	return REALMS_TOKEN_ID;
}
