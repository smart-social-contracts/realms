// Build-time overrides: VITE_INTERNET_IDENTITY_URL, VITE_REALM_INSTALLER_CANISTER_ID,
// VITE_DEPLOY_QUEUE_NETWORK (e.g. staging, demo).

const viteEnv = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {};

// Mainnet Internet Identity canister URL: https://identity.ic0.app/
// Local Internet Identity URL format: http://<canister-id>.localhost:8000
export const CONFIG = {
  internet_identity_url: viteEnv.VITE_INTERNET_IDENTITY_URL || 'https://identity.ic0.app/',
  /**
   * Canonical Internet Identity derivation origin for the whole federation.
   * The registry is the canonical origin: it serves
   * `/.well-known/ii-alternative-origins` listing every realm frontend, so all
   * frontends that log in with this `derivationOrigin` resolve to ONE principal
   * per human (see issue #233). Defaults to the registry's own public origin per
   * environment; override with VITE_II_DERIVATION_ORIGIN. Empty string disables
   * pinning (legacy per-origin principals).
   */
  ii_derivation_origin:
    viteEnv.VITE_II_DERIVATION_ORIGIN ||
    ({
      // staging pins the registry frontend's own canister origin as the canonical
      // derivationOrigin (the public *.realmsgos.org domains aren't DNS-wired yet).
      // It serves /.well-known/ii-alternative-origins listing each realm frontend.
      staging: 'https://77243-aqaaa-aaaau-aggza-cai.icp0.io',
      demo: 'https://demo.realmsgos.org',
      test: 'https://test.realmsgos.org',
    }[viteEnv.VITE_DEPLOY_QUEUE_NETWORK || 'staging'] || ''),
  billing_service_url: viteEnv.VITE_BILLING_SERVICE_URL || 'https://billing.realmsgos.dev',
  /** realm_installer on the target network (staging default matches registry backend). */
  realm_installer_canister_id:
    viteEnv.VITE_REALM_INSTALLER_CANISTER_ID || 'lusjm-wqaaa-aaaau-ago7q-cai',
  /** Network field embedded in deployment manifests (registry → installer). */
  default_deploy_queue_network: viteEnv.VITE_DEPLOY_QUEUE_NETWORK || 'staging',
  /** GitHub release tag for realm canister artifacts (WASM + frontend tarball). */
  deploy_release_tag: viteEnv.VITE_DEPLOY_RELEASE_TAG || 'v0.4.0',
  /** Default realm version for wizard deploys (semver without v, or `main`). */
  default_deploy_version: viteEnv.VITE_DEFAULT_DEPLOY_VERSION || 'main',
  /** Casals section for new realm stands. */
  casals_section: viteEnv.VITE_CASALS_SECTION || 'Deployments',
  /**
   * SHA-256 hex checksums for release assets (no browser fetch — GitHub blocks CORS).
   * Updated by .github/workflows/release.yml alongside deploy_release_tag.
   */
  deploy_release_checksums: {
    'realm_backend.wasm.gz':
      viteEnv.VITE_DEPLOY_RELEASE_BACKEND_CHECKSUM ||
      'c9c38a714762fe56e53534c488e645351deb7905020001b408f054c034b5c408',
    'realm_frontend.tar.gz':
      viteEnv.VITE_DEPLOY_RELEASE_FRONTEND_CHECKSUM ||
      '58cf46349679f137c9e481aa7831d367ee14f0f6aba78de9b76a2385d5031406',
  },
  /** Base URL of the deploy service (legacy; no longer used for branding). */
  deploy_service_url: viteEnv.VITE_DEPLOY_SERVICE_URL || 'https://deploy.realmsgos.dev',
  /**
   * file_registry canister the wizard uploads branding directly to (decentralized,
   * browser → canister, no server). Resolved per deploy-queue network, overridable
   * via VITE_FILE_REGISTRY_CANISTER_ID. Keep in sync with cli .../commands/files.py.
   */
  file_registry_canister_id:
    viteEnv.VITE_FILE_REGISTRY_CANISTER_ID ||
    ({
      staging: 'iebdk-kqaaa-aaaau-agoxq-cai',
      demo: 'vi64l-3aaaa-aaaae-qj4va-cai',
      test: 'uq2mu-kaaaa-aaaah-avqcq-cai',
    }[viteEnv.VITE_DEPLOY_QUEUE_NETWORK || 'staging'] || ''),
  /** Shared marketplace backend — keep in sync with deployment-descriptors/*-mundus-layered.yml */
  marketplace_canister_id:
    viteEnv.VITE_MARKETPLACE_CANISTER_ID ||
    ({
      staging: 'jji3o-uyaaa-aaaah-qreja-cai',
      demo: 'ehyfg-wyaaa-aaaae-qg3qq-cai',
      test: '2wldc-niaaa-aaaad-qlxga-cai',
    }[viteEnv.VITE_DEPLOY_QUEUE_NETWORK || 'staging'] || ''),
};

export const DEV_PORT = 8000;

// --- TEST_MODE umbrella and sub-flags ---
// Activation: URL param (?testmode=1), sessionStorage, or VITE_TEST_MODE env var.

function _readFlag(envKey, urlParam) {
  if (viteEnv[envKey] === 'true') return true;
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    if (params.get(urlParam) === '1') {
      sessionStorage.setItem(urlParam, '1');
      return true;
    }
    if (sessionStorage.getItem(urlParam) === '1') return true;
  }
  return false;
}

export const TEST_MODE = _readFlag('VITE_TEST_MODE', 'testmode');

function _testFlag(envKey, urlParam) {
  if (!TEST_MODE) return false;
  return _readFlag(envKey, urlParam);
}

export const TEST_MODE_II_BYPASS = _testFlag('VITE_TEST_MODE_II_BYPASS', 'ii_bypass');

export const INVITATION_CODE_MODE = _readFlag('VITE_INVITATION_CODE_MODE', 'invitation_code_mode');
