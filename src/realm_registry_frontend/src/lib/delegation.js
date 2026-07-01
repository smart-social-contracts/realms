import { Principal } from '@dfinity/principal';

const DELEGATION_TTL_MS = 55 * 60 * 1000;

/**
 * Mint an II delegation scoped to a single backend canister for iframe handoff.
 * @param {import('@dfinity/agent').Identity} identity
 * @param {string} backendCanisterId
 * @param {Uint8Array} sessionPublicKeyDer
 */
export async function createScopedDelegation(identity, backendCanisterId, sessionPublicKeyDer) {
	const { DelegationChain, Ed25519PublicKey } = await import('@dfinity/identity');
	const backend = Principal.fromText(backendCanisterId);
	const sessionPublicKey = Ed25519PublicKey.fromDer(sessionPublicKeyDer);
	const expiration =
		BigInt(Date.now() + DELEGATION_TTL_MS) * BigInt(1_000_000);
	const delegation = await identity.delegate(sessionPublicKey, expiration, {
		targets: [backend]
	});
	const chain = DelegationChain.fromDelegations(
		[delegation],
		identity.getPublicKey().toDer()
	);
	return {
		delegationChain: chain.toJSON(),
		backendCanisterId,
		expiresAt: Date.now() + DELEGATION_TTL_MS
	};
}
