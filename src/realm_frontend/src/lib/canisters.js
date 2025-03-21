import { createActor, canisterId } from 'declarations/realm_backend';
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
    const [controller, timeoutPromise] = createTimeoutController(DEFAULT_TIMEOUT);
    
    try {
        const response = await Promise.race([
            fetch(endpoint, {
                ...options,
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            }),
            timeoutPromise
        ]);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
        }

        // const contentType = response.headers.get('content-type');
        // if (!contentType || !contentType.includes('application/json')) {
        //     throw new TypeError('Response was not JSON');
        // }

        const ret = await response.json()
        console.log('response.json()',ret);

        return ret;
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Request was aborted');
        }
        throw error;
    }
}

/**
 * Creates a proxy to handle backend server requests
 * @returns {Proxy} Proxy object handling backend requests
 */
function backendServer() {
    const isDevelopment = import.meta.env.DEV;
    const baseUrl = isDevelopment ? 'http://localhost:8000' : undefined;

    return new Proxy({}, {
        get(target, prop) {
            return async (...args) => {
                if (!baseUrl) {
                    // In production, use the ICP canister
                    const actor = createActor(canisterId);
                    return actor[prop](...args);
                }

                // In development, use the method name as the REST endpoint
                const endpoint = args.length > 0 
                    ? `${baseUrl}/${prop}/${args.join('/')}`
                    : `${baseUrl}/${prop}`;
                    
                return makeRequest(endpoint);
            };
        }
    });
}

function dummyActor() {
    return new Proxy({}, {
        get(target, prop) {
            if (prop === "get_universe") {
                console.log("dummyActor.get_universe");
                return () => {
                    return new Promise((resolve) => {
                        setTimeout(() => {
                            resolve({

                            });
                        }, 1000);
                    });
                };
            } else if (prop === "get_stats") {
                console.log("dummyActor.get_stats");
                return () => {
                    return new Promise((resolve) => {
                        setTimeout(() => {
                            resolve({

                            });
                        }, 1000);
                    });
                };
            }

            throw new Error(`Property "${prop}" is not available on dummyActor`);
        }
    });
}

// export const backend = dummyActor();
export const backend = backendServer();
// export const backend = createActor(canisterId);

// console.log(`process.env.NODE_ENV: ${process.env.NODE_ENV}`);
// const buildingOrTesting = building || process.env.NODE_ENV === "test";
// console.log(`buildingOrTesting: ${buildingOrTesting}`);

// export const backend = buildingOrTesting
//     ? dummyActor()
//     : createActor(canisterId);
