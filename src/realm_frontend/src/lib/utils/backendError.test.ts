import { describe, expect, it } from 'vitest';
import {
	isAssignableJoinError,
	localizeBackendError,
	parseBackendError,
} from './backendError';

describe('parseBackendError', () => {
	it('reads JSON error_code', () => {
		expect(
			parseBackendError({
				success: false,
				error_code: 'anonymous_cannot_join',
				error: 'Anonymous principal cannot join a realm — sign in first',
			}),
		).toEqual({
			code: 'anonymous_cannot_join',
			message: 'Anonymous principal cannot join a realm — sign in first',
		});
	});

	it('reads tagged Candid error text', () => {
		expect(
			parseBackendError(
				'[invalid_invite] Invalid or expired invitation code',
			),
		).toEqual({
			code: 'invalid_invite',
			message: 'Invalid or expired invitation code',
		});
	});

	it('reads JSON string envelopes', () => {
		expect(
			parseBackendError(
				JSON.stringify({
					error_code: 'email_code_incorrect',
					error: 'Incorrect verification code',
				}),
			),
		).toEqual({
			code: 'email_code_incorrect',
			message: 'Incorrect verification code',
		});
	});

	it('leaves untagged English alone', () => {
		expect(parseBackendError('Department name is required')).toEqual({
			code: null,
			message: 'Department name is required',
		});
	});
});

describe('localizeBackendError', () => {
	const catalog: Record<string, string> = {
		'errors.anonymous_cannot_join': 'You must sign in before joining this realm.',
		'errors.generic': 'Something went wrong. Please try again.',
	};
	const translate = (key: string) => catalog[key] ?? key;

	it('maps error_code through the catalog', () => {
		expect(
			localizeBackendError(
				'[anonymous_cannot_join] Anonymous principal cannot join a realm — sign in first',
				translate,
			),
		).toBe('You must sign in before joining this realm.');
	});

	it('falls back to the English body when the key is missing', () => {
		expect(
			localizeBackendError('[invite_required] Registration requires an invitation code.', translate),
		).toBe('Registration requires an invitation code.');
	});
});

describe('isAssignableJoinError', () => {
	it('recognizes coordinator_only by code', () => {
		expect(
			isAssignableJoinError(
				'[coordinator_only] This realm is coordinator-only. Please join through a quarter.',
			),
		).toBe(true);
	});

	it('still matches untagged English for older canisters', () => {
		expect(
			isAssignableJoinError('This quarter is still setting up. Please try again in a moment.'),
		).toBe(true);
	});

	it('ignores unrelated errors', () => {
		expect(isAssignableJoinError('[invalid_invite] Invalid or expired invitation code')).toBe(
			false,
		);
	});
});
