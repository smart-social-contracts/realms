/**
 * Runtime extension frontend loader.
 *
 * Loads an extension's compiled JS bundle from the realm's own frontend
 * asset canister at /ext/{id}/{version}/frontend/dist/index.js and mounts
 * it into a DOM target, without rebuilding realm_frontend.
 *
 * Extension bundles are copied to the realm frontend at install time
 * (install_extension_from_registry). There is no runtime fallback to
 * file_registry — if the same-origin bundle is missing, load fails.
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

async function resolveInstalledVersion(
  backend: { get_extension_frontend_info?: (args: string) => Promise<string> },
  extId: string,
  fallbackVersion: string,
): Promise<string> {
  if (typeof backend?.get_extension_frontend_info === 'function') {
    try {
      const raw = await backend.get_extension_frontend_info(
        JSON.stringify({ extension_id: extId }),
      );
      const parsed = JSON.parse(raw);
      if (parsed?.success && parsed.version) {
        return parsed.version;
      }
    } catch (e) {
      console.warn('[extension-loader] get_extension_frontend_info failed:', e);
    }
  }
  return fallbackVersion;
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
  const ver = await resolveInstalledVersion(backend, extId, version);

  const sameOriginPath = `/ext/${extId}/${ver}/frontend/dist/index.js`;
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  const sameOriginUrl = `${origin}${sameOriginPath}`;

  const mod = await import(/* @vite-ignore */ sameOriginUrl);

  const mount: ExtensionMountFn | undefined = mod?.default ?? mod?.mount;
  if (typeof mount !== 'function') {
    throw new Error(
      `Extension '${extId}@${ver}' bundle does not export a default mount() function`,
    );
  }

  return await mount(target, ctx);
}
