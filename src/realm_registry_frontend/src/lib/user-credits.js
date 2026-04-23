/**
 * Spendable credits = balance on `realm_registry_backend` (what deploy uses).
 *
 * We read the canister from the browser when possible. If that fails, we fall
 * back to the billing service GET `/credits/{principal}`, which calls the same
 * `get_credits` on the registry server-side.
 */
import { CONFIG } from '$lib/config.js';

export async function fetchUserCreditBalance(principalText) {
  if (!principalText) return 0;

  try {
    const { backend } = await import('$lib/canisters.js');
    const result = await backend.get_credits(principalText);
    if ('Ok' in result) {
      return Number(result.Ok.balance);
    }
  } catch (e) {
    console.warn(
      'fetchUserCreditBalance: canister get_credits failed, trying billing proxy',
      e
    );
  }

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
    console.error('fetchUserCreditBalance: billing proxy failed', e);
  }

  return 0;
}
