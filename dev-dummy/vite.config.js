import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 3001,
    open: true,
    fs: {
      allow: ['..']
    }
  },
  resolve: {
    alias: {
      '$lib/shared': path.resolve('../src/realm_frontend/src/lib/shared'),
      '$lib': path.resolve('./src/lib')
    }
  }
});
