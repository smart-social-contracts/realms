import { building } from '$app/environment';
import { writable, get } from 'svelte/store';
import { authClient, initializeAuthClient, login } from '$lib/auth';
import { TEST_MODE_II_BYPASS } from '$lib/config.js';

let createActor, canisterId, HttpAgent;
let importsInitialized = false;

async function initializeImports() {
	if (importsInitialized) return;

	console.log('🏭 Loading IC backend implementations');
	
	// Import realm_backend declarations directly
	// This will be bundled by Vite at build time
	let declarationsModule = null;
	try {
		// Use static import path that Vite can analyze at build time
		const { createActor: ca, canisterId: cid } = await import('$lib/declarations/realm_backend');
		declarationsModule = { createActor: ca, canisterId: cid };
		console.log(`✅ Loaded declarations for realm_backend`);
	} catch (e) {
		console.error('Failed to load backend declarations:', e);
		throw new Error('Could not load backend declarations. Please run: dfx generate');
	}
	
	if (declarationsModule) {
		createActor = declarationsModule.createActor;
		canisterId = declarationsModule.canisterId;
	} else {
		throw new Error('Could not load backend declarations. Please run: dfx generate');
	}
	
	const agentModule = await import('@dfinity/agent');
	HttpAgent = agentModule.HttpAgent;

	if (!canisterId) {
		throw new Error('Canister ID not found in declarations');
	}

	importsInitialized = true;
}

function dummyActor() {
	return new Proxy(
		{},
		{
			get() {
				throw new Error('Canister invoked while building');
			}
		}
	);
}

const buildingOrTesting = building || process.env.NODE_ENV === 'test';

// Detect if we're running in local development
// Use a more reliable method than process.env which might not work in browser
function isLocalDevelopment() {
	if (typeof window === 'undefined') return false;
	return (
		window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1')
	);
}

// Create a writable store for the backend actor
export const backendStore = writable(buildingOrTesting ? dummyActor() : null);

// Singleton promise so concurrent callers all wait for the same init.
let _initBackendPromise = null;

// Initialize the backend store after imports are loaded
function initializeBackendStore() {
	if (buildingOrTesting) return Promise.resolve();
	if (_initBackendPromise) return _initBackendPromise;

	_initBackendPromise = (async () => {
		await initializeImports();

		// Try to use an existing authenticated session so the initial actor
		// is not anonymous on page refresh (avoids race with initBackendWithIdentity).
		try {
			const client = authClient || (await initializeAuthClient());

			// In test mode, auto-login before checking auth to avoid race condition
			// where components mount and make calls before AuthButton triggers login
			if (TEST_MODE_II_BYPASS && !(await client.isAuthenticated())) {
				await login();
			}

			if (await client.isAuthenticated()) {
				const identity = client.getIdentity();
				const agent = new HttpAgent({ identity });
				if (isLocalDevelopment()) {
					await agent.fetchRootKey().catch(() => {});
				}
				const actor = createActor(canisterId, { agent });
				backendStore.set(actor);
				console.log('Backend store initialized with authenticated identity');
				return;
			}
		} catch (e) {
			console.warn('Could not check auth during init, falling back to anonymous:', e);
		}

		const actor = createActor(canisterId);
		backendStore.set(actor);
	})();

	return _initBackendPromise;
}

// Initialize immediately if not building/testing.
// Export the promise so components can await full init (including auth).
export const backendReady = buildingOrTesting ? Promise.resolve() : initializeBackendStore();

// Create a proxy that always uses the latest actor from the store
export const backend = new Proxy(
	{},
	{
		get: function (target, prop) {
			const currentBackend = get(backendStore);
			if (!currentBackend) {
				return async (...args) => {
					await initializeBackendStore();
					const backend = get(backendStore);
					return backend[prop](...args);
				};
			}
			return currentBackend[prop];
		}
	}
);

// Initialize backend with authenticated identity
export async function initBackendWithIdentity() {
	try {
		console.log('Initializing backend with authenticated identity...');

		await initializeImports();

		// Make sure we're using the shared auth client
		const client = authClient || (await initializeAuthClient());

		if (await client.isAuthenticated()) {
			// Get the authenticated identity from the shared client
			const identity = client.getIdentity();
			console.log('Using authenticated identity:', identity.getPrincipal().toText());

			const currentActor = get(backendStore);
			if (currentActor && currentActor._agent && currentActor._agent._identity === identity) {
				console.log('Backend already initialized with current identity');
				return currentActor;
			}

			// Create an agent with the identity
			const agent = new HttpAgent({ identity });

			// For local development, we need to fetch the root key
			if (isLocalDevelopment()) {
				console.log('Fetching root key for local development');
				await agent.fetchRootKey().catch((e) => {
					console.warn('Error fetching root key:', e);
					console.log('Continuing anyway as this might be expected in local dev');
				});
			}

			// Create a new actor with the authenticated identity
			const authenticatedActor = createActor(canisterId, {
				agent
			});

			// Update the store with the authenticated actor
			backendStore.set(authenticatedActor);

			console.log('Backend initialized with authenticated identity');
			return authenticatedActor;
		} else {
			console.log('User not authenticated, using anonymous identity');
			return backend;
		}
	} catch (error) {
		console.error('Error initializing backend with identity:', error);
		return backend;
	}
}

// Quarter-aware actor: creates an actor for a specific canister ID
export async function createQuarterActor(quarterCanisterId) {
	if (buildingOrTesting) return dummyActor();

	await initializeImports();

	const client = authClient || (await initializeAuthClient());
	let agent;

	if (await client.isAuthenticated()) {
		const identity = client.getIdentity();
		agent = new HttpAgent({ identity });
	} else {
		agent = new HttpAgent();
	}

	if (isLocalDevelopment()) {
		await agent.fetchRootKey().catch(() => {});
	}

	return createActor(quarterCanisterId, { agent });
}

// --- Quarter-aware backend store ---
// Holds the currently-active actor: main realm backend OR a quarter actor.
// Import activeQuarterId from quarters store and subscribe to swap actors.
export const quarterBackendStore = writable(buildingOrTesting ? dummyActor() : null);

let _currentQuarterId = null;

/**
 * Switch the quarterBackend to a specific quarter canister, or back to the
 * main realm backend when quarterId is null.
 */
export async function setActiveQuarter(quarterId) {
	if (quarterId === _currentQuarterId) return;
	_currentQuarterId = quarterId;

	if (!quarterId) {
		// Revert to main realm backend
		const main = get(backendStore);
		quarterBackendStore.set(main || backend);
		console.log('🏛️ quarterBackend → main realm');
		return;
	}

	try {
		const actor = await createQuarterActor(quarterId);
		quarterBackendStore.set(actor);
		console.log(`🏘️ quarterBackend → quarter ${quarterId}`);
	} catch (e) {
		console.error('Failed to create quarter actor, falling back to main:', e);
		quarterBackendStore.set(get(backendStore) || backend);
	}
}

// Proxy that always resolves to the current quarter (or main) backend
export const quarterBackend = new Proxy(
	{},
	{
		get: function (target, prop) {
			const current = get(quarterBackendStore);
			if (!current) {
				// Not initialised yet — delegate to main backend
				return (...args) => backend[prop](...args);
			}
			return current[prop];
		}
	}
);

// Initialise quarterBackendStore to the main backend once it is ready
backendStore.subscribe((actor) => {
	if (actor && !_currentQuarterId) {
		quarterBackendStore.set(actor);
	}
});

// Debug helper: expose backend globally in browser console
if (typeof window !== 'undefined') {
	window.__debug_backend = backend;
	window.__debug_quarterBackend = quarterBackend;
	console.log('🔍 Debug: backend available as window.__debug_backend');
}
