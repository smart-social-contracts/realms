import { describe, it, expect } from 'vitest';
import { bls12_381 } from '@noble/curves/bls12-381';
import {
	augmentedHashToG1,
	DerivedPublicKey,
	VetKey,
	IbeIdentity,
	IbeCiphertext,
	IbeSeed
} from '@dfinity/vetkeys';
import {
	aesGcmEncryptWithDek,
	aesGcmDecryptWithDek,
	decodeEnvelope,
	identityBytesFor,
	randomDek,
	unwrapDek,
	wrapDekForIdentity,
	buildSharePlan
} from './sharing';

/**
 * Build a *local* vetKD keypair so we can exercise the real IBE wrap/unwrap
 * path without a replica. A DerivedPublicKey is `sk·G2`; the vetKey for an
 * identity is the BLS signature `sk·augmentedHashToG1(dpk, identity)`.
 *
 * This mirrors exactly what the management canister produces, so it faithfully
 * tests the encrypt-to-identity / decrypt-with-own-vetkey contract that our
 * root-key sharing scheme relies on.
 */
function makeRootKeypair() {
	const G2 = bls12_381.G2.ProjectivePoint;
	const r = bls12_381.params.r;
	// Deterministic-ish random scalar in [1, r).
	const bytes = crypto.getRandomValues(new Uint8Array(32));
	let sk = 0n;
	for (const b of bytes) sk = (sk << 8n) | BigInt(b);
	sk = (sk % (r - 1n)) + 1n;
	const dpk = new DerivedPublicKey(G2.BASE.multiply(sk));
	const vetKeyForIdentity = (identityBytes: Uint8Array): VetKey =>
		new VetKey(augmentedHashToG1(dpk, identityBytes).multiply(sk));
	return { dpk, vetKeyForIdentity };
}

const ALICE = 'aaaaa-aa';
const BOB = 'bbbbb-bb';

describe('identityBytesFor', () => {
	it('is the UTF-8 encoding of the principal text', () => {
		expect(Array.from(identityBytesFor('abc'))).toEqual([97, 98, 99]);
	});
});

describe('decodeEnvelope', () => {
	it('strips the toolkit env:v=2:k= prefix', () => {
		expect(decodeEnvelope('env:v=2:k=deadbeef')).toBe('deadbeef');
	});
	it('passes raw hex through unchanged', () => {
		expect(decodeEnvelope('deadbeef')).toBe('deadbeef');
	});
});

describe('AES-256-GCM with an explicit DEK', () => {
	it('round-trips a UTF-8 string', async () => {
		const dek = randomDek();
		const ct = await aesGcmEncryptWithDek(dek, 'hello, world');
		expect(ct.startsWith('enc:v=2:')).toBe(true);
		expect(await aesGcmDecryptWithDek(dek, ct)).toBe('hello, world');
	});

	it('fails to decrypt with the wrong DEK', async () => {
		const ct = await aesGcmEncryptWithDek(randomDek(), 'secret');
		await expect(aesGcmDecryptWithDek(randomDek(), ct)).rejects.toBeDefined();
	});
});

describe('IBE wrap/unwrap under the shared root key', () => {
	it('round-trips a DEK for the addressed identity', () => {
		const { dpk, vetKeyForIdentity } = makeRootKeypair();
		const dek = randomDek();
		const wrapped = wrapDekForIdentity(dpk, ALICE, dek);
		const recovered = unwrapDek(vetKeyForIdentity(identityBytesFor(ALICE)), wrapped);
		expect(Array.from(recovered)).toEqual(Array.from(dek));
	});

	it('binds the ciphertext to the identity (a different principal cannot decrypt)', () => {
		const { dpk, vetKeyForIdentity } = makeRootKeypair();
		const wrapped = wrapDekForIdentity(dpk, ALICE, randomDek());
		// Bob derives his own (different) sharing vetKey and must NOT decrypt
		// data addressed to Alice.
		expect(() => unwrapDek(vetKeyForIdentity(identityBytesFor(BOB)), wrapped)).toThrow();
	});

	it('accepts the toolkit env:v=2:k= envelope format from the canister', () => {
		const { dpk, vetKeyForIdentity } = makeRootKeypair();
		const dek = randomDek();
		const wrappedHex = wrapDekForIdentity(dpk, ALICE, dek);
		// The canister stores the wrapped DEK via encode_envelope(...) → prefixed.
		const stored = `env:v=2:k=${wrappedHex}`;
		const recovered = unwrapDek(vetKeyForIdentity(identityBytesFor(ALICE)), stored);
		expect(Array.from(recovered)).toEqual(Array.from(dek));
	});
});

describe('end-to-end DEK + IBE', () => {
	it('encrypts data, wraps the DEK, then recovers the data via the vetKey', async () => {
		const { dpk, vetKeyForIdentity } = makeRootKeypair();
		const data = { first_name: 'Ada', email: 'ada@example.com' };

		const dek = randomDek();
		const ciphertext = await aesGcmEncryptWithDek(dek, JSON.stringify(data));
		const wrapped = wrapDekForIdentity(dpk, ALICE, dek);

		// Recipient side: unwrap DEK with their vetKey, then AES-decrypt.
		const recoveredDek = unwrapDek(vetKeyForIdentity(identityBytesFor(ALICE)), wrapped);
		const plaintext = await aesGcmDecryptWithDek(recoveredDek, ciphertext);
		expect(JSON.parse(plaintext)).toEqual(data);
	});
});

describe('buildSharePlan', () => {
	it('fetches the root key once and wraps for owner + each recipient (one map for batch grant)', async () => {
		const { dpk, vetKeyForIdentity } = makeRootKeypair();
		let rootCalls = 0;
		const backend = {
			async get_sharing_root_public_key() {
				rootCalls += 1;
				return {
					success: true,
					data: { message: bytesToHex(dpk.publicKeyBytes()) }
				};
			}
		};

		const data = { city: 'Lovelace' };
		const plan = await buildSharePlan(backend, ALICE, data, [BOB, ALICE]);

		// Exactly one management-style call regardless of recipient count.
		expect(rootCalls).toBe(1);
		// Owner is always present; recipient deduped (ALICE not doubled).
		expect(Object.keys(plan.wrappedDeks).sort()).toEqual([ALICE, BOB].sort());

		// Both owner and recipient can recover the same plaintext.
		for (const who of [ALICE, BOB]) {
			const dek = unwrapDek(vetKeyForIdentity(identityBytesFor(who)), plan.wrappedDeks[who]);
			expect(JSON.parse(await aesGcmDecryptWithDek(dek, plan.ciphertext))).toEqual(data);
		}
	});
});

function bytesToHex(bytes: Uint8Array): string {
	return Array.from(bytes)
		.map((b) => b.toString(16).padStart(2, '0'))
		.join('');
}
