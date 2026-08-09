import { describe, expect, it } from 'vitest';
import {
	canAdvanceFromCodexStep,
	canNavigateToWizardStep,
	getCodexStepPrimaryLabel,
	getPreviousWizardStep,
	isCodexInstalled,
	isCodexPrimaryActionDisabled,
	reconcileCodexVersion,
	resolveSelectedCodexVersion,
	shouldClearCodexAdvanceError
} from './wizardLogic';
import type { SetupState } from './types';

const installedState: SetupState = {
	status: 'setup',
	creator: 'abc',
	is_caller_authorized: true,
	codex: { package: 'agora', version: '0.9.5' },
	token: null,
	branding: null
};

const freshState: SetupState = {
	status: 'setup',
	creator: 'abc',
	is_caller_authorized: true,
	codex: null,
	token: null,
	branding: null
};

describe('wizardLogic', () => {
	it('detects installed codex from setup state', () => {
		expect(isCodexInstalled(installedState)).toBe(true);
		expect(isCodexInstalled({ ...installedState, codex: null })).toBe(false);
	});

	it('allows advancing when backend has codex regardless of UI version binding', () => {
		expect(canAdvanceFromCodexStep(installedState)).toBe(true);
		expect(canAdvanceFromCodexStep(null)).toBe(false);
		expect(canAdvanceFromCodexStep(freshState)).toBe(false);
	});

	it('falls back to installed version when UI selection is empty', () => {
		expect(resolveSelectedCodexVersion('', installedState)).toBe('0.9.5');
		expect(resolveSelectedCodexVersion('0.9.4', installedState)).toBe('0.9.4');
	});

	it('keeps installed version when catalog list omits it', () => {
		const versions = ['0.9.6', '1.0.0'];
		expect(
			reconcileCodexVersion(versions, '', '0.9.5', (v) => v[v.length - 1] ?? '')
		).toBe('0.9.5');
	});

	it('uses latest catalog version when nothing is selected or installed', () => {
		const versions = ['0.9.4', '0.9.5'];
		expect(reconcileCodexVersion(versions, '', undefined, (v) => v[v.length - 1] ?? '')).toBe(
			'0.9.5'
		);
	});

	describe('codex primary action', () => {
		it('labels install vs continue for fresh vs installed realms', () => {
			expect(getCodexStepPrimaryLabel(freshState, false)).toBe('Install codex');
			expect(getCodexStepPrimaryLabel(installedState, false)).toBe('Continue');
			expect(getCodexStepPrimaryLabel(freshState, true)).toBe('Installing…');
		});

		it('enables install on fresh realm when codex and version are selected', () => {
			expect(isCodexPrimaryActionDisabled(false, 'agora', '0.9.5', freshState)).toBe(false);
			expect(isCodexPrimaryActionDisabled(false, '', '0.9.5', freshState)).toBe(true);
			expect(isCodexPrimaryActionDisabled(false, 'agora', '', freshState)).toBe(true);
		});

		it('enables continue when codex is already installed', () => {
			expect(isCodexPrimaryActionDisabled(false, '', '', installedState)).toBe(false);
		});
	});

	describe('back navigation', () => {
		it('returns the previous step for steps 2-4', () => {
			expect(getPreviousWizardStep('codex')).toBeNull();
			expect(getPreviousWizardStep('token')).toBe('codex');
			expect(getPreviousWizardStep('branding')).toBe('token');
			expect(getPreviousWizardStep('review')).toBe('branding');
		});
	});

	describe('step navigation and banner scoping', () => {
		it('blocks skipping ahead from codex without install and surfaces the banner', () => {
			expect(canNavigateToWizardStep('codex', 'token', freshState)).toEqual({
				allowed: false,
				showError: true,
				errorMessage: 'Install a codex before continuing to later steps'
			});
		});

		it('allows back navigation without the banner', () => {
			expect(canNavigateToWizardStep('token', 'codex', freshState)).toEqual({ allowed: true });
			expect(canNavigateToWizardStep('review', 'branding', freshState)).toEqual({ allowed: true });
		});

		it('allows forward navigation once codex is installed', () => {
			expect(canNavigateToWizardStep('codex', 'token', installedState)).toEqual({ allowed: true });
		});

		it('clears the codex banner when returning to the codex step', () => {
			expect(
				shouldClearCodexAdvanceError(
					'codex',
					'Install a codex before continuing to later steps'
				)
			).toBe(true);
			expect(shouldClearCodexAdvanceError('token', 'Install a codex before continuing to later steps')).toBe(
				false
			);
		});
	});
});
