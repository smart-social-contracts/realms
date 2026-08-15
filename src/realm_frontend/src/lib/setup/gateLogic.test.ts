import { describe, expect, it } from 'vitest';
import {
	MAX_UNKNOWN_SETUP_ATTEMPTS,
	resolveSetupGate,
	shouldPollSetupState,
	shouldShowSetupLoading
} from './gateLogic';

const settledAuthorized = {
	loading: false,
	status: 'setup' as const,
	unknownStatusFailures: 0,
	isAuthenticated: true,
	isCallerAuthorized: true,
	authChannelSettled: true,
	setupStateLoaded: true
};

describe('shouldShowSetupLoading', () => {
	it('shows loading while gate input is loading', () => {
		expect(
			shouldShowSetupLoading({
				loading: true,
				status: 'setup',
				unknownStatusFailures: 0,
				isAuthenticated: false,
				isCallerAuthorized: false,
				authChannelSettled: false,
				setupStateLoaded: false,
				pathname: '/setup'
			})
		).toBe(true);
	});

	it('shows loading until auth channel settles during setup', () => {
		expect(
			shouldShowSetupLoading({
				loading: false,
				status: 'setup',
				unknownStatusFailures: 0,
				isAuthenticated: true,
				isCallerAuthorized: false,
				authChannelSettled: false,
				setupStateLoaded: false,
				pathname: '/setup'
			})
		).toBe(true);
	});

	it('shows loading until setup state is fetched after auth settles', () => {
		expect(
			shouldShowSetupLoading({
				loading: false,
				status: 'setup',
				unknownStatusFailures: 0,
				isAuthenticated: true,
				isCallerAuthorized: false,
				authChannelSettled: true,
				setupStateLoaded: false,
				pathname: '/setup'
			})
		).toBe(true);
	});

	it('does not load forever once auth and setup state have settled', () => {
		expect(
			shouldShowSetupLoading({
				...settledAuthorized,
				isCallerAuthorized: false,
				pathname: '/setup'
			})
		).toBe(false);
	});
});

describe('resolveSetupGate', () => {
	it('shows loading while gate input is loading', () => {
		expect(
			resolveSetupGate({
				loading: true,
				status: null,
				unknownStatusFailures: 0,
				isAuthenticated: false,
				isCallerAuthorized: false,
				authChannelSettled: false,
				setupStateLoaded: false,
				pathname: '/'
			})
		).toEqual({ kind: 'loading' });
	});

	it('allows normal app when setup state is unavailable', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: null,
				unknownStatusFailures: MAX_UNKNOWN_SETUP_ATTEMPTS,
				isAuthenticated: false,
				isCallerAuthorized: false,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/'
			})
		).toEqual({ kind: 'normal' });
	});

	it('allows normal app when not in setup', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'alpha',
				unknownStatusFailures: 0,
				isAuthenticated: false,
				isCallerAuthorized: false,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/'
			})
		).toEqual({ kind: 'normal' });
	});

	it('shows anonymous gate when setup and not logged in', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				unknownStatusFailures: 0,
				isAuthenticated: false,
				isCallerAuthorized: false,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/'
			})
		).toEqual({ kind: 'gate', variant: 'anonymous' });
	});

	it('shows unauthorized gate for logged-in non-creators after settlement', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				unknownStatusFailures: 0,
				isAuthenticated: true,
				isCallerAuthorized: false,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/dashboard'
			})
		).toEqual({ kind: 'gate', variant: 'unauthorized' });
	});

	it('keeps loading instead of unauthorized while authorization is unresolved', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				unknownStatusFailures: 0,
				isAuthenticated: true,
				isCallerAuthorized: false,
				authChannelSettled: false,
				setupStateLoaded: false,
				pathname: '/setup'
			})
		).toEqual({ kind: 'loading' });
	});

	it('allows join flow during setup', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				unknownStatusFailures: 0,
				isAuthenticated: false,
				isCallerAuthorized: false,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/join'
			})
		).toEqual({ kind: 'normal' });
	});

	it('redirects authorized creators to the wizard', () => {
		expect(
			resolveSetupGate({
				...settledAuthorized,
				pathname: '/settings'
			})
		).toEqual({ kind: 'redirect', to: '/setup' });
	});

	it('shows setup wizard on /setup for authorized creators', () => {
		expect(
			resolveSetupGate({
				...settledAuthorized,
				pathname: '/setup'
			})
		).toEqual({ kind: 'setup_wizard' });
	});

	it('shows loading for unknown status with no failures yet', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: null,
				unknownStatusFailures: 0,
				isAuthenticated: true,
				isCallerAuthorized: true,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/'
			})
		).toEqual({ kind: 'loading' });
	});

	it('shows loading for unknown status with one failure', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: null,
				unknownStatusFailures: 1,
				isAuthenticated: true,
				isCallerAuthorized: true,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/'
			})
		).toEqual({ kind: 'loading' });
	});

	it('shows loading for unknown status with two failures', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: null,
				unknownStatusFailures: 2,
				isAuthenticated: true,
				isCallerAuthorized: true,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/'
			})
		).toEqual({ kind: 'loading' });
	});

	it('fails open after max unknown status failures', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: null,
				unknownStatusFailures: MAX_UNKNOWN_SETUP_ATTEMPTS,
				isAuthenticated: true,
				isCallerAuthorized: true,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/'
			})
		).toEqual({ kind: 'normal' });
	});

	it('redirects authorized creators during setup from non-setup pathname', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				unknownStatusFailures: 0,
				isAuthenticated: true,
				isCallerAuthorized: true,
				authChannelSettled: true,
				setupStateLoaded: true,
				pathname: '/dashboard'
			})
		).toEqual({ kind: 'redirect', to: '/setup' });
	});
});

describe('shouldPollSetupState', () => {
	it('polls while realm is in setup', () => {
		expect(shouldPollSetupState('setup')).toBe(true);
	});

	it('polls while setup status is unknown', () => {
		expect(shouldPollSetupState(null)).toBe(true);
	});

	it('does not poll when not in setup', () => {
		expect(shouldPollSetupState('alpha')).toBe(false);
	});
});
