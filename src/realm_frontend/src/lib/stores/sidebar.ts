import { writable, get } from 'svelte/store';
import { buildSidebar, type SidebarConfig, type ExtensionManifest } from '$lib/config/sidebar';

export const sidebarConfig = writable<SidebarConfig | null>(null);
export const sidebarLoading = writable(false);

const CACHE_PREFIX = 'sidebar_cache_';

function cacheKey(profiles: string[]): string {
	return CACHE_PREFIX + [...profiles].sort().join(',');
}

function readCache(profiles: string[]): SidebarConfig | null {
	try {
		const raw = localStorage.getItem(cacheKey(profiles));
		if (!raw) return null;
		return JSON.parse(raw) as SidebarConfig;
	} catch {
		return null;
	}
}

function writeCache(profiles: string[], config: SidebarConfig): void {
	try {
		localStorage.setItem(cacheKey(profiles), JSON.stringify(config));
	} catch {
		// storage full or unavailable
	}
}

/**
 * Load the sidebar from the backend's installed extension manifests.
 * Uses get_my_extensions to determine visibility when available,
 * falling back to profile-based filtering for older backends.
 */
export async function loadSidebar(
	backend: { list_runtime_extensions: () => Promise<string>; get_my_extensions?: () => Promise<string> },
	userProfiles: string[],
	locale: string = 'en',
): Promise<void> {
	const cached = readCache(userProfiles);
	if (cached) {
		sidebarConfig.set(cached);
	}

	sidebarLoading.set(true);
	try {
		const [manifestsRaw, myExtRaw] = await Promise.all([
			backend.list_runtime_extensions(),
			backend.get_my_extensions?.().catch(() => null) ?? Promise.resolve(null),
		]);

		const parsed = JSON.parse(manifestsRaw);
		const manifests: Record<string, ExtensionManifest> = parsed?.all_manifests ?? {};

		let visibleExtensions: string[] | null = null;
		if (myExtRaw) {
			try {
				const extParsed = JSON.parse(myExtRaw);
				if (extParsed?.success && Array.isArray(extParsed.extensions)) {
					visibleExtensions = extParsed.extensions;
				}
			} catch {
				// fallback to profile-based filtering
			}
		}

		const config = buildSidebar(manifests, userProfiles, locale, visibleExtensions);
		sidebarConfig.set(config);
		writeCache(userProfiles, config);
	} catch (e) {
		console.error('Failed to load sidebar manifests:', e);
		if (!get(sidebarConfig) && cached) {
			sidebarConfig.set(cached);
		}
	} finally {
		sidebarLoading.set(false);
	}
}
