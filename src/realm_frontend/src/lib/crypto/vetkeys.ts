/**
 * VetKeys crypto utilities for encrypting/decrypting user private data.
 *
 * Uses the IC's vetKD (Verifiably Encrypted Threshold Key Derivation) system
 * to derive a per-user AES-256-GCM symmetric key.  The plaintext key never
 * leaves the IC subnet; only a transport-encrypted version is sent to the
 * browser, where it is decrypted locally using an ephemeral BLS12-381 key pair.
 *
 * Flow:
 *   1. get_my_vetkey_public_key  → derived public key (hex)
 *   2. generate TransportSecretKey.random() (BLS12-381 G1, 48-byte compressed)
 *   3. derive_my_vetkey(tpk_hex) → encrypted vetKey (hex)
 *   4. EncryptedVetKey.decryptAndVerify(…)  → VetKey
 *   5. VetKey.deriveSymmetricKey(…)  → 32-byte AES-256-GCM key
 *   6. AES-GCM encrypt / decrypt
 */

import {
	TransportSecretKey,
	DerivedPublicKey,
	EncryptedVetKey
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

// ---------------------------------------------------------------------------
// Key derivation
// ---------------------------------------------------------------------------

/** Domain separator for symmetric key derivation from VetKey. */
const AES_GCM_DOMAIN_SEP = 'aes-256-gcm-realms-private-data';

/**
 * Derive a 32-byte AES-256-GCM key for the currently authenticated user.
 *
 * @param backend  The canister actor (must be authenticated).
 * @returns A `CryptoKey` ready for `encrypt` / `decrypt`.
 */
export async function deriveAesKey(backend: any): Promise<CryptoKey> {
	// 1. Fetch the vetKD derived public key for this user's context
	const pkResp = await backend.get_my_vetkey_public_key();
	if (!pkResp.success || !pkResp.data?.message) {
		throw new Error(
			`vetKD public key fetch failed: ${pkResp.data?.error || 'unknown error'}`
		);
	}
	const publicKeyHex: string = pkResp.data.message;
	console.log('vetKD public key hex:', publicKeyHex.substring(0, 80) + '...', 'hex len:', publicKeyHex.length, 'bytes:', publicKeyHex.length / 2);
	const publicKeyBytes = hexToBytes(publicKeyHex);
	const dpk = DerivedPublicKey.deserialize(publicKeyBytes);

	// 2. Generate ephemeral transport key pair (48-byte compressed G1)
	const tsk = TransportSecretKey.random();
	const tpkHex = bytesToHex(tsk.publicKeyBytes());

	// 3. Ask the canister to derive the encrypted key
	const deriveResp = await backend.derive_my_vetkey(tpkHex);
	if (!deriveResp.success || !deriveResp.data?.message) {
		throw new Error(
			`vetKD key derivation failed: ${deriveResp.data?.error || 'unknown error'}`
		);
	}
	const encryptedKeyBytes = hexToBytes(deriveResp.data.message);

	// 4. Decrypt & verify → VetKey (BLS signature)
	//    input is empty (matches backend input_hex="")
	const encryptedVetKey = EncryptedVetKey.deserialize(encryptedKeyBytes);
	const vetKey = encryptedVetKey.decryptAndVerify(tsk, dpk, new Uint8Array());

	// 5. Derive 32-byte symmetric key via HKDF
	const symmetricKeyRaw = vetKey.deriveSymmetricKey(AES_GCM_DOMAIN_SEP, 32);

	// 6. Import into Web Crypto
	return crypto.subtle.importKey('raw', symmetricKeyRaw, { name: 'AES-GCM' }, false, [
		'encrypt',
		'decrypt'
	]);
}

// ---------------------------------------------------------------------------
// AES-GCM encrypt / decrypt
// ---------------------------------------------------------------------------

/**
 * Encrypt a UTF-8 string with AES-256-GCM.
 *
 * Output format: `enc:v=2:iv=<12-byte-hex>:d=<ciphertext-hex>`
 * (basilisk OS standard ciphertext format)
 */
export async function aesGcmEncrypt(key: CryptoKey, plaintext: string): Promise<string> {
	const iv = crypto.getRandomValues(new Uint8Array(12));
	const encoded = new TextEncoder().encode(plaintext);
	const cipherBuf = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded);
	const cipher = new Uint8Array(cipherBuf);
	return `enc:v=2:iv=${bytesToHex(iv)}:d=${bytesToHex(cipher)}`;
}

/**
 * Decrypt a ciphertext string produced by `aesGcmEncrypt`.
 *
 * Accepts both:
 *   - New format: `enc:v=2:iv=<hex>:d=<hex>`
 *   - Legacy format: raw hex `<12-byte IV><ciphertext+tag>`
 */
export async function aesGcmDecrypt(key: CryptoKey, ciphertext: string): Promise<string> {
	let iv: Uint8Array;
	let data: Uint8Array;

	if (ciphertext.startsWith('enc:v=2:')) {
		// New basilisk OS format
		const parts: Record<string, string> = {};
		for (const seg of ciphertext.slice('enc:v=2:'.length).split(':')) {
			const eq = seg.indexOf('=');
			if (eq > 0) parts[seg.slice(0, eq)] = seg.slice(eq + 1);
		}
		if (!parts.iv || !parts.d) throw new Error('Invalid enc:v=2 format');
		iv = hexToBytes(parts.iv);
		data = hexToBytes(parts.d);
	} else {
		// Legacy raw hex format
		const combined = hexToBytes(ciphertext);
		iv = combined.slice(0, 12);
		data = combined.slice(12);
	}

	const plainBuf = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, data);
	return new TextDecoder().decode(plainBuf);
}

// ---------------------------------------------------------------------------
// High-level helpers for the UI
// ---------------------------------------------------------------------------

/**
 * Encrypt a private-data JSON object for storage.
 *
 * Returns an `enc:v=2:iv=...:d=...` string for `update_my_private_data`.
 */
export async function encryptPrivateData(
	backend: any,
	data: Record<string, string>
): Promise<string> {
	const key = await deriveAesKey(backend);
	return aesGcmEncrypt(key, JSON.stringify(data));
}

/**
 * Decrypt a stored private-data blob back into a JSON object.
 *
 * Accepts both `enc:v=2:…` format and legacy raw hex.
 * Returns `null` if the data is empty or decryption fails (e.g. legacy
 * unencrypted data).
 */
export async function decryptPrivateData(
	backend: any,
	ciphertextOrHex: string
): Promise<Record<string, string> | null> {
	if (!ciphertextOrHex) return null;

	// New format check
	const isEncV2 = ciphertextOrHex.startsWith('enc:v=2:');
	if (!isEncV2 && ciphertextOrHex.length < 26) {
		// Too short to be iv+ciphertext; likely empty or legacy plaintext
		return null;
	}

	const key = await deriveAesKey(backend);
	try {
		const plaintext = await aesGcmDecrypt(key, ciphertextOrHex);
		return JSON.parse(plaintext);
	} catch {
		// Decryption or parsing failed — probably legacy unencrypted JSON
		return null;
	}
}
