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

function isInSetupFlow(input: ResolveSetupGateInput): boolean {
	if (isJoinPath(input.pathname)) return false;
	return input.status === 'setup' || isSetupPath(input.pathname);
}

/**
 * True while the setup skeleton / gate must hold instead of the live app.
 *
 * Ordinary boot of a live realm (portal embed at `/`, unknown or non-setup
 * status) is not a setup flow — do not paint "Loading setup…". Keep the
 * skeleton only when the visitor is already on `/setup` or we already know
 * the realm is in setup, and auth + setup state have not settled yet.
 */
export function shouldShowSetupLoading(input: ResolveSetupGateInput): boolean {
	if (!isInSetupFlow(input)) return false;

	if (input.status === null) {
		return input.unknownStatusFailures < MAX_UNKNOWN_SETUP_ATTEMPTS;
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
