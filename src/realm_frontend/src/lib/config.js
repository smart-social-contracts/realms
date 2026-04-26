// This file is generated during the build process - do not edit manually
// It contains canister IDs and other configuration for the application


export const CONFIG = {
  ckbtc_ledger_canister_id: 'mxzaz-hqaaa-aaaar-qaada-cai',
  ckbtc_indexer_canister_id: 'n5wcd-faaaa-aaaar-qaaea-cai',
  token_backend_canister_id: 'xbkkh-syaaa-aaaah-qq3ya-cai',
};

// --- TEST_MODE umbrella and sub-flags (see GitHub issue #157) ---
// TEST_MODE is the master switch. Sub-flags are only effective when TEST_MODE is true.
// Activation: URL param (?testmode=1), sessionStorage, or VITE_TEST_MODE env var.
// Once activated via URL, flags persist in sessionStorage for the browser session.

function _readFlag(envKey, urlParam) {
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env[envKey] === 'true') return true;
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

// Sub-flags — all disabled by default, even when TEST_MODE is true.
function _testFlag(envKey, urlParam) {
  if (!TEST_MODE) return false;
  return _readFlag(envKey, urlParam);
}

// Bypass Internet Identity with a deterministic Ed25519 identity (for Playwright).
export const TEST_MODE_II_BYPASS = _testFlag('VITE_TEST_MODE_II_BYPASS', 'ii_bypass');
// Allow users to self-register as administrators on the join page.
export const TEST_MODE_ADMIN_SELF_REGISTRATION = _testFlag('VITE_TEST_MODE_ADMIN_SELF_REGISTRATION', 'admin_self_reg');
// Populate realm with demo/fake data.
export const TEST_MODE_DEMO_DATA = _testFlag('VITE_TEST_MODE_DEMO_DATA', 'demo_data');
// Skip terms acceptance step on the join page.
export const TEST_MODE_SKIP_TERMS = _testFlag('VITE_TEST_MODE_SKIP_TERMS', 'skip_terms');

export const DEV_PORT = 8000;
