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

const IFRAME_ONLY_PARAMS = ['portal', 'slug'];
/** Kept on iframe + portal URLs so `/join?ti=1` survives host pathname-only syncs. */
const TEST_IDENTITY_PARAMS = ['ti', 'skip_ii', 'test_mode'];
const STICKY_PARAMS = [...IFRAME_ONLY_PARAMS, ...TEST_IDENTITY_PARAMS];

function meaningfulSearch(params: URLSearchParams): string {
  const copy = new URLSearchParams(params);
  for (const key of IFRAME_ONLY_PARAMS) copy.delete(key);
  copy.sort();
  return copy.toString();
}

/**
 * Build the in-iframe URL for a portal `nav:sync`, keeping iframe-only query
 * params (`portal=1`, `slug=…`) that the host path does not carry.
 *
 * Comparing host `/join` to iframe `/join?portal=1&slug=x` as unequal used to
 * `goto('/join')`, strip the embed flags, and reload the iframe in a loop.
 */
export function resolvePortalNavSyncHref(
  currentPathSearchHash: string,
  syncPath: string,
): string | null {
  if (!syncPath) return null;
  const current = new URL(currentPathSearchHash, 'https://portal.invalid');
  const target = new URL(syncPath, 'https://portal.invalid');
  const nextParams = new URLSearchParams(target.search);
  for (const key of STICKY_PARAMS) {
    if (nextParams.has(key)) continue;
    const value = current.searchParams.get(key);
    if (value != null) nextParams.set(key, value);
  }
  // Host syncs are pathname-only (`/join`). Do not clobber iframe-only params,
  // invite codes, or hashes the embed already has.
  if (current.pathname === target.pathname) {
    const targetMeaningful = meaningfulSearch(target.searchParams);
    const currentMeaningful = meaningfulSearch(current.searchParams);
    const hashUnchanged = !target.hash || target.hash === current.hash;
    if ((!targetMeaningful || targetMeaningful === currentMeaningful) && hashUnchanged) {
      return null;
    }
  }
  const qs = nextParams.toString();
  return `${target.pathname}${qs ? `?${qs}` : ''}${target.hash}`;
}
