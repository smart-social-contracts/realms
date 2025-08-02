import { building } from '$app/environment';
import { writable, get } from 'svelte/store';
import { authClient, initializeAuthClient } from '$lib/auth';
import { isDevelopmentMode } from './dev-mode.js';

let createActor, canisterId, HttpAgent;
let dummyBackend;
let importsInitialized = false;

async function initializeImports() {
	if (importsInitialized) return;

	if (isDevelopmentMode()) {
		console.log('🔧 DEV MODE: Loading dummy backend implementations');
		const declarationsModule = await import('./dummy-implementations/declarations-dummy.js');
		const dfinityModule = await import('./dummy-implementations/dfinity-dummy.js');
		const backendModule = await import('./dummy-implementations/backend-dummy.js');

		createActor = declarationsModule.createActor;
		canisterId = declarationsModule.canisterId;
		HttpAgent = dfinityModule.DummyHttpAgent;
		dummyBackend = backendModule.dummyBackend;
	} else {
		console.log('🏭 PROD MODE: Loading IC backend implementations');
		const declarationsModule = await import('declarations/realm_backend');
		const agentModule = await import('@dfinity/agent');

		createActor = declarationsModule.createActor;
		canisterId = declarationsModule.canisterId;
		HttpAgent = agentModule.HttpAgent;
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

// Initialize the backend store after imports are loaded
async function initializeBackendStore() {
	if (buildingOrTesting) return;

	await initializeImports();

	const actor = isDevelopmentMode() ? dummyBackend : createActor(canisterId);
	backendStore.set(actor);
}

// Initialize immediately if not building/testing
if (!buildingOrTesting) {
	initializeBackendStore();
}

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

		if (isDevelopmentMode()) {
			console.log('🔧 DEV MODE: Using dummy backend, skipping identity initialization');
			return dummyBackend;
		}

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
