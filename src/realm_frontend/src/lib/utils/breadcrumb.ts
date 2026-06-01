import type { SidebarConfig } from '$lib/config/sidebar';
import { topUtilityItems } from '$lib/config/sidebar';

export interface BreadcrumbSegment {
	label: string;
	href?: string;
}

function normalizePath(pathname: string): string {
	const path = pathname.split('?')[0].replace(/\/$/, '');
	return path || '/';
}

function pathMatches(href: string, path: string): boolean {
	if (href.includes('?')) return href === path;
	return path === href || path.startsWith(href + '/');
}

export function titleFromSlug(slug: string): string {
	return slug
		.replace(/_/g, ' ')
		.replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Human-readable extension name for UI (sidebar label when available).
 */
export function resolveExtensionLabel(
	extensionId: string,
	config: SidebarConfig | null,
): string {
	const segments = resolveBreadcrumb(`/extensions/${extensionId}`, config);
	return segments[segments.length - 1]?.label ?? titleFromSlug(extensionId);
}

export function extensionLoadingMessage(
	extensionId: string,
	config: SidebarConfig | null,
): string {
	return `Loading ${resolveExtensionLabel(extensionId, config)}...`;
}

function fallbackSegments(path: string): BreadcrumbSegment[] {
	if (path === '/') {
		return [];
	}

	const parts = path.split('/').filter(Boolean);
	const segments: BreadcrumbSegment[] = [];

	let accumulated = '';
	for (let i = 0; i < parts.length; i++) {
		accumulated += `/${parts[i]}`;
		const isLast = i === parts.length - 1;
		segments.push({
			label: titleFromSlug(parts[i]),
			href: isLast ? undefined : accumulated,
		});
	}

	return segments;
}

/**
 * Resolve breadcrumb trail for the current pathname using sidebar nav labels.
 */
export function resolveBreadcrumb(
	pathname: string,
	config: SidebarConfig | null,
): BreadcrumbSegment[] {
	const path = normalizePath(pathname);

	for (const item of topUtilityItems) {
		if (pathMatches(item.href, path)) {
			return [{ label: item.label }];
		}
	}

	if (config) {
		for (const item of config.welcomeItems) {
			if (pathMatches(item.href, path)) {
				return [{ label: item.label }];
			}
		}

		for (const item of config.mundusItems) {
			if (pathMatches(item.href, path)) {
				return [{ label: item.label }];
			}
		}

		for (const category of config.categories) {
			for (const item of category.items) {
				if (pathMatches(item.href, path)) {
					return [{ label: category.label }, { label: item.label }];
				}
			}
		}
	}

	const extensionMatch = path.match(/^\/extensions\/([^/]+)/);
	if (extensionMatch) {
		const extId = extensionMatch[1];
		const label = titleFromSlug(extId);
		return [{ label }];
	}

	return fallbackSegments(path);
}
