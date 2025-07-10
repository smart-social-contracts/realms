export const canisterId = 'dummy-canister-id-123456789';

export function createActor(canisterId, options = {}) {
  console.log('🔧 DEV MODE: createActor called with dummy implementation');
  
  return new Proxy({}, {
    get: function(target, prop) {
      return function(...args) {
        console.log(`🔧 DEV MODE: Actor method ${prop} called with:`, args);
        return Promise.resolve({ success: true, data: `Dummy response for ${prop}` });
      };
    }
  });
}
