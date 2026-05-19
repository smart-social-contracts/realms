const env =
  (typeof process !== 'undefined' && (process as any).env) || ({} as Record<string, string | undefined>);

function pick(...keys: string[]): string {
  for (const k of keys) {
    const v = env[k];
    if (v && String(v).trim() !== '') return String(v);
  }
  return '';
}

export const CONFIG = {
  internet_identity_url:
    pick('VITE_INTERNET_IDENTITY_URL') ||
    (pick('CANISTER_ID_INTERNET_IDENTITY')
      ? `http://${pick('CANISTER_ID_INTERNET_IDENTITY')}.localhost:4943`
      : 'https://identity.ic0.app'),

  realm_registry_backend_id: pick('CANISTER_ID_REALM_REGISTRY_BACKEND'),
  realm_registry_frontend_id: pick('CANISTER_ID_REALM_REGISTRY_FRONTEND'),
  realm_installer_id: pick('CANISTER_ID_REALM_INSTALLER'),
  realm_installer_frontend_id: pick('CANISTER_ID_REALM_INSTALLER_FRONTEND'),
  file_registry_id: pick('CANISTER_ID_FILE_REGISTRY'),
  file_registry_frontend_id: pick('CANISTER_ID_FILE_REGISTRY_FRONTEND'),
  marketplace_backend_id: pick('CANISTER_ID_MARKETPLACE_BACKEND'),
  marketplace_frontend_id: pick('CANISTER_ID_MARKETPLACE_FRONTEND'),
  deploy_service_url: pick('VITE_DEPLOY_SERVICE_URL') || 'https://deploy.realmsgos.dev',
};

// --- TEST_MODE umbrella and sub-flags ---
// Activation: URL param (?testmode=1), sessionStorage, or VITE_TEST_MODE env var.

const _viteEnv: Record<string, string | undefined> =
  typeof import.meta !== 'undefined' && (import.meta as any).env ? (import.meta as any).env : {};

function _readFlag(envKey: string, urlParam: string): boolean {
  if (_viteEnv[envKey] === 'true') return true;
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

export const TEST_MODE: boolean = _readFlag('VITE_TEST_MODE', 'testmode');

function _testFlag(envKey: string, urlParam: string): boolean {
  if (!TEST_MODE) return false;
  return _readFlag(envKey, urlParam);
}

export const TEST_MODE_II_BYPASS: boolean = _testFlag('VITE_TEST_MODE_II_BYPASS', 'ii_bypass');

export function frontendUrl(canisterId: string): string {
  return `https://${canisterId}.icp0.io`;
}

export function candidUiUrl(canisterId: string): string {
  return `https://a4gq6-oaaaa-aaaab-qaa4q-cai.raw.icp0.io/?id=${canisterId}`;
}

export function icDashboardUrl(canisterId: string): string {
  return `https://dashboard.internetcomputer.org/canister/${canisterId}`;
}

export function shortId(id: string): string {
  if (id.length <= 15) return id;
  return id.slice(0, 7) + '...' + id.slice(-5);
}
