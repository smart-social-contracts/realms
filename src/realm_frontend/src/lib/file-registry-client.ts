/**
 * Lightweight HTTP client for talking to a `file_registry` canister from
 * the realm_frontend.
 *
 * Why HTTP and not candid? The file_registry canister exposes both:
 *   - candid query methods: list_extensions / list_codices / latest_version /
 *     get_extension_manifest (see src/file_registry/main.py)
 *   - HTTP routes: GET /api/extensions, GET /api/codices, GET /{namespace}/{path}
 *     (handled by `_handle_http` in the same file)
 *
 * The HTTP route is preferred here because:
 *   1. It works for any registry the realm is linked to without the
 *      realm_frontend having to bake every registry's candid actor into
 *      its bundle (the realm_frontend only ships the realm_backend actor).
 *   2. It re-uses the same URL scheme as `extension-loader.ts` —
 *      one helper (`fileRegistryBaseUrlFor`) covers both runtime bundle
 *      loading and registry browsing.
 *   3. The registry already adds permissive CORS headers in
 *      `_http_response`, so the browser can read the response directly.
 */
import { fileRegistryBaseUrlFor } from '$lib/extension-loader';

export interface RegistryExtension {
  ext_id: string;
  versions: string[];
  latest: string;
  manifest: Record<string, unknown> | null;
}

export interface RegistryCodex {
  codex_id: string;
  versions: string[];
  latest: string;
}

async function fetchJson<T>(url: string): Promise<T> {
  const resp = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status} from ${url}: ${await resp.text().catch(() => '')}`);
  }
  return (await resp.json()) as T;
}

/**
 * List every extension published in the given file_registry canister.
 * Returns the same shape as the candid `list_extensions` query.
 */
export async function listRegistryExtensions(
  registryCanisterId: string,
): Promise<RegistryExtension[]> {
  const base = fileRegistryBaseUrlFor(registryCanisterId);
  return fetchJson<RegistryExtension[]>(`${base}/api/extensions`);
}

/**
 * List every codex package published in the given file_registry canister.
 */
export async function listRegistryCodices(
  registryCanisterId: string,
): Promise<RegistryCodex[]> {
  const base = fileRegistryBaseUrlFor(registryCanisterId);
  return fetchJson<RegistryCodex[]>(`${base}/api/codices`);
}

/**
 * Compare two semver-ish version strings ("1.2.3", "0.1.0", "1.2.3-rc1").
 * Returns a negative number if a < b, positive if a > b, 0 if equal.
 *
 * This is a deliberately simple comparator (matching `_parse_semver` on the
 * registry side); pre-release tags compare lexically, which is enough for
 * the package-manager UI's "is the installed version older than the
 * registry's latest?" check.
 */
export function compareVersions(a: string, b: string): number {
  const pa = a.split('-', 1)[0].split('.').map((n) => parseInt(n, 10) || 0);
  const pb = b.split('-', 1)[0].split('.').map((n) => parseInt(n, 10) || 0);
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const x = pa[i] ?? 0;
    const y = pb[i] ?? 0;
    if (x !== y) return x - y;
  }
  // Same numeric prefix → fall back to lexical comparison of full string
  // so "1.0.0-rc1" < "1.0.0".
  if (a === b) return 0;
  return a < b ? -1 : 1;
}

export const _internal = { fetchJson };
