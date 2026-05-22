// Build-time overrides: VITE_INTERNET_IDENTITY_URL, VITE_REALM_INSTALLER_CANISTER_ID,
// VITE_DEPLOY_QUEUE_NETWORK (e.g. staging, demo).

const viteEnv = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {};

// Mainnet Internet Identity canister URL: https://identity.ic0.app/
// Local Internet Identity URL format: http://<canister-id>.localhost:8000
export const CONFIG = {
  internet_identity_url: viteEnv.VITE_INTERNET_IDENTITY_URL || 'https://identity.ic0.app/',
  billing_service_url: viteEnv.VITE_BILLING_SERVICE_URL || 'https://billing.realmsgos.dev',
  /** realm_installer on the target network (staging default matches registry backend). */
  realm_installer_canister_id:
    viteEnv.VITE_REALM_INSTALLER_CANISTER_ID || 'lusjm-wqaaa-aaaau-ago7q-cai',
  /** Network field embedded in deployment manifests (registry → installer). */
  default_deploy_queue_network: viteEnv.VITE_DEPLOY_QUEUE_NETWORK || 'staging',
  /** GitHub release tag for realm canister artifacts (WASM + frontend tarball). */
  deploy_release_tag: viteEnv.VITE_DEPLOY_RELEASE_TAG || 'v0.3.6',
  /** Base URL of the deploy service (branding upload, etc.). */
  deploy_service_url: viteEnv.VITE_DEPLOY_SERVICE_URL || 'https://deploy.realmsgos.dev',
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
