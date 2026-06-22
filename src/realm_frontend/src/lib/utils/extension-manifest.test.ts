import { describe, expect, it } from 'vitest';
import {
	parseExtensionIdFromPath,
	resolveExtensionRepoUrl,
	type ExtensionManifestInfo,
} from './extension-manifest';

describe('parseExtensionIdFromPath', () => {
	it('extracts extension id from extension routes', () => {
		expect(parseExtensionIdFromPath('/extensions/voting')).toBe('voting');
		expect(parseExtensionIdFromPath('/extensions/voting/settings')).toBe('voting');
	});

	it('returns null for non-extension routes', () => {
		expect(parseExtensionIdFromPath('/settings')).toBeNull();
		expect(parseExtensionIdFromPath('/')).toBeNull();
	});
});

describe('resolveExtensionRepoUrl', () => {
	it('prefers doc_url over repository', () => {
		const manifest: ExtensionManifestInfo = {
			name: 'voting',
			doc_url: 'https://github.com/example/doc',
			repository: 'https://github.com/example/repo',
		};
		expect(resolveExtensionRepoUrl(manifest, 'voting')).toBe('https://github.com/example/doc');
	});

	it('rewrites legacy realms repo paths to realms-extensions', () => {
		const manifest: ExtensionManifestInfo = {
			name: 'voting',
			doc_url: 'https://github.com/smart-social-contracts/realms/tree/main/extensions/voting',
		};
		expect(resolveExtensionRepoUrl(manifest, 'voting')).toBe(
			'https://github.com/smart-social-contracts/realms-extensions/tree/main/extensions/voting',
		);
	});

	it('rewrites legacy bare extensions repo paths', () => {
		const manifest: ExtensionManifestInfo = {
			name: 'market_place',
			doc_url: 'https://github.com/smart-social-contracts/extensions/market_place',
		};
		expect(resolveExtensionRepoUrl(manifest, 'market_place')).toBe(
			'https://github.com/smart-social-contracts/realms-extensions/tree/main/extensions/market_place',
		);
	});

	it('falls back to repository when doc_url is missing', () => {
		const manifest: ExtensionManifestInfo = {
			name: 'vault',
			repository: 'https://github.com/example/vault',
		};
		expect(resolveExtensionRepoUrl(manifest, 'vault')).toBe('https://github.com/example/vault');
	});

	it('falls back to realms-extensions when no link is in manifest', () => {
		expect(resolveExtensionRepoUrl({ name: 'metrics', doc_url: null }, 'metrics')).toBe(
			'https://github.com/smart-social-contracts/realms-extensions/tree/main/extensions/metrics',
		);
		expect(resolveExtensionRepoUrl(null, 'voting')).toBe(
			'https://github.com/smart-social-contracts/realms-extensions/tree/main/extensions/voting',
		);
	});
});
