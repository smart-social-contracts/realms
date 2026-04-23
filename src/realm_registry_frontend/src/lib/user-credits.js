/**
 * Credit balances come from two places:
 * - **Registry** (`realm_registry_backend.get_credits`): on-chain balance; this is what
 *   `request_deployment` and other canister methods spend.
 * - **Billing** (HTTP `/credits/{principal}`): Stripe / account ledger; can differ until
 *   vouchers or webhooks call `add_credits` on the registry.
 */
import { CONFIG } from '$lib/config.js';

export async function fetchRegistryCreditBalance(principalText) {
  if (!principalText) return 0;
  try {
    const { backend } = await import('$lib/canisters.js');
    const result = await backend.get_credits(principalText);
    if ('Ok' in result) {
      return Number(result.Ok.balance);
    }
  } catch (e) {
    console.error('fetchRegistryCreditBalance: get_credits failed', e);
  }
  return 0;
}

/** @returns {Promise<number|null>} Credits from billing API, or null if unavailable */
export async function fetchBillingCreditBalance(principalText) {
  if (!principalText) return null;
  const billingUrl =
    CONFIG.billing_service_url || 'https://billing.realmsgos.dev';
  try {
    const br = await fetch(
      `${billingUrl}/credits/${encodeURIComponent(principalText)}`
    );
    if (br.ok) {
      const j = await br.json();
      if (j && j.credits != null) {
        return Number(j.credits);
      }
    }
  } catch (e) {
    console.warn('fetchBillingCreditBalance: request failed', e);
  }
  return null;
}

/**
 * On-chain credits usable for deployment and other registry spend.
 * Prefer this for gating `request_deployment` and similar calls.
 */
export async function fetchUserCreditBalance(principalText) {
  return fetchRegistryCreditBalance(principalText);
}

/** Both sources — use when explaining billing vs registry drift in the UI. */
export async function fetchCreditBalances(principalText) {
  const [registry, billing] = await Promise.all([
    fetchRegistryCreditBalance(principalText),
    fetchBillingCreditBalance(principalText),
  ]);
  return { registry, billing };
}
