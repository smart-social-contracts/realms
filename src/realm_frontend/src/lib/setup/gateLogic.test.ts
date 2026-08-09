import { describe, expect, it } from 'vitest';
import { resolveSetupGate, shouldPollSetupState, shouldShowSetupLoading } from './gateLogic';

const settledAuthorized = {
	loading: false,
	status: 'setup' as const,
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
});

describe('shouldPollSetupState', () => {
	it('polls only while realm is in setup', () => {
		expect(shouldPollSetupState('setup')).toBe(true);
		expect(shouldPollSetupState('alpha')).toBe(false);
		expect(shouldPollSetupState(null)).toBe(false);
	});
});
