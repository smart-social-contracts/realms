/**
 * VetKeys crypto utilities for encrypting/decrypting user private data.
 *
 * Uses the IC's vetKD (Verifiably Encrypted Threshold Key Derivation) system
 * to derive a per-user AES-256-GCM symmetric key.  The plaintext key never
 * leaves the IC subnet; only a transport-encrypted version is sent to the
 * browser, where it is decrypted locally using an ephemeral BLS12-381 key pair.
 *
 * Flow:
 *   1. get_my_vetkey_public_key  → IBE master public key (hex)
 *   2. generate TransportSecretKey (random 32-byte seed)
 *   3. derive_my_vetkey(tpk_hex) → encrypted symmetric key (hex)
 *   4. tsk.decrypt_and_hash(…)    → 32-byte AES-256-GCM key
 *   5. AES-GCM encrypt / decrypt
 */

// ---------------------------------------------------------------------------
// WASM initialisation  (ic-vetkd-utils is a wasm-pack crate)
// ---------------------------------------------------------------------------

let vetkdModule: typeof import('ic-vetkd-utils') | null = null;

async function getVetkdModule(): Promise<typeof import('ic-vetkd-utils')> {
	if (vetkdModule) return vetkdModule;

	const mod = await import('ic-vetkd-utils');
	// Initialise WASM – the .wasm file is served from /wasm/ in static/
	await mod.default('/wasm/ic_vetkd_utils_bg.wasm');
	vetkdModule = mod;
	return mod;
}

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

/** Associated data baked into the KDF so the key is bound to our cipher. */
const AES_GCM_AD = new TextEncoder().encode('aes-256-gcm-realms-private-data');

/**
 * Derive a 32-byte AES-256-GCM key for the currently authenticated user.
 *
 * @param backend  The canister actor (must be authenticated).
 * @returns A `CryptoKey` ready for `encrypt` / `decrypt`.
 */
export async function deriveAesKey(backend: any): Promise<CryptoKey> {
	const { TransportSecretKey } = await getVetkdModule();

	// 1. Fetch the vetKD public key for this user's context
	const pkResp = await backend.get_my_vetkey_public_key();
	if (!pkResp.success || !pkResp.data?.message) {
		throw new Error(
			`vetKD public key fetch failed: ${pkResp.data?.error || 'unknown error'}`
		);
	}
	const publicKeyHex: string = pkResp.data.message;
	const publicKeyBytes = hexToBytes(publicKeyHex);

	// 2. Generate ephemeral transport key pair
	const seed = crypto.getRandomValues(new Uint8Array(32));
	const tsk = new TransportSecretKey(seed);
	const tpkHex = bytesToHex(tsk.public_key());

	// 3. Ask the canister to derive the encrypted key
	const deriveResp = await backend.derive_my_vetkey(tpkHex);
	if (!deriveResp.success || !deriveResp.data?.message) {
		throw new Error(
			`vetKD key derivation failed: ${deriveResp.data?.error || 'unknown error'}`
		);
	}
	const encryptedKeyBytes = hexToBytes(deriveResp.data.message);

	// 4. Decrypt & hash → 32-byte symmetric key
	//    derivation_id is empty (matches backend input_hex="")
	const symmetricKeyRaw = tsk.decrypt_and_hash(
		encryptedKeyBytes,
		publicKeyBytes,
		new Uint8Array(), // derivation_id
		32, // 256 bits
		AES_GCM_AD
	);

	// 5. Import into Web Crypto
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
 * Output format (hex): `<12-byte IV><ciphertext+tag>`
 */
export async function aesGcmEncrypt(key: CryptoKey, plaintext: string): Promise<string> {
	const iv = crypto.getRandomValues(new Uint8Array(12));
	const encoded = new TextEncoder().encode(plaintext);
	const cipherBuf = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, encoded);
	const cipher = new Uint8Array(cipherBuf);
	const combined = new Uint8Array(iv.length + cipher.length);
	combined.set(iv);
	combined.set(cipher, iv.length);
	return bytesToHex(combined);
}

/**
 * Decrypt a hex blob produced by `aesGcmEncrypt`.
 */
export async function aesGcmDecrypt(key: CryptoKey, ciphertextHex: string): Promise<string> {
	const combined = hexToBytes(ciphertextHex);
	const iv = combined.slice(0, 12);
	const ciphertext = combined.slice(12);
	const plainBuf = await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, ciphertext);
	return new TextDecoder().decode(plainBuf);
}

// ---------------------------------------------------------------------------
// High-level helpers for the UI
// ---------------------------------------------------------------------------

/**
 * Encrypt a private-data JSON object for storage.
 *
 * Returns a hex string that can be passed to `update_my_private_data`.
 */
export async function encryptPrivateData(
	backend: any,
	data: Record<string, string>
): Promise<string> {
	const key = await deriveAesKey(backend);
	return aesGcmEncrypt(key, JSON.stringify(data));
}

/**
 * Decrypt a stored private-data hex blob back into a JSON object.
 *
 * Returns `null` if the data is empty or decryption fails (e.g. legacy
 * unencrypted data).
 */
export async function decryptPrivateData(
	backend: any,
	ciphertextHex: string
): Promise<Record<string, string> | null> {
	if (!ciphertextHex || ciphertextHex.length < 26) {
		// Too short to be iv+ciphertext; likely empty or legacy plaintext
		return null;
	}
	const key = await deriveAesKey(backend);
	try {
		const plaintext = await aesGcmDecrypt(key, ciphertextHex);
		return JSON.parse(plaintext);
	} catch {
		// Decryption or parsing failed — probably legacy unencrypted JSON
		return null;
	}
}
