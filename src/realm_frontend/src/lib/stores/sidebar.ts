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
 * Shows cached data instantly, then refreshes from backend in background.
 */
export async function loadSidebar(
	backend: { list_runtime_extensions: () => Promise<string> },
	userProfiles: string[],
	locale: string = 'en',
): Promise<void> {
	const cached = readCache(userProfiles);
	if (cached) {
		sidebarConfig.set(cached);
	}

	sidebarLoading.set(true);
	try {
		const raw = await backend.list_runtime_extensions();
		const parsed = JSON.parse(raw);
		const manifests: Record<string, ExtensionManifest> = parsed?.all_manifests ?? {};

		const config = buildSidebar(manifests, userProfiles, locale);
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
