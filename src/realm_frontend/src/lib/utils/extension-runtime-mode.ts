import type { ExtensionManifestInfo } from './extension-manifest';

export type ExtensionMountMode =
	| { kind: 'not_installed' }
	| { kind: 'manifest_unavailable' }
	| { kind: 'sandboxed' }
	| { kind: 'in_process' }
	| { kind: 'not_privileged' };

export function resolveExtensionMountMode(
	version: string | null | undefined,
	manifest: ExtensionManifestInfo | null | undefined,
	isPrivileged: boolean,
): ExtensionMountMode {
	if (!version) {
		return { kind: 'not_installed' };
	}

	if (!manifest) {
		return { kind: 'manifest_unavailable' };
	}

	if (manifest.runtime === 'sandboxed') {
		return { kind: 'sandboxed' };
	}

	if (!isPrivileged) {
		return { kind: 'not_privileged' };
	}

	return { kind: 'in_process' };
}
