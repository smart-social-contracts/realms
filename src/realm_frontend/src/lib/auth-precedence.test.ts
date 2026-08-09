import { describe, expect, it } from 'vitest';
import {
	resolveAuthChannel,
	shouldAttemptPortalAuth,
	shouldPreferTestModeLogin,
	shouldRestoreTestModeSession,
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

	it('allows join page to prefer test identities inside portal iframe', () => {
		expect(shouldPreferTestModeLogin(true, true)).toBe(true);
		expect(shouldPreferTestModeLogin(true, false)).toBe(false);
		expect(shouldPreferTestModeLogin(false, true)).toBe(false);
	});

	it('restores test sessions when II bypass is on (including portal reloads)', () => {
		expect(shouldRestoreTestModeSession(true)).toBe(true);
		expect(shouldRestoreTestModeSession(false)).toBe(false);
	});
});
