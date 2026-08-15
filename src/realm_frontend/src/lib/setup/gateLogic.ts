export const MAX_UNKNOWN_SETUP_ATTEMPTS = 3;

export type SetupGateVariant = 'anonymous' | 'unauthorized';

export type SetupGateDecision =
	| { kind: 'loading' }
	| { kind: 'normal' }
	| { kind: 'gate'; variant: SetupGateVariant }
	| { kind: 'setup_wizard' }
	| { kind: 'redirect'; to: string };

export interface ResolveSetupGateInput {
	loading: boolean;
	status: string | null;
	/** Consecutive failures to read setup state; unknown status fails open past the cap. */
	unknownStatusFailures: number;
	isAuthenticated: boolean;
	isCallerAuthorized: boolean;
	/** Portal / II auth channel has finished its initial bootstrap. */
	authChannelSettled: boolean;
	/** Setup state fetched at least once after auth channel settled. */
	setupStateLoaded: boolean;
	pathname: string;
}

const JOIN_PREFIX = '/join';
const SETUP_PATH = '/setup';

function isJoinPath(pathname: string): boolean {
	return pathname === JOIN_PREFIX || pathname.startsWith(`${JOIN_PREFIX}/`);
}

function isSetupPath(pathname: string): boolean {
	return pathname === SETUP_PATH || pathname.startsWith(`${SETUP_PATH}/`);
}

/**
 * True while setup gate must not show anonymous/unauthorized copy yet.
 * Keeps a neutral loading state until auth + setup state have settled.
 */
export function shouldShowSetupLoading(input: ResolveSetupGateInput): boolean {
	if (input.loading) return true;
	if (input.status === null && input.unknownStatusFailures < MAX_UNKNOWN_SETUP_ATTEMPTS) {
		return true;
	}
	if (input.status !== 'setup') return false;
	if (!input.authChannelSettled) return true;
	if (!input.setupStateLoaded) return true;
	return false;
}

/** Pure gate resolver — unit-tested. */
export function resolveSetupGate(input: ResolveSetupGateInput): SetupGateDecision {
	if (shouldShowSetupLoading(input)) {
		return { kind: 'loading' };
	}

	if (input.status !== 'setup') {
		return { kind: 'normal' };
	}

	if (isJoinPath(input.pathname)) {
		return { kind: 'normal' };
	}

	if (!input.isAuthenticated) {
		return { kind: 'gate', variant: 'anonymous' };
	}

	if (!input.isCallerAuthorized) {
		return { kind: 'gate', variant: 'unauthorized' };
	}

	if (isSetupPath(input.pathname)) {
		return { kind: 'setup_wizard' };
	}

	return { kind: 'redirect', to: SETUP_PATH };
}

export function shouldPollSetupState(status: string | null): boolean {
	return status === null || status === 'setup';
}
