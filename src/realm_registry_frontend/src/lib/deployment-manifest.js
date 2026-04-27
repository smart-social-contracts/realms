import { CONFIG } from './config.js';

const REALMS_RELEASE_BASE =
  'https://github.com/smart-social-contracts/realms/releases/download';

/**
 * Fetch checksums.txt from a GitHub release and parse it into a map.
 * Returns e.g. { "realm_backend.wasm.gz": "sha256:abc...", ... }
 * Falls back to empty map on any error (non-blocking).
 */
async function fetchReleaseChecksums(tag) {
  try {
    const url = `${REALMS_RELEASE_BASE}/${tag}/checksums.txt`;
    const resp = await fetch(url);
    if (!resp.ok) return {};
    const text = await resp.text();
    const map = {};
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const [hash, filename] = trimmed.split(/\s+/);
      if (hash && filename) map[filename] = `sha256:${hash}`;
    }
    return map;
  } catch {
    return {};
  }
}

/** In-memory cache so we only fetch once per page load. */
let _checksumCache = null;
let _checksumCacheTag = '';

/**
 * Build `canister_artifacts` from a GitHub release tag.
 *
 * Fetches checksums.txt from the release to populate integrity hashes.
 * Falls back to empty checksums if the file isn't available yet.
 *
 * @param {string} tag - release tag, e.g. "v0.3.1"
 */
async function buildArtifactRefs(tag) {
  if (_checksumCacheTag !== tag) {
    _checksumCache = await fetchReleaseChecksums(tag);
    _checksumCacheTag = tag;
  }
  const cs = _checksumCache || {};
  return {
    realm: {
      backend: {
        wasm: {
          url: `${REALMS_RELEASE_BASE}/${tag}/realm_backend.wasm.gz`,
          checksum: cs['realm_backend.wasm.gz'] || '',
        },
      },
      frontend: {
        url: `${REALMS_RELEASE_BASE}/${tag}/realm_frontend.tar.gz`,
        checksum: cs['realm_frontend.tar.gz'] || '',
      },
    },
  };
}

/**
 * Build the JSON manifest for realm_registry_backend.request_deployment.
 *
 * @param {object} formData - create-realm wizard state
 * @param {string} network - e.g. staging, demo
 * @param {{ logo?: string, background?: string }} [brandingUrls]
 *   URLs returned by uploadBrandingFiles (deploy service).
 */
export async function buildRealmDeploymentManifest(formData, network, brandingUrls) {
  const name = (formData.name || '').trim();
  const lang = (formData.languages && formData.languages[0]) || 'en';

  let description = (formData.descriptions && formData.descriptions[lang]) || '';
  if (!description && formData.descriptions) {
    description =
      Object.values(formData.descriptions).find((s) => s && String(s).trim()) || '';
  }
  description = String(description).trim() || `Welcome to ${name}.`;

  let welcome_message = (formData.welcome_messages && formData.welcome_messages[lang]) || '';
  if (!welcome_message && formData.welcome_messages) {
    welcome_message =
      Object.values(formData.welcome_messages).find((s) => s && String(s).trim()) || '';
  }
  welcome_message =
    String(welcome_message).trim() || `Welcome to ${name}!`;

  const realm = {
    name,
    display_name: name,
    description,
    welcome_message,
    extensions: Array.isArray(formData.extensions) ? [...formData.extensions] : ['all'],
  };

  if (formData.codex_source === 'package' && formData.codex_package_name?.trim()) {
    realm.codex = {
      package: formData.codex_package_name.trim(),
      version: (formData.codex_package_version || 'latest').trim(),
    };
  } else {
    realm.codex = { package: 'syntropia', version: 'latest' };
  }

  if (formData.assistant) {
    realm.assistant = formData.assistant;
  }

  const tag = CONFIG.deploy_release_tag;
  const canister_artifacts = tag ? await buildArtifactRefs(tag) : undefined;

  const manifest = {
    name,
    network: network || 'staging',
    realm,
    ...(canister_artifacts && { canister_artifacts }),
  };

  const branding = {};
  if (brandingUrls?.logo) branding.logo = brandingUrls.logo;
  if (brandingUrls?.background) branding.background = brandingUrls.background;
  if (Object.keys(branding).length > 0) manifest.branding = branding;

  return manifest;
}
