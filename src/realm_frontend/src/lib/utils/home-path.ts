import type { SidebarConfig } from '$lib/config/sidebar';

/**
 * Resolve the realm member-home path from host sidebar config.
 * Extensions emit `navigate.home`; only the host knows this target.
 */
export function resolveHomePath(config: Pick<SidebarConfig, 'defaultPath'> | null | undefined): string {
	const path = typeof config?.defaultPath === 'string' ? config.defaultPath.trim() : '';
	return path || '/';
}
