import { building } from '$app/environment';

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

const buildingOrTesting = building || process.env.NODE_ENV === "test";

// Detect if we're running in local development
function isLocalDevelopment() {
    if (typeof window === 'undefined') return false;
    return (
        window.location.hostname.includes('localhost') ||
        window.location.hostname.includes('127.0.0.1')
    );
}

// Create backend actor with proper root key fetching for local development
async function createBackendActor() {
    if (buildingOrTesting) {
        return dummyActor();
    }

    // Dynamically import to avoid SSR issues
    const { createActor, canisterId } = await import('declarations/realm_registry_backend');
    const { HttpAgent } = await import('@dfinity/agent');

    // Create an agent
    const agent = new HttpAgent();

    // For local development, we need to fetch the root key
    if (isLocalDevelopment()) {
        console.log('🔑 Fetching root key for local development');
        try {
            await agent.fetchRootKey();
            console.log('✅ Root key fetched successfully');
        } catch (e) {
            console.warn('⚠️  Error fetching root key:', e);
            console.log('Continuing anyway as this might be expected in local dev');
        }
    }

    // Create actor with the agent
    return createActor(canisterId, { agent });
}

// Initialize backend with a promise
let backendPromise = createBackendActor();

// Export a proxy that waits for the backend to be ready
export const backend = new Proxy({}, {
    get: function (target, prop) {
        return async function (...args) {
            const actor = await backendPromise;
            return actor[prop](...args);
        };
    }
});
