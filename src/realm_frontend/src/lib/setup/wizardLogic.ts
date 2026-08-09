import type { SetupState } from './types';

export type WizardStep = 'codex' | 'token' | 'branding' | 'review';

export const WIZARD_STEPS: WizardStep[] = ['codex', 'token', 'branding', 'review'];

const CODEX_ADVANCE_ERROR = 'Install a codex before continuing to later steps';

/** True when backend setup state already has a codex installed. */
export function isCodexInstalled(state: SetupState | null | undefined): boolean {
	return Boolean(state?.codex?.package && state?.codex?.version);
}

/**
 * Resolve the version to send for install / continue checks.
 * Prefer explicit UI selection, then installed backend version.
 */
export function resolveSelectedCodexVersion(
	selectedVersion: string,
	setupState: SetupState | null | undefined
): string {
	const trimmed = selectedVersion.trim();
	if (trimmed) return trimmed;
	return setupState?.codex?.version?.trim() ?? '';
}

/**
 * Whether the codex step can advance without calling install again.
 * Uses backend truth — do not require UI Select binding to match.
 */
export function canAdvanceFromCodexStep(setupState: SetupState | null | undefined): boolean {
	return isCodexInstalled(setupState);
}

/**
 * Pick a default version for the codex picker without clobbering an installed version.
 */
export function reconcileCodexVersion(
	codexVersions: string[],
	selectedVersion: string,
	installedVersion: string | undefined,
	latestVersion: (versions: string[]) => string
): string {
	const installed = installedVersion?.trim() ?? '';
	if (installed) {
		return installed;
	}
	if (selectedVersion && codexVersions.includes(selectedVersion)) {
		return selectedVersion;
	}
	return latestVersion(codexVersions);
}

export function getPreviousWizardStep(current: WizardStep): WizardStep | null {
	const index = WIZARD_STEPS.indexOf(current);
	if (index <= 0) return null;
	return WIZARD_STEPS[index - 1] ?? null;
}

export function getCodexStepPrimaryLabel(
	setupState: SetupState | null | undefined,
	busy: boolean
): string {
	if (busy) return 'Installing…';
	return canAdvanceFromCodexStep(setupState) ? 'Continue' : 'Install codex';
}

export function isCodexPrimaryActionDisabled(
	busy: boolean,
	selectedCodexId: string,
	selectedVersion: string,
	setupState: SetupState | null | undefined
): boolean {
	if (busy) return true;
	if (canAdvanceFromCodexStep(setupState)) return false;
	return !selectedCodexId.trim() || !selectedVersion.trim();
}

export interface WizardStepNavigationResult {
	allowed: boolean;
	showError?: boolean;
	errorMessage?: string;
}

/**
 * Stepper / programmatic navigation rules. Back navigation never mutates backend state.
 * The codex-install banner only appears when attempting to skip ahead from step 1.
 */
export function canNavigateToWizardStep(
	from: WizardStep,
	to: WizardStep,
	setupState: SetupState | null | undefined
): WizardStepNavigationResult {
	if (from === to) {
		return { allowed: true };
	}

	const fromIndex = WIZARD_STEPS.indexOf(from);
	const toIndex = WIZARD_STEPS.indexOf(to);
	if (fromIndex < 0 || toIndex < 0) {
		return { allowed: false };
	}

	if (toIndex <= fromIndex) {
		return { allowed: true };
	}

	if (!canAdvanceFromCodexStep(setupState)) {
		return {
			allowed: false,
			showError: from === 'codex',
			errorMessage: CODEX_ADVANCE_ERROR
		};
	}

	return { allowed: true };
}

export function shouldClearCodexAdvanceError(currentStep: WizardStep, error: string): boolean {
	return currentStep === 'codex' && error === CODEX_ADVANCE_ERROR;
}
