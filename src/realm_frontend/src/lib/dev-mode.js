export const isDevelopmentMode = () => {
  return (
    process.env.NODE_ENV === 'development' ||
    process.env.VITE_DEV_DUMMY_MODE === 'true' ||
    window?.location?.hostname?.includes('localhost') ||
    window?.location?.hostname?.includes('127.0.0.1')
  );
};

export const isProductionMode = () => !isDevelopmentMode();

console.log(`Running in ${isDevelopmentMode() ? 'DEVELOPMENT' : 'PRODUCTION'} mode`);
