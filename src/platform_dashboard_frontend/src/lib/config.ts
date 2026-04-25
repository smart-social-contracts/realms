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
  deploy_service_url: pick('VITE_DEPLOY_SERVICE_URL') || '',
};

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
