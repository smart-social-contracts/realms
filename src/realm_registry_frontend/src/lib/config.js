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
};

export const DEV_PORT = 8000;
