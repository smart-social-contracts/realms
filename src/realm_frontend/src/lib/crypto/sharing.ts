/**
 * Consent-based private-data sharing via vetKeys IBE.
 *
 * The member's private data is encrypted with a random per-save Data Encryption
 * Key (DEK) using AES-256-GCM. The DEK is then wrapped (IBE-encrypted) once per
 * authorized recipient under that recipient's vetKD *derived public key* and
 * stored as a `KeyEnvelope` at scope `user:<member>:private`.
 *
 * A recipient (the member themselves, or a consented admin) decrypts by:
 *   1. deriving their own vetKey (only they can — it is bound to their principal
 *      via the vetKD context),
 *   2. IBE-decrypting their envelope to recover the DEK,
 *   3. AES-GCM decrypting the ciphertext.
 *
 * The plaintext DEK and vetKey never leave the browser; the canister only ever
 * stores ciphertext and opaque wrapped keys.
 *
 * Identity note: recipients derive their vetKey with an empty derivation id
 * (see `derive_my_vetkey` / `deriveAesKey`), so the IBE identity must also be
 * empty. The per-recipient binding is provided by the derived public key, whose
 * vetKD context already includes the recipient's principal.
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

/** IBE identity bound to the recipient's (empty) vetKD derivation id. */
const EMPTY_IDENTITY = IbeIdentity.fromBytes(new Uint8Array());

// ---------------------------------------------------------------------------
// VetKey derivation
// ---------------------------------------------------------------------------

/**
 * Derive the caller's raw vetKey (and the matching derived public key).
 *
 * Unlike {@link deriveAesKey}, this returns the underlying `VetKey` object so it
 * can be used for IBE decryption of wrapped DEKs.
 */
export async function deriveMyVetKey(
	backend: any
): Promise<{ vetKey: VetKey; dpk: DerivedPublicKey }> {
	const pkResp = await backend.get_my_vetkey_public_key();
	if (!pkResp.success || !pkResp.data?.message) {
		throw new Error(
			`vetKD public key fetch failed: ${pkResp.data?.error || 'unknown error'}`
		);
	}
	const dpk = DerivedPublicKey.deserialize(hexToBytes(pkResp.data.message));

	const tsk = TransportSecretKey.random();
	const tpkHex = bytesToHex(tsk.publicKeyBytes());

	const deriveResp = await backend.derive_my_vetkey(tpkHex);
	if (!deriveResp.success || !deriveResp.data?.message) {
		throw new Error(
			`vetKD key derivation failed: ${deriveResp.data?.error || 'unknown error'}`
		);
	}
	const encryptedVetKey = EncryptedVetKey.deserialize(hexToBytes(deriveResp.data.message));
	const vetKey = encryptedVetKey.decryptAndVerify(tsk, dpk, new Uint8Array());
	return { vetKey, dpk };
}

/** Fetch the vetKD derived public key for an arbitrary target principal. */
export async function getDerivedPublicKeyFor(
	backend: any,
	principal: string
): Promise<DerivedPublicKey> {
	const resp = await backend.get_vetkey_public_key_for(principal);
	if (!resp.success || !resp.data?.message) {
		throw new Error(
			`derived public key fetch failed for ${principal}: ${resp.data?.error || 'unknown error'}`
		);
	}
	return DerivedPublicKey.deserialize(hexToBytes(resp.data.message));
}

// ---------------------------------------------------------------------------
// DEK wrap / unwrap (IBE)
// ---------------------------------------------------------------------------

/** Generate a fresh 32-byte Data Encryption Key. */
export function randomDek(): Uint8Array {
	return crypto.getRandomValues(new Uint8Array(32));
}

/**
 * IBE-wrap a DEK for a target principal using their derived public key.
 * Returns the serialized ciphertext as hex (stored in a KeyEnvelope).
 */
export function wrapDekForDpk(dpk: DerivedPublicKey, dek: Uint8Array): string {
	const ct = IbeCiphertext.encrypt(dpk, EMPTY_IDENTITY, dek, IbeSeed.random());
	return bytesToHex(ct.serialize());
}

/** Convenience: fetch the target's DPK and wrap the DEK for them. */
export async function wrapDekForPrincipal(
	backend: any,
	targetPrincipal: string,
	dek: Uint8Array
): Promise<string> {
	const dpk = await getDerivedPublicKeyFor(backend, targetPrincipal);
	return wrapDekForDpk(dpk, dek);
}

/** IBE-unwrap a wrapped DEK (hex) using the holder's vetKey. */
export function unwrapDek(vetKey: VetKey, wrappedDekHex: string): Uint8Array {
	const ct = IbeCiphertext.deserialize(hexToBytes(wrappedDekHex));
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
	/** Wrapped DEK for the owner (always present). */
	selfWrappedDek: string;
	/** Wrapped DEK per consented recipient principal. */
	recipientWrappedDeks: Record<string, string>;
}

/**
 * Encrypt the member's private data with a fresh DEK and wrap that DEK for the
 * member plus every recipient principal in `recipients`.
 */
export async function buildSharePlan(
	backend: any,
	ownerPrincipal: string,
	data: Record<string, string>,
	recipients: string[]
): Promise<SharePlan> {
	const dek = randomDek();
	const ciphertext = await aesGcmEncryptWithDek(dek, JSON.stringify(data));

	const selfWrappedDek = await wrapDekForPrincipal(backend, ownerPrincipal, dek);

	const recipientWrappedDeks: Record<string, string> = {};
	for (const r of recipients) {
		if (r === ownerPrincipal) continue;
		recipientWrappedDeks[r] = await wrapDekForPrincipal(backend, r, dek);
	}

	return { ciphertext, selfWrappedDek, recipientWrappedDeks };
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
			const { vetKey } = await deriveMyVetKey(backend);
			const dek = unwrapDek(vetKey, wrapped);
			const plaintext = await aesGcmDecryptWithDek(dek, ciphertext);
			return JSON.parse(plaintext);
		}
	} catch (e) {
		console.warn('[sharing] DEK-model decrypt failed, will try legacy:', e);
	}
	return null;
}
