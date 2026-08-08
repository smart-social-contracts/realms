import { describe, expect, it } from 'vitest';
import { resolveSetupGate, shouldPollSetupState } from './gateLogic';

describe('resolveSetupGate', () => {
	it('shows loading while gate input is loading', () => {
		expect(
			resolveSetupGate({
				loading: true,
				status: null,
				isAuthenticated: false,
				isCallerAuthorized: false,
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
				pathname: '/'
			})
		).toEqual({ kind: 'gate', variant: 'anonymous' });
	});

	it('shows unauthorized gate for logged-in non-creators', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				isAuthenticated: true,
				isCallerAuthorized: false,
				pathname: '/dashboard'
			})
		).toEqual({ kind: 'gate', variant: 'unauthorized' });
	});

	it('allows join flow during setup', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				isAuthenticated: false,
				isCallerAuthorized: false,
				pathname: '/join'
			})
		).toEqual({ kind: 'normal' });
	});

	it('redirects authorized creators to the wizard', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				isAuthenticated: true,
				isCallerAuthorized: true,
				pathname: '/settings'
			})
		).toEqual({ kind: 'redirect', to: '/setup' });
	});

	it('shows setup wizard on /setup for authorized creators', () => {
		expect(
			resolveSetupGate({
				loading: false,
				status: 'setup',
				isAuthenticated: true,
				isCallerAuthorized: true,
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
