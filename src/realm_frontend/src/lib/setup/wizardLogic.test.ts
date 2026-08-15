import { describe, expect, it } from 'vitest';
import {
	canAdvanceFromCodexStep,
	canAdvanceFromWelcomeStep,
	canNavigateToWizardStep,
	getCodexStepPrimaryLabel,
	getNextWizardStep,
	getPreviousWizardStep,
	getWelcomeAdvanceStep,
	isCodexChosen,
	isCodexInstalled,
	isCodexPrimaryActionDisabled,
	reconcileCodexVersion,
	resolveInitialWizardStep,
	resolveSelectedCodexVersion,
	shouldClearCodexAdvanceError,
	stepToUrlToken,
	urlTokenToStep
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

const draftChosenState: SetupState = {
	status: 'setup',
	creator: 'abc',
	is_caller_authorized: true,
	codex: null,
	token: null,
	branding: null,
	draft: {
		step: 'codex',
		codex: { package: 'agora', version: '0.9.5' }
	}
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

	it('detects chosen codex from draft or installed backend state', () => {
		expect(isCodexChosen(draftChosenState)).toBe(true);
		expect(isCodexChosen(installedState)).toBe(true);
		expect(isCodexChosen(freshState)).toBe(false);
		expect(isCodexChosen(null)).toBe(false);
	});

	it('allows advancing when draft or backend has a codex', () => {
		expect(canAdvanceFromCodexStep(draftChosenState)).toBe(true);
		expect(canAdvanceFromCodexStep(installedState)).toBe(true);
		expect(canAdvanceFromCodexStep(freshState)).toBe(false);
	});

	it('falls back to draft then installed version when UI selection is empty', () => {
		expect(resolveSelectedCodexVersion('', draftChosenState)).toBe('0.9.5');
		expect(resolveSelectedCodexVersion('', installedState)).toBe('0.9.5');
		expect(resolveSelectedCodexVersion('0.9.4', installedState)).toBe('0.9.4');
	});

	it('keeps saved version when catalog list omits it', () => {
		const versions = ['0.9.6', '1.0.0'];
		expect(
			reconcileCodexVersion(versions, '', '0.9.5', (v) => v[v.length - 1] ?? '')
		).toBe('0.9.5');
	});

	it('uses latest catalog version when nothing is selected or saved', () => {
		const versions = ['0.9.4', '0.9.5'];
		expect(reconcileCodexVersion(versions, '', undefined, (v) => v[v.length - 1] ?? '')).toBe(
			'0.9.5'
		);
	});

	describe('codex primary action', () => {
		it('always labels continue when not busy', () => {
			expect(getCodexStepPrimaryLabel(freshState, false)).toBe('Continue');
			expect(getCodexStepPrimaryLabel(installedState, false)).toBe('Continue');
			expect(getCodexStepPrimaryLabel(freshState, true)).toBe('Saving…');
		});

		it('requires codex and version selection on a fresh realm', () => {
			expect(isCodexPrimaryActionDisabled(false, 'agora', '0.9.5', freshState)).toBe(false);
			expect(isCodexPrimaryActionDisabled(false, '', '0.9.5', freshState)).toBe(true);
			expect(isCodexPrimaryActionDisabled(false, 'agora', '', freshState)).toBe(true);
		});

		it('enables continue when codex is already chosen', () => {
			expect(isCodexPrimaryActionDisabled(false, '', '', draftChosenState)).toBe(false);
		});
	});

	describe('welcome step', () => {
		it('always allows advancing to codex without backend state', () => {
			expect(canAdvanceFromWelcomeStep()).toBe(true);
			expect(getWelcomeAdvanceStep()).toBe('codex');
		});

		it('places welcome first in the step order', () => {
			expect(getPreviousWizardStep('welcome')).toBeNull();
			expect(getPreviousWizardStep('codex')).toBe('welcome');
			expect(getNextWizardStep('welcome')).toBe('codex');
			expect(getNextWizardStep('review')).toBeNull();
		});

		it('allows navigation from welcome to codex without a chosen codex', () => {
			expect(canNavigateToWizardStep('welcome', 'codex', freshState)).toEqual({ allowed: true });
		});

		it('blocks skipping ahead from welcome past codex', () => {
			expect(canNavigateToWizardStep('welcome', 'token', freshState)).toEqual({
				allowed: false,
				showError: false,
				errorMessage: 'Choose a codex before continuing to later steps'
			});
		});
	});

	describe('back navigation', () => {
		it('returns the previous step for steps 2-5', () => {
			expect(getPreviousWizardStep('welcome')).toBeNull();
			expect(getPreviousWizardStep('codex')).toBe('welcome');
			expect(getPreviousWizardStep('token')).toBe('codex');
			expect(getPreviousWizardStep('branding')).toBe('token');
			expect(getPreviousWizardStep('review')).toBe('branding');
		});
	});

	describe('step navigation and banner scoping', () => {
		it('blocks skipping ahead from codex without a choice and surfaces the banner', () => {
			expect(canNavigateToWizardStep('codex', 'token', freshState)).toEqual({
				allowed: false,
				showError: true,
				errorMessage: 'Choose a codex before continuing to later steps'
			});
		});

		it('allows back navigation without the banner', () => {
			expect(canNavigateToWizardStep('token', 'codex', freshState)).toEqual({ allowed: true });
			expect(canNavigateToWizardStep('review', 'branding', freshState)).toEqual({ allowed: true });
		});

		it('allows forward navigation once codex is chosen', () => {
			expect(canNavigateToWizardStep('codex', 'token', draftChosenState)).toEqual({ allowed: true });
		});

		it('clears the codex banner when returning to the codex step', () => {
			expect(
				shouldClearCodexAdvanceError(
					'codex',
					'Choose a codex before continuing to later steps'
				)
			).toBe(true);
			expect(
				shouldClearCodexAdvanceError('token', 'Choose a codex before continuing to later steps')
			).toBe(false);
		});
	});

	describe('initial step resolution', () => {
		it('prefers a reachable URL step', () => {
			expect(resolveInitialWizardStep(draftChosenState, 'token')).toBe('token');
		});

		it('resumes a running or failed launch on review', () => {
			expect(
				resolveInitialWizardStep(
					{ ...freshState, launch: { status: 'running', phase: 'install_codex', steps: [], updated_at: null } },
					null
				)
			).toBe('review');
		});

		it('falls back to the saved draft step', () => {
			expect(
				resolveInitialWizardStep(
					{ ...draftChosenState, draft: { ...draftChosenState.draft!, step: 'branding' } },
					null
				)
			).toBe('branding');
		});
	});

	describe('url token mapping', () => {
		it('maps review to launch in the URL', () => {
			expect(stepToUrlToken('review')).toBe('launch');
			expect(stepToUrlToken('welcome')).toBe('welcome');
			expect(stepToUrlToken('codex')).toBe('codex');
			expect(stepToUrlToken('token')).toBe('token');
			expect(stepToUrlToken('branding')).toBe('branding');
		});

		it('maps launch back to review and rejects unknown tokens', () => {
			expect(urlTokenToStep('launch')).toBe('review');
			expect(urlTokenToStep('welcome')).toBe('welcome');
			expect(urlTokenToStep('codex')).toBe('codex');
			expect(urlTokenToStep('token')).toBe('token');
			expect(urlTokenToStep('branding')).toBe('branding');
			expect(urlTokenToStep('review')).toBeNull();
			expect(urlTokenToStep('')).toBeNull();
			expect(urlTokenToStep('unknown')).toBeNull();
		});
	});
});
