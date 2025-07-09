import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export default defineConfig(({ mode }) => ({
  plugins: [svelte({ 
    hot: !process.env.VITEST, 
    compilerOptions: { 
      dev: true
    },
    onwarn: (warning, handler) => {
      if (process.env.VITEST) return;
      handler(warning);
    }
  })],
  resolve: {
    conditions: ['browser'],
    alias: {
      $lib: path.resolve('./src/lib'),
      $routes: path.resolve('./src/routes'),
      $assets: path.resolve('./src/assets'),
      $components: path.resolve('./src/components'),
      '$app/navigation': path.resolve('./src/test-mocks/app-navigation.js'),
      '$app/stores': path.resolve('./src/test-mocks/app-stores.js'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    includeSource: ['src/**/*.{js,ts,svelte}'],
    exclude: ['node_modules', '.svelte-kit', 'dist', 'tests/e2e'],
    coverage: {
      reporter: ['text', 'json', 'html'],
    },
    setupFiles: ['./src/test-setup.ts'],
  },
}));
