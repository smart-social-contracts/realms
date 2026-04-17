/**
 * Runtime extension frontend loader.
 *
 * Loads an extension's compiled JS bundle from the file_registry canister
 * over HTTP and mounts it into a DOM target — without rebuilding realm_frontend.
 *
 * See Issue #168 Layer 2 (runtime extensions). The corresponding backend
 * code is loaded by realm_backend from the same file_registry namespace
 * (`ext/<id>/<version>/backend/`). This module loads the frontend half
 * (`ext/<id>/<version>/frontend/dist/index.js`).
 *
 * Extension bundle contract:
 *   The file at `frontend/dist/index.js` MUST be a valid ES module that
 *   exports a default `mount(target: HTMLElement, props: object)` function
 *   returning an optional `unmount()` function.
 *
 * In production this bundle would typically be produced by a per-extension
 * `vite build --lib` step; any framework (Svelte/React/vanilla) is fine
 * as long as it compiles to a self-contained ESM.
 */

export interface ExtensionManifest {
  id?: string;
  name: string;
  version?: string;
  description?: string;
  [key: string]: unknown;
}

export interface MountResult {
  unmount?: () => void;
}

export type MountFn = (
  target: HTMLElement,
  props?: Record<string, unknown>,
) => MountResult | void | Promise<MountResult | void>;

export interface ExtensionFrontendInfo {
  registryCanisterId: string;
  version: string;
  namespace: string; // e.g. "ext/test_bench/0.1.3"
  frontendPath: string; // e.g. "frontend/dist/index.js"
}

/**
 * Build the HTTP base URL for a file_registry canister, valid for both
 * local `dfx` (subdomain on localhost) and production ICP gateways.
 *
 * Exported because the i18n loader (`$lib/i18n`) needs to fetch translation
 * JSON from the same canister using the same URL convention.
 */
export function fileRegistryBaseUrlFor(canisterId: string): string {
  const host = typeof window !== 'undefined' ? window.location.host : '';
  const isLocal = host.includes('localhost') || host.includes('127.0.0.1');

  if (isLocal) {
    const port = host.split(':')[1] ?? '4943';
    return `http://${canisterId}.localhost:${port}`;
  }
  return `https://${canisterId}.icp0.io`;
}

/**
 * Resolve the file_registry canister id to use for a given extension.
 *
 * Preferred source: realm_backend's `get_extension_frontend_info`, which
 * returns the registry the extension was actually installed from. This
 * means realm_frontend does NOT need the registry id baked in at build
 * time, and can correctly load extensions installed from any registry.
 *
 * Fallback: build-time `CANISTER_ID_FILE_REGISTRY` (set by `dfx deploy`),
 * used during the bootstrap window before the realm has any extensions
 * installed and during local development.
 */
async function resolveFrontendInfo(
  backend: { get_extension_frontend_info?: (args: string) => Promise<string> },
  extId: string,
): Promise<ExtensionFrontendInfo> {
  if (typeof backend?.get_extension_frontend_info === 'function') {
    try {
      const raw = await backend.get_extension_frontend_info(
        JSON.stringify({ extension_id: extId }),
      );
      const parsed = JSON.parse(raw);
      if (parsed?.success && parsed.registry_canister_id) {
        return {
          registryCanisterId: parsed.registry_canister_id,
          version: parsed.version ?? '',
          namespace: parsed.namespace ?? `ext/${extId}/${parsed.version ?? ''}`,
          frontendPath: parsed.frontend_path ?? 'frontend/dist/index.js',
        };
      }
    } catch (e) {
      // Backend may be older than this method — fall through to env fallback.
      console.warn('[extension-loader] get_extension_frontend_info failed, using env fallback:', e);
    }
  }

  const fallbackId: string | undefined =
    process.env.CANISTER_ID_FILE_REGISTRY ||
    (import.meta as any).env?.VITE_FILE_REGISTRY_CANISTER_ID;
  if (!fallbackId) {
    throw new Error(
      `Could not resolve file_registry for extension '${extId}': backend ` +
        `did not return source info and CANISTER_ID_FILE_REGISTRY is unset.`,
    );
  }
  return {
    registryCanisterId: fallbackId,
    version: '',
    namespace: `ext/${extId}`,
    frontendPath: 'frontend/dist/index.js',
  };
}

/**
 * Resolve an extension's installed version by querying the realm_backend.
 * Returns undefined if the extension is not installed.
 */
export async function resolveExtensionVersion(
  backend: {
    list_runtime_extensions: () => Promise<string>;
  },
  extId: string,
): Promise<string | undefined> {
  const raw = await backend.list_runtime_extensions();
  const parsed = JSON.parse(raw);
  const manifest = parsed?.all_manifests?.[extId];
  return manifest?.version;
}

/**
 * Fetch and dynamically import an extension's compiled frontend bundle,
 * then call its default export to mount it into `target`.
 *
 * Bundle URL is built from realm_backend's `get_extension_frontend_info`:
 *   {fileRegistryBase}/{namespace}/{frontendPath}
 *   = {fileRegistryBase}/ext/{extId}/{version}/frontend/dist/index.js
 *
 * `version` is used to override what the backend returns when set (e.g.
 * for development pinning); otherwise the backend-resolved version wins.
 */
export async function mountExtension(
  extId: string,
  version: string,
  target: HTMLElement,
  props: Record<string, unknown> = {},
): Promise<MountResult | void> {
  const backend: any = (props as any)?.backend;
  const info = await resolveFrontendInfo(backend, extId);

  const ver = info.version || version;
  const namespace = info.version ? info.namespace : `ext/${extId}/${ver}`;
  const base = fileRegistryBaseUrlFor(info.registryCanisterId);
  const bundleUrl = `${base}/${namespace}/${info.frontendPath}`;

  // Browsers require explicit module specifier for dynamic import.
  // The /* @vite-ignore */ prevents Vite from trying to statically analyse/bundle this URL.
  const mod = await import(/* @vite-ignore */ bundleUrl);

  const mount: MountFn | undefined = mod?.default ?? mod?.mount;
  if (typeof mount !== 'function') {
    throw new Error(
      `Extension '${extId}@${ver}' bundle does not export a default mount() function`,
    );
  }

  return await mount(target, props);
}

export const _internal = { fileRegistryBaseUrlFor, resolveFrontendInfo };
