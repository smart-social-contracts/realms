import type { SetupState } from './types';

export type WizardStep = 'codex' | 'token' | 'branding' | 'review';

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
