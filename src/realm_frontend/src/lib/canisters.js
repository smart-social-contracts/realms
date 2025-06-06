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
 * Creates a backend proxy with graceful fallbacks
 * This version doesn't use dynamic imports at the top level to avoid build errors
 */
function createBackendProxy() {
    const isDevelopment = import.meta.env.DEV;
    const baseUrl = isDevelopment ? 'http://localhost:8000' : undefined;

    return new Proxy({}, {
        get(target, prop) {
            return async (...args) => {
                try {
                    console.log(`Backend proxy call: ${prop}(${JSON.stringify(args)})`);
                    
                    // In production and development, try to use canister methods
                    try {
                        console.log(`Trying to import canister declarations for ${prop}`);
                        const { createActor, canisterId } = await import('declarations/realm_backend');
                        
                        // Create proper agent options with fetchRootKey for local development
                        const options = {
                            agentOptions: {
                                host: isDevelopment ? "http://localhost:8000" : "https://ic0.app",
                                // This is the critical fix: In development, we need to fetch the root key
                                // In production, this should be false as the root key is hardcoded
                                fetchRootKey: isDevelopment
                            }
                        };
                        
                        console.log(`Creating actor with canister ID: ${canisterId} for method ${prop}`);
                        const actor = createActor(canisterId, options);
                        
                        if (typeof actor[prop] === 'function') {
                            console.log(`Calling canister method ${prop} with args:`, args);
                            const result = await actor[prop](...args);
                            console.log(`Canister method ${prop} result:`, result);
                            return result;
                        } else {
                            console.warn(`Method ${prop} not found in actor, available methods:`, Object.keys(actor));
                            return { success: false, error: `Method ${prop} not found in actor` };
                        }
                    } catch (err) {
                        console.error(`Error accessing canister method ${prop}:`, err);
                        
                        // Provide more specific error messages for certificate issues
                        if (err.message && err.message.includes('certificate')) {
                            console.error('Certificate validation error - This could be due to clock skew or network issues');
                            return { 
                                success: false, 
                                error: `Certificate validation error: ${err.message}. Try refreshing the page or check your system clock` 
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
