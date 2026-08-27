import { describe, expect, it } from 'vitest';
import {
	applyTestIdentitySearch,
	hrefWithPreservedTestIdentityParams,
	parseTestIdentitySearch
} from './test-identity-query';

describe('parseTestIdentitySearch', () => {
	it('reads 0-based ti including Identity 1 (ti=0)', () => {
		expect(parseTestIdentitySearch('?ti=0').identityIndex).toBe(0);
		expect(parseTestIdentitySearch('ti=1').identityIndex).toBe(1);
		expect(parseTestIdentitySearch(new URLSearchParams('ti=1')).identityIndex).toBe(1);
	});

	it('does not treat a missing ti as index 0', () => {
		expect(parseTestIdentitySearch('').identityIndex).toBeNull();
		expect(parseTestIdentitySearch('?invite=abc').identityIndex).toBeNull();
	});

	it('parses skip_ii and test_mode flags', () => {
		expect(parseTestIdentitySearch('?ti=1&skip_ii=true&test_mode=1')).toEqual({
			identityIndex: 1,
			skipII: true,
			testMode: true
		});
		expect(parseTestIdentitySearch('?skip_ii=false&test_mode=no')).toEqual({
			identityIndex: null,
			skipII: false,
			testMode: false
		});
	});
});

describe('applyTestIdentitySearch', () => {
	it('writes ti=0 instead of dropping the param', () => {
		expect(applyTestIdentitySearch('', { identityIndex: 0 })).toBe('ti=0');
		expect(applyTestIdentitySearch('?invite=abc', { identityIndex: 1 })).toBe('invite=abc&ti=1');
	});

	it('keeps skip_ii / test_mode / portal when setting ti', () => {
		expect(
			applyTestIdentitySearch('?portal=1&slug=x&skip_ii=true&test_mode=true', { identityIndex: 1 })
		).toBe('portal=1&slug=x&skip_ii=true&test_mode=true&ti=1');
	});
});

describe('hrefWithPreservedTestIdentityParams', () => {
	it('keeps ti=0 through a home-page redirect', () => {
		expect(hrefWithPreservedTestIdentityParams('?ti=0', '/extensions/public_dashboard')).toBe(
			'/extensions/public_dashboard?ti=0'
		);
	});

	it('keeps ti / skip_ii / test_mode through the first continue target', () => {
		expect(
			hrefWithPreservedTestIdentityParams('?ti=1&skip_ii=true&test_mode=true', '/join')
		).toBe('/join?ti=1&skip_ii=true&test_mode=true');
	});

	it('does not overwrite an explicit ti already on the href', () => {
		expect(hrefWithPreservedTestIdentityParams('?ti=0', '/join?ti=1')).toBe('/join?ti=1');
	});
});
