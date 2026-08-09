/**
 * Auth channel precedence: portal embed wins over test-mode II bypass.
 * Standalone test realms keep the deterministic mock identities.
 */
export type AuthChannel = 'portal' | 'test' | 'ii';

export function resolveAuthChannel(
	embeddedInPortal: boolean,
	testModeIIBypass: boolean
): AuthChannel {
	if (embeddedInPortal) return 'portal';
	if (testModeIIBypass) return 'test';
	return 'ii';
}

/** True when portal delegation restore/login should run (even if II bypass is on). */
export function shouldAttemptPortalAuth(embeddedInPortal: boolean): boolean {
	return embeddedInPortal;
}

/** True when the test-mode mock should run (standalone test realms only). */
export function shouldUseTestModeAuth(
	embeddedInPortal: boolean,
	testModeIIBypass: boolean
): boolean {
	return testModeIIBypass && !embeddedInPortal;
}

/** Join page may opt into test identities even inside the portal iframe. */
export function shouldPreferTestModeLogin(
	preferTestMode: boolean,
	testModeIIBypass: boolean
): boolean {
	return preferTestMode && testModeIIBypass;
}

/** Test sessions may be restored after iframe reloads when II bypass is on. */
export function shouldRestoreTestModeSession(testModeIIBypass: boolean): boolean {
	return testModeIIBypass;
}
