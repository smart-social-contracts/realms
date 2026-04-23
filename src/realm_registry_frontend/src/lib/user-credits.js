/**
 * Resolve the user's credit balance for UI gating (deploy wizard, etc.).
 *
 * Prefer the billing service (same source as voucher top-ups and My Dashboard).
 * Fall back to realm_registry_backend.get_credits when billing is unreachable.
 */
import { CONFIG } from '$lib/config.js';

export async function fetchUserCreditBalance(principalText) {
  if (!principalText) return 0;

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
    console.warn('fetchUserCreditBalance: billing request failed, using canister', e);
  }

  try {
    const { backend } = await import('$lib/canisters.js');
    const result = await backend.get_credits(principalText);
    if ('Ok' in result) {
      return Number(result.Ok.balance);
    }
  } catch (e) {
    console.error('fetchUserCreditBalance: canister get_credits failed', e);
  }

  return 0;
}
