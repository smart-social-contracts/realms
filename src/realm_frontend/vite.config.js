import { fileURLToPath, URL } from 'url';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import environment from 'vite-plugin-environment';
import dotenv from 'dotenv';

dotenv.config({ path: '../../.env' });

export default defineConfig({
  build: {
    emptyOutDir: true,
    rollupOptions: {
      // Comment out external dependencies for development
      // external: [
      //   '@dfinity/agent',
      //   '@dfinity/principal',
      //   '@dfinity/auth-client',
      //   '@dfinity/identity',
      //   '@dfinity/candid'
      // ]
    },
    // Minimize build output
    minify: true,
    reportCompressedSize: false,
  },
  logLevel: 'error', // Only show errors
  optimizeDeps: {
    esbuildOptions: {
      define: {
        global: "globalThis",
      },
    },
    include: [
      '@dfinity/agent',
      '@dfinity/principal',
      '@dfinity/auth-client',
      '@dfinity/identity',
      '@dfinity/candid'
    ]
  },
  plugins: [
    sveltekit(),
    environment("all", { prefix: "CANISTER_" }),
    environment("all", { prefix: "DFX_" }),
  ],
  resolve: {
    alias: [
      {
        find: "declarations",
        replacement: fileURLToPath(
          new URL("../declarations", import.meta.url)
        ),
      },
      // // Add aliases for IC dependencies in development mode
      // ...(process.env.NODE_ENV === 'development' ? [
      //   { find: '@dfinity/candid', replacement: fileURLToPath(new URL('./src/lib/ic-stub.js', import.meta.url)) },
      //   { find: '@dfinity/agent', replacement: fileURLToPath(new URL('./src/lib/ic-stub.js', import.meta.url)) },
      //   { find: '@dfinity/identity', replacement: fileURLToPath(new URL('./src/lib/ic-stub.js', import.meta.url)) },
      // ] : []),
    ],
  },
  server: {
    fs: {
      allow: [
        'assets/images', // Add this directory
      ],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:4943',
        changeOrigin: true,
      },
    },
  },
});
