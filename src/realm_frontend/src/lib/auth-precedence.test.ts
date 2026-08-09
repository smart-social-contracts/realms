import { describe, expect, it } from 'vitest';
import {
	resolveAuthChannel,
	shouldAttemptPortalAuth,
	shouldUseTestModeAuth
} from './auth-precedence';

describe('auth-precedence', () => {
	it('prefers portal auth when embedded even with II bypass', () => {
		expect(resolveAuthChannel(true, true)).toBe('portal');
		expect(shouldAttemptPortalAuth(true)).toBe(true);
		expect(shouldUseTestModeAuth(true, true)).toBe(false);
	});

	it('uses test-mode auth when standalone with II bypass', () => {
		expect(resolveAuthChannel(false, true)).toBe('test');
		expect(shouldAttemptPortalAuth(false)).toBe(false);
		expect(shouldUseTestModeAuth(false, true)).toBe(true);
	});

	it('uses Internet Identity when not embedded and no bypass', () => {
		expect(resolveAuthChannel(false, false)).toBe('ii');
		expect(shouldUseTestModeAuth(false, false)).toBe(false);
	});
});
