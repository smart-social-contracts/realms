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

// Define mock implementations for API methods that may not be available yet
const mockImplementations = {
    // Extension API methods
    call_extension: async (extensionName, method, params = {}) => {
        console.log(`Mock call to extension ${extensionName}.${method} with params:`, params);
        return { success: false, error: `Extension ${extensionName} not found or method not implemented` };
    },
    
    // Generic list_extensions mock
    list_extensions: async () => ([])
};

/**
 * Helper function to call extension methods
 * @param {string} extensionName - Name of the extension
 * @param {string} method - Method name to call
 * @param {Object} params - Parameters to pass to the method
 * @returns {Promise<any>} Response data
 */
async function callExtension(actor, extensionName, method, params = {}) {
    try {
        const result = await actor.call_extension(extensionName, method, params);
        console.log(`Extension call ${extensionName}.${method} result:`, result);
        return result;
    } catch (error) {
        console.error(`Error calling extension ${extensionName}.${method}:`, error);
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
                    // Original implementation for non-extension methods
                    if (baseUrl) {
                        const endpoint = args.length > 0 
                            ? `${baseUrl}/${prop}/${args.join('/')}`
                            : `${baseUrl}/${prop}`;
                            
                        try {
                            return await makeRequest(endpoint);
                        } catch (err) {
                            console.warn(`API request to ${endpoint} failed, using mock implementation`);
                            if (mockImplementations[prop]) {
                                return mockImplementations[prop](...args);
                            }
                            return { success: false, error: `API endpoint ${prop} failed` };
                        }
                    }

                    // In production, try to use canister methods, but fall back to mocks
                    try {
                        const { createActor, canisterId } = await import('../../../declarations/realm_backend');
                        const actor = createActor(canisterId);
                        
                        if (typeof actor[prop] === 'function') {
                            return actor[prop](...args);
                        } else {
                            console.warn(`Method ${prop} not found in actor, using mock implementation`);
                        }
                    } catch (err) {
                        console.warn(`Error accessing canister method ${prop}:`, err);
                    }
                    
                    // Fall back to mock implementation if available
                    if (mockImplementations[prop]) {
                        return mockImplementations[prop](...args);
                    }
                    return { success: false, error: `Method ${prop} not available` };
                } catch (error) {
                    console.error(`Error in backendProxy for method ${prop}:`, error);
                    return { success: false, error: error.message };
                }
            };
        }
    });
}

/**
 * Creates a dummy actor for development without a backend
 * @returns {Object} Dummy actor with mock methods
 */
function dummyActor() {
    return {
        list_extensions: async () => ([]),
        ...mockImplementations
    };
}

// Export the backend instance
export const backend = createBackendProxy();
