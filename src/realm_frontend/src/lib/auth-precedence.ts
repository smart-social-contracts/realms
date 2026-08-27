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

/** Established session pin overrides ambient embed/bypass precedence. */
export function resolveEffectiveAuthChannel(
	embeddedInPortal: boolean,
	testModeIIBypass: boolean,
	pinnedChannel: AuthChannel | null = null
): AuthChannel {
	if (pinnedChannel) return pinnedChannel;
	return resolveAuthChannel(embeddedInPortal, testModeIIBypass);
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
	_testModeIIBypass?: boolean
): boolean {
	// The picker is already gated on the live bypass flag. Requiring a second
	// canister_ids hint dropped Continue clicks in the portal iframe.
	return !!preferTestMode;
}

/**
 * True when login() must mint a deterministic test identity instead of
 * waiting on Internet Identity or a portal delegation.
 *
 * An explicit picker index (including 0) always wins — that is the Continue
 * as Identity N path. `preferTestMode` is the join page opt-in for portal
 * embeds. Ambient test auth still applies only to standalone bypass realms.
 */
export function shouldLoginWithTestIdentity(options: {
	identityIndex?: number | null;
	preferTestMode?: boolean;
	testModeIIBypass?: boolean;
	embeddedInPortal?: boolean;
} = {}): boolean {
	const { identityIndex = null, preferTestMode = false, testModeIIBypass = false, embeddedInPortal = false } =
		options;
	if (identityIndex != null && Number.isFinite(identityIndex)) return true;
	if (preferTestMode) return true;
	return shouldUseTestModeAuth(!!embeddedInPortal, !!testModeIIBypass);
}

/** Test sessions may be restored after iframe reloads when II bypass is on. */
export function shouldRestoreTestModeSession(testModeIIBypass: boolean): boolean {
	return testModeIIBypass;
}
