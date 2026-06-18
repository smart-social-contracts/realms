/**
 * Runtime extension frontend loader.
 *
 * Loads an extension's compiled JS bundle from the realm's own frontend
 * asset canister at /ext/{id}/{version}/frontend/dist/index.js and mounts
 * it into a DOM target, without rebuilding realm_frontend.
 *
 * Extension bundle contract:
 *   The file at `frontend/dist/index.js` MUST be a valid ES module that
 *   exports a default `mount(target: HTMLElement, props: object)` function
 *   returning an optional `unmount()` function.
 */

import type {
  RealmExtensionContext,
  MountResult,
  ExtensionMountFn,
} from './realm-extension-sdk';

export type { MountResult, ExtensionMountFn as MountFn };

export interface ExtensionManifest {
  id?: string;
  name: string;
  version?: string;
  description?: string;
  [key: string]: unknown;
}

export interface ExtensionFrontendInfo {
  registryCanisterId: string;
  version: string;
  namespace: string;
  frontendPath: string;
}

/**
 * Build the HTTP base URL for a file_registry canister, valid for both
 * local `dfx` (subdomain on localhost) and production ICP gateways.
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

async function resolveFrontendInfo(
  backend: { get_extension_frontend_info?: (args: string) => Promise<string> },
  extId: string,
  /** From status().canisters (set on ctx.config by the host page) */
  fileRegistryFromRealmConfig?: string,
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
      console.warn('[extension-loader] get_extension_frontend_info failed, using env fallback:', e);
    }
  }

  const cfg = (fileRegistryFromRealmConfig ?? '').trim();
  const ids = (globalThis as unknown as { __CANISTER_IDS?: { file_registry?: string } })
    .__CANISTER_IDS;
  const fromGlobals = (ids?.file_registry ?? '').trim();
  const fallbackId: string | undefined =
    cfg ||
    fromGlobals ||
    process.env.CANISTER_ID_FILE_REGISTRY ||
    (import.meta as any).env?.VITE_FILE_REGISTRY_CANISTER_ID;
  if (!fallbackId) {
    throw new Error(
      `Could not resolve file_registry for extension '${extId}': backend ` +
        `did not return source info, realm config has no fileRegistryCanisterId, and CANISTER_ID_FILE_REGISTRY is unset.`,
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
 * The bundle is loaded from the realm's own frontend asset canister at
 * /ext/{id}/{version}/frontend/dist/index.js (same origin, certified).
 */
export async function mountExtension(
  extId: string,
  version: string,
  target: HTMLElement,
  ctx: RealmExtensionContext,
): Promise<MountResult | void> {
  const backend: any = ctx?.backend;
  let info = await resolveFrontendInfo(
    backend,
    extId,
    ctx?.config?.fileRegistryCanisterId,
  );
  let ver = info.version || version;

  const sameOriginPath = `/ext/${extId}/${ver}/frontend/dist/index.js`;
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  const sameOriginUrl = `${origin}${sameOriginPath}`;

  let mod: any;
  try {
    mod = await import(/* @vite-ignore */ sameOriginUrl);
  } catch (e) {
    // Stale version in cache — re-resolve from backend before registry fallback.
    if (typeof backend?.get_extension_frontend_info === 'function') {
      try {
        const fresh = await resolveFrontendInfo(
          backend,
          extId,
          ctx?.config?.fileRegistryCanisterId,
        );
        if (fresh.version && fresh.version !== ver) {
          ver = fresh.version;
          info = fresh;
          const retryUrl = `${origin}/ext/${extId}/${ver}/frontend/dist/index.js`;
          mod = await import(/* @vite-ignore */ retryUrl);
        }
      } catch {
        /* fall through to registry */
      }
    }
    if (!mod) {
      const ns = info.version
        ? info.namespace
        : `ext/${extId}/${ver}`;
      const base = fileRegistryBaseUrlFor(info.registryCanisterId);
      const fallbackUrl = `${base}/${ns}/${info.frontendPath}`;
      console.warn(
        `[extension-loader] Same-origin load failed for '${extId}', falling back to registry: ${fallbackUrl}`,
        e,
      );
      mod = await import(/* @vite-ignore */ fallbackUrl);
    }
  }

  const mount: ExtensionMountFn | undefined = mod?.default ?? mod?.mount;
  if (typeof mount !== 'function') {
    throw new Error(
      `Extension '${extId}@${ver}' bundle does not export a default mount() function`,
    );
  }

  return await mount(target, ctx);
}

export const _internal = { fileRegistryBaseUrlFor, resolveFrontendInfo };
