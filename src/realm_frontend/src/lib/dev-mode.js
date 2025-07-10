export const isDevelopmentMode = () => {
  return (
    import.meta.env.VITE_DEV_DUMMY_MODE === 'true'
  );
};

export const isProductionMode = () => !isDevelopmentMode();

console.log(`Running in ${isDevelopmentMode() ? 'DEVELOPMENT' : 'PRODUCTION'} mode`);
