import { writable, get } from 'svelte/store';
import type { SidebarConfig } from '$lib/config/sidebar';

export const sidebarConfig = writable<SidebarConfig | null>(null);
export const sidebarLoading = writable(false);

const CACHE_KEY = 'sidebar_cache';

function readCache(): SidebarConfig | null {
	try {
		const raw = localStorage.getItem(CACHE_KEY);
		if (!raw) return null;
		return JSON.parse(raw) as SidebarConfig;
	} catch {
		return null;
	}
}

function writeCache(config: SidebarConfig): void {
	try {
		localStorage.setItem(CACHE_KEY, JSON.stringify(config));
	} catch {
		// storage full or unavailable
	}
}

/**
 * Load the sidebar from the backend's get_sidebar endpoint.
 * The backend resolves all ordering, visibility, and welcome page logic.
 */
export async function loadSidebar(
	backend: { get_sidebar: (args: string) => Promise<string> },
	locale: string = 'en',
): Promise<void> {
	const cached = readCache();
	if (cached) {
		sidebarConfig.set(cached);
	}

	sidebarLoading.set(true);
	try {
		const raw = await backend.get_sidebar(JSON.stringify({ locale }));
		const parsed = JSON.parse(raw);

		if (!parsed?.success) {
			throw new Error(parsed?.error || 'Backend returned failure');
		}

		const config: SidebarConfig = {
			welcomeItems: parsed.welcome_items || [],
			mundusItems: parsed.mundus_items || [],
			categories: parsed.categories || [],
			defaultPath: parsed.default_path || '/extensions/member_dashboard',
		};

		sidebarConfig.set(config);
		writeCache(config);
	} catch (e) {
		console.error('Failed to load sidebar:', e);
		if (!get(sidebarConfig) && cached) {
			sidebarConfig.set(cached);
		}
	} finally {
		sidebarLoading.set(false);
	}
}
