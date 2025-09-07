export const isDevelopmentMode = () => {
  return false; // Always use production mode - no dummy backend
};

export const isProductionMode = () => true;

console.log('Running in PRODUCTION mode - using real backend canister');
