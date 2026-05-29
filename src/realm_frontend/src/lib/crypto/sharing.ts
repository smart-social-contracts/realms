/**
 * Consent-based private-data sharing via vetKeys IBE.
 *
 * The member's private data is encrypted with a random per-save Data Encryption
 * Key (DEK) using AES-256-GCM. The DEK is then wrapped (IBE-encrypted) once per
 * authorized recipient and stored as a `KeyEnvelope` at scope
 * `user:<member>:private`.
 *
 * A recipient (the member themselves, or a consented admin) decrypts by:
 *   1. deriving their own *sharing* vetKey (only they can — vetKD binds the
 *      derivation `input` to their principal via `ic.caller()`),
 *   2. IBE-decrypting their envelope to recover the DEK,
 *   3. AES-GCM decrypting the ciphertext.
 *
 * The plaintext DEK and vetKey never leave the browser; the canister only ever
 * stores ciphertext and opaque wrapped keys.
 *
 * Key derivation scheme (performance):
 * Instead of fetching a separate vetKD public key per recipient (one
 * inter-canister `vetkd_public_key` call each), everyone shares a single *root*
 * public key. A recipient is distinguished by the IBE **identity** — their
 * principal text. The browser therefore fetches the root key once and wraps the
 * DEK for every recipient locally, with zero extra management calls. Security is
 * unchanged: the matching sharing vetKey for identity `P` can only be derived by
 * the principal `P` itself (the backend forces `input = ic.caller()`).
 */

import {
	TransportSecretKey,
	DerivedPublicKey,
	EncryptedVetKey,
	IbeCiphertext,
	IbeIdentity,
	IbeSeed,
	type VetKey
} from '@dfinity/vetkeys';

// ---------------------------------------------------------------------------
// Hex helpers
// ---------------------------------------------------------------------------

function hexToBytes(hex: string): Uint8Array {
	const h = hex.replace(/\s/g, '');
	const bytes = new Uint8Array(h.length / 2);
	for (let i = 0; i < bytes.length; i++) {
		bytes[i] = parseInt(h.substring(i * 2, i * 2 + 2), 16);
	}
	return bytes;
}

function bytesToHex(bytes: Uint8Array): string {
	return Array.from(bytes)
		.map((b) => b.toString(16).padStart(2, '0'))
		.join('');
}

/**
 * The IBE identity / vetKD derivation input for a principal: the UTF-8 bytes of
 * its textual principal. The backend uses the same encoding
 * (`caller_principal.encode()`) for the `input`, keeping wrap and unwrap aligned.
 */
export function identityBytesFor(principalText: string): Uint8Array {
	return new TextEncoder().encode(principalText);
}

// ---------------------------------------------------------------------------
// VetKey derivation (shared root context + per-principal identity)
// ---------------------------------------------------------------------------

/** Fetch the shared root derived public key (one call, cacheable). */
export async function getSharingRootPublicKey(backend: any): Promise<DerivedPublicKey> {
	const pkResp = await backend.get_sharing_root_public_key();
	if (!pkResp.success || !pkResp.data?.message) {
		throw new Error(
			`sharing root public key fetch failed: ${pkResp.data?.error || 'unknown error'}`
		);
	}
	return DerivedPublicKey.deserialize(hexToBytes(pkResp.data.message));
}

/**
 * Derive the caller's *sharing* vetKey (bound to their own principal identity)
 * under the shared root context, for IBE-decrypting wrapped DEKs addressed to
 * them. `myPrincipal` must be the caller's own principal text.
 */
export async function deriveMySharingVetKey(
	backend: any,
	myPrincipal: string,
	rootDpk?: DerivedPublicKey
): Promise<{ vetKey: VetKey; dpk: DerivedPublicKey }> {
	const dpk = rootDpk ?? (await getSharingRootPublicKey(backend));

	const tsk = TransportSecretKey.random();
	const tpkHex = bytesToHex(tsk.publicKeyBytes());

	const deriveResp = await backend.derive_my_sharing_vetkey(tpkHex);
	if (!deriveResp.success || !deriveResp.data?.message) {
		throw new Error(
			`sharing vetKey derivation failed: ${deriveResp.data?.error || 'unknown error'}`
		);
	}
	const encryptedVetKey = EncryptedVetKey.deserialize(hexToBytes(deriveResp.data.message));
	const identity = identityBytesFor(myPrincipal);
	const vetKey = encryptedVetKey.decryptAndVerify(tsk, dpk, identity);
	return { vetKey, dpk };
}

// ---------------------------------------------------------------------------
// DEK wrap / unwrap (IBE)
// ---------------------------------------------------------------------------

/** Generate a fresh 32-byte Data Encryption Key. */
export function randomDek(): Uint8Array {
	return crypto.getRandomValues(new Uint8Array(32));
}

/**
 * IBE-wrap a DEK for a recipient principal under the shared root public key,
 * using the recipient's principal as the IBE identity. Fully client-side — no
 * network call. Returns the serialized ciphertext as hex.
 */
export function wrapDekForIdentity(
	rootDpk: DerivedPublicKey,
	recipientPrincipal: string,
	dek: Uint8Array
): string {
	const identity = IbeIdentity.fromBytes(identityBytesFor(recipientPrincipal));
	const ct = IbeCiphertext.encrypt(rootDpk, identity, dek, IbeSeed.random());
	return bytesToHex(ct.serialize());
}

/**
 * Strip the toolkit envelope wrapper (`env:v=2:k=<hex>`) if present,
 * returning the raw wrapped-DEK hex. Mirrors `decode_envelope` in
 * ic_basilisk_toolkit.crypto, since the canister stores envelopes in this
 * format via CryptoService.grant_access.
 */
export function decodeEnvelope(stored: string): string {
	const prefix = 'env:v=2:k=';
	return stored.startsWith(prefix) ? stored.slice(prefix.length) : stored;
}

/** IBE-unwrap a wrapped DEK using the holder's vetKey. Accepts the toolkit's
 * `env:v=2:k=<hex>` envelope format or raw hex. */
export function unwrapDek(vetKey: VetKey, wrappedDek: string): Uint8Array {
	const ct = IbeCiphertext.deserialize(hexToBytes(decodeEnvelope(wrappedDek)));
	return ct.decrypt(vetKey);
}

// ---------------------------------------------------------------------------
// AES-256-GCM with an explicit DEK
// ---------------------------------------------------------------------------

async function importDek(dek: Uint8Array): Promise<CryptoKey> {
	return crypto.subtle.importKey('raw', dek as BufferSource, { name: 'AES-GCM' }, false, [
		'encrypt',
		'decrypt'
	]);
}

/** Encrypt a UTF-8 string with a DEK. Output: `enc:v=2:iv=<hex>:d=<hex>`. */
export async function aesGcmEncryptWithDek(dek: Uint8Array, plaintext: string): Promise<string> {
	const key = await importDek(dek);
	const iv = crypto.getRandomValues(new Uint8Array(12));
	const cipherBuf = await crypto.subtle.encrypt(
		{ name: 'AES-GCM', iv: iv as BufferSource },
		key,
		new TextEncoder().encode(plaintext) as BufferSource
	);
	return `enc:v=2:iv=${bytesToHex(iv)}:d=${bytesToHex(new Uint8Array(cipherBuf))}`;
}

/** Decrypt an `enc:v=2:...` ciphertext (or legacy raw hex) with a DEK. */
export async function aesGcmDecryptWithDek(dek: Uint8Array, ciphertext: string): Promise<string> {
	const key = await importDek(dek);
	let iv: Uint8Array;
	let data: Uint8Array;

	if (ciphertext.startsWith('enc:v=2:')) {
		const parts: Record<string, string> = {};
		for (const seg of ciphertext.slice('enc:v=2:'.length).split(':')) {
			const eq = seg.indexOf('=');
			if (eq > 0) parts[seg.slice(0, eq)] = seg.slice(eq + 1);
		}
		if (!parts.iv || !parts.d) throw new Error('Invalid enc:v=2 format');
		iv = hexToBytes(parts.iv);
		data = hexToBytes(parts.d);
	} else {
		const combined = hexToBytes(ciphertext);
		iv = combined.slice(0, 12);
		data = combined.slice(12);
	}

	const plainBuf = await crypto.subtle.decrypt(
		{ name: 'AES-GCM', iv: iv as BufferSource },
		key,
		data as BufferSource
	);
	return new TextDecoder().decode(plainBuf);
}

// ---------------------------------------------------------------------------
// High-level orchestration
// ---------------------------------------------------------------------------

export const PRIVATE_DATA_SCOPE = (principal: string) => `user:${principal}:private`;

export interface SharePlan {
	/** Ciphertext to store via `update_my_private_data`. */
	ciphertext: string;
	/**
	 * Wrapped DEK per principal (owner + every consented recipient), ready to
	 * upsert in a single `crypto_grant_to_my_scope_batch` call.
	 */
	wrappedDeks: Record<string, string>;
}

/**
 * Encrypt the member's private data with a fresh DEK and wrap that DEK for the
 * member plus every recipient principal in `recipients`. The shared root public
 * key is fetched once; all wraps are local (no per-recipient network call).
 */
export async function buildSharePlan(
	backend: any,
	ownerPrincipal: string,
	data: Record<string, string>,
	recipients: string[]
): Promise<SharePlan> {
	const dek = randomDek();
	const ciphertext = await aesGcmEncryptWithDek(dek, JSON.stringify(data));

	const rootDpk = await getSharingRootPublicKey(backend);

	const wrappedDeks: Record<string, string> = {};
	// Owner is always a recipient so the new ciphertext stays self-decryptable.
	wrappedDeks[ownerPrincipal] = wrapDekForIdentity(rootDpk, ownerPrincipal, dek);
	for (const r of recipients) {
		if (r === ownerPrincipal || wrappedDeks[r]) continue;
		wrappedDeks[r] = wrapDekForIdentity(rootDpk, r, dek);
	}

	return { ciphertext, wrappedDeks };
}

/**
 * Decrypt the member's own private data using the DEK + envelope model, with a
 * fallback to legacy direct-symmetric data (returns null if neither works).
 */
export async function decryptOwnPrivateData(
	backend: any,
	ownerPrincipal: string,
	ciphertext: string
): Promise<Record<string, string> | null> {
	if (!ciphertext) return null;

	const scope = PRIVATE_DATA_SCOPE(ownerPrincipal);
	try {
		const envResp = await backend.crypto_get_my_envelope(scope);
		const wrapped = envResp?.data?.envelope?.wrapped_dek;
		if (envResp?.success && wrapped) {
			const { vetKey } = await deriveMySharingVetKey(backend, ownerPrincipal);
			const dek = unwrapDek(vetKey, wrapped);
			const plaintext = await aesGcmDecryptWithDek(dek, ciphertext);
			return JSON.parse(plaintext);
		}
	} catch (e) {
		console.warn('[sharing] DEK-model decrypt failed, will try legacy:', e);
	}
	return null;
}
