export interface ExtensionManifestInfo {
	name: string;
	version?: string;
	description?: string;
	author?: string;
	doc_url?: string | null;
	repository?: string;
	categories?: string[];
	profiles?: string[];
	[key: string]: unknown;
}

let cache: Record<string, ExtensionManifestInfo> | null = null;
let loadPromise: Promise<Record<string, ExtensionManifestInfo>> | null = null;

const LEGACY_REALMS_EXTENSIONS_PREFIX =
	'https://github.com/smart-social-contracts/realms/tree/main/extensions/';
const EXTENSIONS_REPO_PREFIX =
	'https://github.com/smart-social-contracts/realms-extensions/tree/main/extensions/';

export function extensionRepoUrl(extensionId: string): string {
	return `${EXTENSIONS_REPO_PREFIX}${extensionId}`;
}

export function resolveExtensionRepoUrl(
	manifest: ExtensionManifestInfo | null,
	extensionId?: string,
): string | null {
	if (!manifest) {
		return extensionId ? extensionRepoUrl(extensionId) : null;
	}

	const doc = typeof manifest.doc_url === 'string' ? manifest.doc_url.trim() : '';
	if (doc) {
		if (doc.startsWith(LEGACY_REALMS_EXTENSIONS_PREFIX)) {
			return doc.replace(LEGACY_REALMS_EXTENSIONS_PREFIX, EXTENSIONS_REPO_PREFIX);
		}
		const legacyBareMatch = doc.match(
			/^https:\/\/github\.com\/smart-social-contracts\/extensions\/([^/]+)$/,
		);
		if (legacyBareMatch) {
			return extensionRepoUrl(legacyBareMatch[1]);
		}
		return doc;
	}

	const repo = typeof manifest.repository === 'string' ? manifest.repository.trim() : '';
	if (repo) return repo;

	return extensionId ? extensionRepoUrl(extensionId) : null;
}

export function parseExtensionIdFromPath(pathname: string): string | null {
	const match = pathname.match(/^\/extensions\/([^/]+)/);
	return match?.[1] ?? null;
}

export async function fetchExtensionManifests(): Promise<Record<string, ExtensionManifestInfo>> {
	if (cache) return cache;
	if (loadPromise) return loadPromise;

	loadPromise = (async () => {
		try {
			const { backend } = await import('$lib/canisters');
			const raw = await backend.list_runtime_extensions();
			const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
			cache = parsed?.all_manifests ?? {};
			return cache;
		} catch (e) {
			console.warn('[extension-manifest] failed to load manifests:', e);
			return {};
		}
	})();

	return loadPromise;
}

export async function getExtensionManifest(
	extId: string,
): Promise<ExtensionManifestInfo | null> {
	const manifests = await fetchExtensionManifests();
	return manifests[extId] ?? null;
}

export function clearExtensionManifestCache(): void {
	cache = null;
	loadPromise = null;
}
