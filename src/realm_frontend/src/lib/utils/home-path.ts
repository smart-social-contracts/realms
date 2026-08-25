import { resolveMemberHomeHref, type SidebarHomeInput } from '../extension-home';

/**
 * Host-only wrapper: extensions emit `navigate.home`; the host resolves
 * `/extensions/[id]` from get_sidebar_manifests() / MY REALM rows.
 */
export function resolveHomePath(input: SidebarHomeInput | null | undefined): string {
	return resolveMemberHomeHref(input);
}
