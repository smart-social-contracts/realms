/**
 * Normalize a raw canister pathname before building a federation portal URL.
 *
 * The static adapter fallback (`index.html`) can boot the realm SPA at internal
 * extension bundle paths (`/ext/{id}/…/index.html`). Those must never become
 * portal deep links — map them to the public extension route instead.
 */
export function normalizePortalRedirectPath(pathname: string): string {
  if (!pathname || pathname === '/') return '';
  const extMatch = pathname.match(/^\/ext\/([^/]+)(?:\/.*)?$/);
  if (extMatch) {
    return `/extensions/${extMatch[1]}`;
  }
  return pathname;
}
