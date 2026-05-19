// Build-time + runtime configuration for the marketplace frontend.
//
// Values are injected by Vite at build time from the dfx-generated
// .env file (see vite.config.js: the ``CANISTER_*`` and ``DFX_*`` env
// vars are exposed via vite-plugin-environment).

const env = (typeof process !== 'undefined' && (process as any).env) || ({} as Record<string, string | undefined>);

function pick(...keys: string[]): string {
  for (const k of keys) {
    const v = env[k];
    if (v && String(v).trim() !== '') return String(v);
  }
  return '';
}

export const CONFIG = {
  // Internet Identity URL used by @dfinity/auth-client.
  // Defaults to mainnet II; local dev points the env var at the local II canister.
  internet_identity_url:
    pick('VITE_INTERNET_IDENTITY_URL') ||
    (pick('CANISTER_ID_INTERNET_IDENTITY')
      ? `http://${pick('CANISTER_ID_INTERNET_IDENTITY')}.localhost:4943`
      : 'https://identity.ic0.app'),

  // Marketplace + file_registry canister ids — primarily resolved via the
  // generated declarations module (declarations/marketplace_backend), but
  // exposed here for convenience (e.g. constructing file URLs).
  marketplace_canister_id: pick('CANISTER_ID_MARKETPLACE_BACKEND'),
  file_registry_canister_id: pick('CANISTER_ID_FILE_REGISTRY'),
  internet_identity_canister_id: pick('CANISTER_ID_INTERNET_IDENTITY'),

  // Off-chain billing service that handles credit-card → Stripe → license payment.
  // Plan §4.3.1 names this BILLING_SERVICE_URL; we also accept the
  // VITE_-prefixed form so it can be set per Vite's standard env-loader
  // convention without needing the dfx-style CANISTER_ prefix.
  billing_service_url:
    pick('BILLING_SERVICE_URL', 'VITE_BILLING_SERVICE_URL') || 'https://billing.realmsgos.dev',
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
