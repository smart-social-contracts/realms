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

function normalizeEmbeddedPath(pathname: string): string {
  const path = (pathname || '/').split('?')[0].replace(/\/$/, '');
  return path || '/';
}

/** Join / setup carry host-only query (`?ti=`); do not overwrite them on enter. */
function isHostOnlyQueryPath(pathname: string): boolean {
  const path = normalizeEmbeddedPath(pathname);
  return path === '/join' || path === '/setup' || path.startsWith('/join/') || path.startsWith('/setup/');
}

/**
 * After a full iframe reload (afterNavigate type `enter`), the portal address
 * bar can still show the previous route (e.g. /identities, member_dashboard)
 * while the iframe is already on /messages or another extension. Push when the
 * host told us its embedded path and it differs — skipping the matched case
 * preserves host-only query params like `?ti=` on first paint.
 */
export function shouldPortalEnterPush(
  iframePathname: string,
  hostEmbeddedPath: string | null | undefined,
): boolean {
  const iframe = normalizeEmbeddedPath(iframePathname);
  if (hostEmbeddedPath) {
    return iframe !== normalizeEmbeddedPath(hostEmbeddedPath);
  }
  // Old portal hosts omit `config.realm.path`. Mirror the iframe route after a
  // full reload so the bar does not stay on Account while Messages is on
  // screen (same for extension routes). Leave /join and /setup alone — that is
  // where pushing used to drop `?ti=`.
  return !isHostOnlyQueryPath(iframe);
}

/** Strip iframe-only query params before mirroring a path onto the portal bar. */
export function portalSharePathFromUrl(url: {
  pathname: string;
  search?: string;
  hash?: string;
}): string {
  const params = new URLSearchParams(url.search || '');
  for (const key of IFRAME_ONLY_PARAMS) params.delete(key);
  const qs = params.toString();
  return `${url.pathname}${qs ? `?${qs}` : ''}${url.hash || ''}`;
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
