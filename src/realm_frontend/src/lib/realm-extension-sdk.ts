/**
 * RealmExtensionContext — the shared SDK surface exposed by the host app
 * to every runtime-loaded extension bundle.
 *
 * Extension bundles receive this as the second argument to their mount()
 * function and use it instead of reaching into host internals ($lib/*, $app/*).
 *
 * The stores follow the Svelte store contract: { subscribe(cb): unsubscribe }.
 * Plain-JS bundles can call ctx.principal.subscribe(v => …) directly.
 */

// ── Re-exported helper types ───────────────────────────────────────────

export interface Readable<T> {
	subscribe(run: (value: T) => void): () => void;
}

export interface NotificationItem {
	id: string;
	title: string;
	message: string;
	timestamp_ms: number;
	read: boolean;
	icon?: string;
	href?: string;
	color?: string;
}

export interface RealmInfo {
	name: string;
	welcomeMessage: string;
	manifesto: string;
	registries: { canister_id: string; canister_type: string }[];
	quarters: { name: string; canister_id: string; population: number; status: string }[];
	isQuarter: boolean;
	parentRealmCanisterId: string;
	loading: boolean;
	error: string | null;
}

// ── Main context interface ─────────────────────────────────────────────

export interface RealmExtensionContext {
	/** The extension's ID as registered in the realm backend. */
	extensionId: string;
	/** The installed version string. */
	version: string;

	/**
	 * The realm backend canister actor (proxy).
	 * Supports extension_sync_call, extension_async_call, get_objects_paginated,
	 * status, and all other Candid methods exposed by the realm_backend.
	 */
	backend: any;

	/**
	 * Call a sync extension function on the backend.
	 * Automatically handles positional Candid args and JSON serialization.
	 *
	 * @param fn    The function name exposed by the backend extension.
	 * @param args  A plain JS object that will be JSON-stringified as the `args` parameter.
	 * @returns     The parsed JSON response, or throws on failure.
	 */
	callSync: (fn: string, args?: Record<string, unknown>) => Promise<unknown>;

	/**
	 * Call an async (inter-canister) extension function on the backend.
	 * Same ergonomics as callSync.
	 */
	callAsync: (fn: string, args?: Record<string, unknown>) => Promise<unknown>;

	/** The logged-in user's principal as a reactive store. Empty string when anonymous. */
	principal: Readable<string>;
	/** Whether the user has authenticated via Internet Identity. */
	isAuthenticated: Readable<boolean>;
	/** The user's profile tags (e.g. ["member", "admin"]). Empty while loading or anonymous. */
	userProfiles: Readable<string[]>;

	/** Realm metadata (name, logo, manifesto, quarters, etc.). */
	realmInfo: Readable<RealmInfo>;
	/** Static config values (canister IDs for ckBTC, token backend, etc.). */
	config: {
		ckbtc_ledger_canister_id: string;
		ckbtc_indexer_canister_id: string;
		token_backend_canister_id: string;
		/** The realm_backend canister ID itself. */
		canisterId: string;
		/** File registry canister ID (shared infra, set via set_canister_config). */
		fileRegistryCanisterId?: string;
		/** Marketplace canister ID (shared infra, set via set_canister_config). */
		marketplaceCanisterId?: string;
	};

	/** Navigate to a path within the realm SPA (wraps SvelteKit's goto). */
	navigate: (path: string) => Promise<void>;

	/** The i18n translate function as a reactive store. Usage: $t('key', { values }). */
	t: Readable<(key: string, vars?: Record<string, unknown>) => string>;
	/** The current locale code (e.g. "en", "de"). */
	locale: Readable<string>;

	/** Notification subsystem. */
	notifications: {
		items: Readable<NotificationItem[]>;
		unreadCount: Readable<number>;
		load: () => Promise<void>;
		markAsRead: (id: string, read?: boolean) => Promise<void>;
	};

	/** Theme utility for combining Tailwind class strings. */
	theme: {
		cn: (...classes: (string | undefined | null | false)[]) => string;
	};

	/**
	 * Crypto helpers backed by the host's bundled `@dfinity/vetkeys`, so
	 * extensions can decrypt consent-shared member data without bundling the
	 * (large) vetKeys library themselves.
	 */
	crypto: {
		/**
		 * Decrypt a member's private data the caller has been granted access to.
		 *
		 * @param wrappedDekHex  The caller's IBE-wrapped DEK (from a KeyEnvelope).
		 * @param ciphertext     The member's `enc:v=2:...` private-data ciphertext.
		 * @returns The decrypted key/value object, or null if decryption fails.
		 */
		decryptWithEnvelope: (
			wrappedDekHex: string,
			ciphertext: string,
		) => Promise<Record<string, string> | null>;
	};

	/** Shared UI helpers provided by the host app. */
	ui: {
		AccessDenied: import('svelte').Component<{ operation?: string }>;
		/** Returns the denied operation name, or null if the error is not access-denied. */
		accessDeniedOperation: (error: unknown) => string | null;
	};
}

// ── Mount function signature ───────────────────────────────────────────

export interface MountResult {
	unmount?: () => void;
}

export type ExtensionMountFn = (
	target: HTMLElement,
	ctx: RealmExtensionContext,
) => MountResult | void | Promise<MountResult | void>;
