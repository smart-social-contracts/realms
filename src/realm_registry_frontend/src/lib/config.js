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
  deploy_release_tag: viteEnv.VITE_DEPLOY_RELEASE_TAG || 'v0.3.2',
  /** Base URL of the deploy service (branding upload, etc.). */
  deploy_service_url: viteEnv.VITE_DEPLOY_SERVICE_URL || 'https://deploy.realmsgos.dev',
};

export const DEV_PORT = 8000;
