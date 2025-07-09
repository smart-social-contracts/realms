import { building } from '$app/environment';
import { HttpAgent } from '@dfinity/agent';
import { writable, get } from 'svelte/store';

const isDevDummyMode = import.meta.env.VITE_DEV_DUMMY_MODE === 'true' || 
                      import.meta.env.DEV_DUMMY_MODE === 'true' ||
                      (typeof window !== 'undefined' && window.location.search.includes('dummy=true'));


export const canisterId = isDevDummyMode ? 'dummy-canister-id' : 'rdmx6-jaaaa-aaaah-qcaiq-cai';  

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

const buildingOrTesting = building || process.env.NODE_ENV === "test";

// Detect if we're running in local development
// Use a more reliable method than process.env which might not work in browser
const isLocalDevelopment = typeof window !== 'undefined' && 
                          (window.location.hostname.includes('localhost') || 
                           window.location.hostname.includes('127.0.0.1'));

console.log('Running in local development mode:', isLocalDevelopment);

// Create dev dummy actor with comprehensive mock responses
function createDevDummyActor() {
    const mockExtensionResponses = {
        vault_manager: {
            get_balance: {
                success: true,
                response: JSON.stringify({
                    success: true,
                    data: {
                        Balance: {
                            amount: 150000000,
                            principal_id: "rdmx6-jaaaa-aaaah-qcaiq-cai"
                        }
                    }
                })
            },
            get_status: {
                success: true,
                response: JSON.stringify({
                    success: true,
                    data: {
                        Stats: {
                            app_data: {
                                sync_tx_id: 500000000,
                                admin_principal: "rdmx6-jaaaa-aaaah-qcaiq-cai",
                                sync_status: "Active"
                            },
                            balances: [
                                { principal_id: "rdmx6-jaaaa-aaaah-qcaiq-cai", amount: 150000000 },
                                { principal_id: "rrkah-fqaaa-aaaah-qcaiq-cai", amount: 75000000 }
                            ]
                        }
                    }
                })
            },
            get_transactions: {
                success: true,
                response: JSON.stringify({
                    success: true,
                    data: {
                        Transactions: [
                            {
                                id: "1",
                                amount: "50000000",
                                timestamp: "1704067200000000000"
                            },
                            {
                                id: "2", 
                                amount: "-25000000",
                                timestamp: "1704153600000000000"
                            }
                        ]
                    }
                })
            }
        },
        llm_chat: {
            get_realm_data: {
                success: true,
                response: JSON.stringify({
                    success: true,
                    data: {
                        realm_name: "Dev Dummy Realm",
                        population: 1250,
                        governance_type: "Democratic",
                        treasury_balance: 150000000
                    }
                })
            }
        }
    };

    return {
        extension_sync_call: async (extension_name, method_name, args) => {
            console.log(`[DEV DUMMY] extension_sync_call: ${extension_name}.${method_name}`, args);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const extensionMocks = mockExtensionResponses[extension_name];
            if (extensionMocks && extensionMocks[method_name]) {
                return extensionMocks[method_name];
            }
            
            return {
                success: true,
                response: JSON.stringify({
                    success: true,
                    data: { message: `Mock response for ${extension_name}.${method_name}` }
                })
            };
        },

        extension_async_call: async (extension_name, method_name, args) => {
            console.log(`[DEV DUMMY] extension_async_call: ${extension_name}.${method_name}`, args);
            await new Promise(resolve => setTimeout(resolve, 200));
            
            const extensionMocks = mockExtensionResponses[extension_name];
            if (extensionMocks && extensionMocks[method_name]) {
                return extensionMocks[method_name];
            }
            
            return {
                success: true,
                response: JSON.stringify({
                    success: true,
                    data: { message: `Mock async response for ${extension_name}.${method_name}` }
                })
            };
        },

        get_my_user_status: async () => {
            console.log('[DEV DUMMY] get_my_user_status called');
            await new Promise(resolve => setTimeout(resolve, 100));
            return {
                success: true,
                data: {
                    user_id: "dev-user-123",
                    username: "DevUser",
                    roles: ["member", "developer"],
                    joined_date: "2024-01-01",
                    profile_complete: true
                }
            };
        },

        greet: async (name) => {
            console.log('[DEV DUMMY] greet called with:', name);
            await new Promise(resolve => setTimeout(resolve, 50));
            return `Hello, ${name}! Welcome to Dev Dummy Mode.`;
        },

        get_universe: async () => {
            console.log('[DEV DUMMY] get_universe called');
            await new Promise(resolve => setTimeout(resolve, 100));
            return {
                success: true,
                data: {
                    realm_name: "Dev Dummy Realm",
                    version: "1.0.0-dev",
                    total_users: 1250,
                    active_extensions: ["vault_manager", "llm_chat", "test_bench"]
                }
            };
        },

        get_snapshots: async () => {
            console.log('[DEV DUMMY] get_snapshots called');
            await new Promise(resolve => setTimeout(resolve, 100));
            return {
                success: true,
                data: {
                    snapshots: [
                        { id: "snap-1", timestamp: Date.now() - 3600000, size: "2.5MB" },
                        { id: "snap-2", timestamp: Date.now() - 7200000, size: "2.3MB" }
                    ]
                }
            };
        },

        status: async () => {
            console.log('[DEV DUMMY] status called');
            await new Promise(resolve => setTimeout(resolve, 50));
            return {
                success: true,
                data: {
                    status: "healthy",
                    uptime: "24h 15m",
                    version: "1.0.0-dev",
                    mode: "development"
                }
            };
        },

        join_realm: async (selectedProfile) => {
            console.log('[DEV DUMMY] join_realm called with profile:', selectedProfile);
            await new Promise(resolve => setTimeout(resolve, 500));
            return {
                success: true,
                data: {
                    user_id: "dev-user-123",
                    profile: selectedProfile,
                    joined_date: new Date().toISOString(),
                    realm_name: "Dev Dummy Realm",
                    message: `Successfully joined as ${selectedProfile}`
                }
            };
        }
    };
}

// Create a writable store for the backend actor
function initializeBackendActor() {
    if (buildingOrTesting) {
        return dummyActor();
    }
    
    if (isDevDummyMode) {
        console.log('Using dev dummy mode - all backend calls will be mocked');
        return createDevDummyActor();
    }
    
    console.log('Normal mode - backend will be initialized when needed');
    return createDevDummyActor(); // Temporary fallback until real backend is loaded
}

export const backendStore = writable(initializeBackendActor());

// Create a proxy that always uses the latest actor from the store
export const backend = new Proxy({}, {
    get: function(target, prop) {
        // Get the latest actor from the store
        const actor = get(backendStore);
        // Forward the property access to the actor
        return actor[prop];
    }
});

// Initialize backend with authenticated identity
export async function initBackendWithIdentity() {
    try {
        console.log('Initializing backend with authenticated identity...');
        
        // Make sure we're using the shared auth client
        const client = authClient || await initializeAuthClient();
        
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
            if (isLocalDevelopment) {
                console.log('Fetching root key for local development');
                await agent.fetchRootKey().catch(e => {
                    console.warn('Error fetching root key:', e);
                    console.log('Continuing anyway as this might be expected in local dev');
                });
            }
            
            // Create a new actor with the authenticated identity
            let authenticatedActor;
            if (isDevDummyMode) {
                authenticatedActor = createDevDummyActor();
            } else {
                // Only reference createActor when not in dev dummy mode
                try {
                    const backendPath = 'declarations/realm_backend';
                    const { createActor: realCreateActor, canisterId: realCanisterId } = await import(/* @vite-ignore */ backendPath);
                    authenticatedActor = realCreateActor(realCanisterId, { agent });
                } catch (error) {
                    console.log('Backend declarations not available, falling back to dummy mode');
                    authenticatedActor = createDevDummyActor();
                }
            }
            
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
