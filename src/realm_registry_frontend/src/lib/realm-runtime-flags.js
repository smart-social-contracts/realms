/**
 * Fetch runtime flags from a realm backend canister (anonymous query).
 * @param {string} backendCanisterId
 * @returns {Promise<{ test_mode_ii_bypass?: boolean } | null>}
 */
export async function fetchRealmRuntimeFlags(backendCanisterId) {
  if (!backendCanisterId || typeof window === 'undefined') return null;
  try {
    const { HttpAgent, Actor } = await import('@dfinity/agent');
    const { IDL } = await import('@dfinity/candid');
    const idlFactory = ({ IDL: I }) => {
      const RuntimeFlags = I.Record({
        test_mode: I.Bool,
        test_mode_ii_bypass: I.Bool,
        test_mode_user_self_registration: I.Bool,
        test_mode_demo_data: I.Bool,
        test_mode_skip_terms: I.Bool,
        test_mode_skip_passport_zkproof: I.Bool,
      });
      return I.Service({
        get_runtime_flags: I.Func([], [RuntimeFlags], ['query']),
      });
    };
    const agent = new HttpAgent({ host: 'https://icp0.io' });
    const actor = Actor.createActor(idlFactory, { agent, canisterId: backendCanisterId });
    const flags = await actor.get_runtime_flags();
    return flags || null;
  } catch (e) {
    console.warn('[portal] could not fetch realm runtime flags:', e);
    return null;
  }
}
