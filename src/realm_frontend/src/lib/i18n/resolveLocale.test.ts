import { describe, expect, it } from 'vitest';
import {
	coerceRealmLanguages,
	normalizeLanguages,
	resolveUiLocale
} from './realmLocales';

describe('normalizeLanguages', () => {
	it('requires primary to be in the enabled list', () => {
		expect(normalizeLanguages(['en', 'ca-valencia'], 'fr')).toEqual({
			error: 'primary_language must be one of the enabled languages'
		});
	});

	it('accepts ca-valencia as the only Valencian catalog id', () => {
		expect(normalizeLanguages(['en', 'ca-valencia'], 'ca-valencia')).toEqual({
			languages: ['en', 'ca-valencia'],
			primary: 'ca-valencia'
		});
	});

	it('rejects a second Catalan catalog id', () => {
		expect(normalizeLanguages(['en', 'ca'], 'en')).toEqual({
			error: 'unsupported locale: ca'
		});
	});
});

describe('resolveUiLocale', () => {
	it('uses the user override when it is in the realm list', () => {
		expect(resolveUiLocale('ca-valencia', ['en', 'ca-valencia'], 'en')).toBe('ca-valencia');
	});

	it('falls back to realm primary when the user override is empty', () => {
		expect(resolveUiLocale('', ['en', 'ca-valencia'], 'ca-valencia')).toBe('ca-valencia');
		expect(resolveUiLocale(null, ['es'], 'es')).toBe('es');
	});

	it('ignores a user override that is not in the realm list', () => {
		expect(resolveUiLocale('de', ['en'], 'en')).toBe('en');
	});

	it('falls back to en when primary is missing or not in the catalog', () => {
		expect(resolveUiLocale('', [], 'de')).toBe('en');
		expect(resolveUiLocale('', null, null)).toBe('en');
	});
});

describe('coerceRealmLanguages', () => {
	it('defaults missing config to English', () => {
		expect(coerceRealmLanguages(undefined, undefined)).toEqual({
			languages: ['en'],
			primary: 'en'
		});
	});
});
