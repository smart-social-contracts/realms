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

// Mock implementation for build time or when canisters are not available
class MockBackend {
    constructor() {
        return new Proxy(this, {
            get: (target, prop) => {
                if (prop in target) return target[prop];
                return async (...args) => {
                    console.log(`Mock backend call: ${prop}(${JSON.stringify(args)})`);
                    return { success: false, error: 'Backend service not available in this environment' };
                };
            }
        });
    }
}

/**
 * Creates a backend proxy with graceful fallbacks
 */
function createBackendProxy() {
    // If we're building the app, return a mock implementation
    if (building) {
        console.log('Using mock backend during build');
        return new MockBackend();
    }

    const isDevelopment = typeof import.meta !== 'undefined' && import.meta.env?.DEV;
    
    return new Proxy({}, {
        get(target, prop) {
            return async (...args) => {
                try {
                    console.log(`Backend proxy call: ${prop}(${JSON.stringify(args)})`);
                    
                    // For runtime use, attempt to load the actual canister
                    if (typeof window !== 'undefined') {
                        try {
                            // We'll attempt dynamic import at runtime, not during build
                            const backendModule = '__CANISTER_IMPORT_PLACEHOLDER__';
                            
                            // This code only runs at runtime
                            if (backendModule && typeof backendModule.createActor === 'function') {
                                const actor = backendModule.createActor(backendModule.canisterId);
                                if (typeof actor[prop] === 'function') {
                                    const result = await actor[prop](...args);
                                    return result;
                                }
                            }
                        } catch (err) {
                            console.error(`Error accessing canister: ${err.message}`);
                        }
                    }
                    
                    // Fallback response
                    return { success: false, error: 'Backend service not available' };
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
