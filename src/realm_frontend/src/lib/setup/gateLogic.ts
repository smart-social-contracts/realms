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
	isAuthenticated: boolean;
	isCallerAuthorized: boolean;
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

/** Pure gate resolver — unit-tested. */
export function resolveSetupGate(input: ResolveSetupGateInput): SetupGateDecision {
	if (input.loading) {
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
	return status === 'setup';
}
