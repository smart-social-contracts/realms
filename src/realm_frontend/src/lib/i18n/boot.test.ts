import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { locale } from 'svelte-i18n';
import { bootI18n, formatBootedMessage } from './boot';

describe('i18n boot gate', () => {
	it('seeds English in the same turn so $_() cannot throw during hydration', () => {
		expect(bootI18n('en')).toBe('en');
		expect(get(locale)).toBe('en');
		expect(() => formatBootedMessage('common.loading')).not.toThrow();
		expect(formatBootedMessage('common.loading')).toBe('Loading...');
		expect(formatBootedMessage('setup.loading')).toBe('Loading setup…');
	});

	it('re-seeding is idempotent and keeps locale usable', () => {
		bootI18n('en');
		bootI18n('en');
		expect(get(locale)).toBe('en');
		expect(formatBootedMessage('common.home')).toBe('Home');
	});
});
