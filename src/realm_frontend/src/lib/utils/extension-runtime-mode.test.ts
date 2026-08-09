import { describe, expect, it } from 'vitest';
import { resolveExtensionMountMode } from './extension-runtime-mode';
import type { ExtensionManifestInfo } from './extension-manifest';

const sandboxedManifest: ExtensionManifestInfo = {
	name: 'member_dashboard',
	runtime: 'sandboxed',
};

const inProcessManifest: ExtensionManifestInfo = {
	name: 'admin_dashboard',
};

describe('resolveExtensionMountMode', () => {
	it('returns not_installed when version is missing', () => {
		expect(resolveExtensionMountMode(null, sandboxedManifest, true)).toEqual({
			kind: 'not_installed',
		});
	});

	it('returns manifest_unavailable when version exists but manifest is null', () => {
		expect(resolveExtensionMountMode('1.1.2', null, true)).toEqual({
			kind: 'manifest_unavailable',
		});
	});

	it('never selects in_process when manifest is unavailable', () => {
		const mode = resolveExtensionMountMode('1.1.2', null, true);
		expect(mode.kind).not.toBe('in_process');
	});

	it('selects sandboxed when manifest declares sandboxed runtime', () => {
		expect(resolveExtensionMountMode('1.1.2', sandboxedManifest, false)).toEqual({
			kind: 'sandboxed',
		});
	});

	it('selects in_process for privileged extensions with non-sandboxed manifest', () => {
		expect(resolveExtensionMountMode('1.0.0', inProcessManifest, true)).toEqual({
			kind: 'in_process',
		});
	});

	it('returns not_privileged for non-sandboxed manifest when extension is not privileged', () => {
		expect(resolveExtensionMountMode('1.0.0', inProcessManifest, false)).toEqual({
			kind: 'not_privileged',
		});
	});
});
