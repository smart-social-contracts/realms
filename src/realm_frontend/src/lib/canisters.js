import { building } from '$app/environment';

/**
 * Default timeout for API requests in milliseconds
 * @type {number}
 */
const DEFAULT_TIMEOUT = 10000;

/**
 * Creates an AbortController with timeout
 * @param {number} timeout - Timeout in milliseconds
 * @returns {[AbortController, Promise<never>]} Tuple of controller and timeout promise
 */
function createTimeoutController(timeout) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    return [
        controller,
        new Promise((_, reject) => {
            setTimeout(() => {
                reject(new Error(`Request timed out after ${timeout}ms`));
            }, timeout);
        }).finally(() => clearTimeout(timeoutId))
    ];
}

/**
 * Generic API request handler with timeout and error handling
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise<any>} Response data
 */
async function makeRequest(endpoint, options = {}) {
    const [controller, timeoutPromise] = createTimeoutController(
        options.timeout || DEFAULT_TIMEOUT
    );

    options = {
        ...options,
        signal: controller.signal,
        headers: {
            ...(options.headers || {}),
            'Content-Type': 'application/json'
        }
    };

    try {
        const fetchPromise = fetch(endpoint, options);
        const response = await Promise.race([fetchPromise, timeoutPromise]);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status} ${response.statusText}`);
        }

        const contentType = response.headers.get('Content-Type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            return response.text();
        }
    } catch (error) {
        console.error(`API request to ${endpoint} failed:`, error);
        throw error;
    }
}

/**
 * Creates a backend proxy with improved error handling for local development
 */
export function createBackendProxy() {
    const isDevelopment = import.meta.env.DEV;
    const baseUrl = isDevelopment ? 'http://localhost:8000' : undefined;
    
    // Track failed methods to avoid spamming logs
    const failedMethods = new Set();

    return new Proxy({}, {
        get(target, prop) {
            return async (...args) => {
                try {
                    console.log(`Backend proxy call: ${prop}(${JSON.stringify(args)})`);
                    
                    // In production and development, try to use canister methods
                    try {
                        // This dynamic import pattern worked in the original code
                        const { Actor, HttpAgent } = await import('@dfinity/agent');
                        
                        // Import from dfx-generated directory - the path will be resolved by Vite
                        // We avoid using relative paths like "../../declarations" which might be fragile
                        const declarations = await import('declarations/realm_backend');
                        
                        // Log the available exports to help with debugging
                        console.log('Available from declarations:', Object.keys(declarations));
                        
                        // Enhanced agent options for local development
                        const options = {
                            agentOptions: {
                                host: isDevelopment ? baseUrl : "https://ic0.app",
                                // Fetch root key is critical for local development
                                fetchRootKey: isDevelopment,
                                // Add proper verification for local development
                                verifyQuerySignatures: !isDevelopment,
                                // Increase timeouts for local development
                                callTimeout: isDevelopment ? 60000 : 30000,
                                // Disable subnet lookup for local development which often fails
                                disableRootSubnetCheck: isDevelopment
                            }
                        };
                        
                        // Get canister ID from declarations
                        const canisterId = declarations.canisterId;
                        console.log(`Creating actor with canister ID: ${canisterId} for method ${prop}`);
                        console.log(`Using host: ${options.agentOptions.host}`);
                        
                        // Create the agent first
                        const agent = new HttpAgent(options.agentOptions);
                        
                        // Fetch root key once in development
                        if (isDevelopment) {
                            try {
                                await agent.fetchRootKey();
                                console.log("Successfully fetched root key for local development");
                            } catch (rootKeyErr) {
                                console.error("Failed to fetch root key:", rootKeyErr.message);
                            }
                        }
                        
                        // Use the createActor function from declarations if available, otherwise fall back to Actor.createActor
                        let actor;
                        if (typeof declarations.createActor === 'function') {
                            actor = declarations.createActor(canisterId, { agent });
                        } else if (declarations.idlFactory) {
                            actor = Actor.createActor(declarations.idlFactory, { agent, canisterId });
                        } else {
                            throw new Error('Could not find createActor function or idlFactory in declarations');
                        }
                        
                        if (typeof actor[prop] === 'function') {
                            console.log(`Calling canister method ${prop} with args:`, args);
                            
                            try {
                                const result = await actor[prop](...args);
                                console.log(`Canister method ${prop} result:`, result);
                                
                                // Clear from failed methods if it succeeded this time
                                if (failedMethods.has(prop)) {
                                    failedMethods.delete(prop);
                                }
                                
                                return { success: true, data: result };
                            } catch (callError) {
                                console.error(`Error calling canister method ${prop}:`, callError);
                                
                                // Record the failed method
                                failedMethods.add(prop);
                                return { success: false, error: callError.message };
                            }
                        } else {
                            console.warn(`Method ${prop} not found in actor, available methods:`, Object.keys(actor));
                            return { success: false, error: `Method ${prop} not found in actor` };
                        }
                    } catch (err) {
                        console.error(`Error accessing canister method ${prop}:`, err);
                        
                        // Provide more specific error messages for certificate and subnet issues
                        if (err.message && err.message.includes('certificate')) {
                            console.error('Certificate validation error - This could be due to clock skew or network issues');
                            return { 
                                success: false, 
                                error: `Certificate validation error: ${err.message}. Try refreshing the page or check your system clock` 
                            };
                        } else if (err.message && (err.message.includes('subnet') || err.message.includes('canister_not_found'))) {
                            console.error('Subnet or canister discovery error - This is common in local development');
                            return {
                                success: false,
                                error: `IC network error: ${err.message}. This may be due to local development environment issues.`
                            };
                        } else if (err.message && err.message.includes('HTTP error: 400')) {
                            return { 
                                success: false, 
                                error: `HTTP 400 error: Backend canister not responding correctly. Verify that you're running a local replica with 'dfx start' and the canister is deployed with 'dfx deploy'.` 
                            };
                        }
                        
                        return { success: false, error: `Error accessing canister method: ${err.message}` };
                    }
                } catch (error) {
                    console.error(`Error in backendProxy for method ${prop}:`, error);
                    return { success: false, error: error.message };
                }
            };
        }
    });
}

// Export the backend instance
export const backend = createBackendProxy();
