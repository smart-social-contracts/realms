import { fileURLToPath, URL } from 'url';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import environment from 'vite-plugin-environment';
import dotenv from 'dotenv';
import { execSync } from 'child_process';
import { readFileSync } from 'fs';

dotenv.config({ path: '../../.env' });

// Get build-time values for local development
function getBuildTimeValues() {
  let version = 'dev';
  let commitHash = 'local';
  const buildTime = new Date().toISOString().replace('T', ' ').substring(0, 19);
  
  try {
    version = readFileSync('../../version.txt', 'utf-8').trim();
  } catch (e) {
    // version.txt not found, use default
  }
  
  try {
    commitHash = execSync('git rev-parse --short HEAD', { encoding: 'utf-8' }).trim();
  } catch (e) {
    // git not available, use default
  }
  
  return { version, commitHash, buildTime };
}

const buildValues = getBuildTimeValues();

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
  define: {
    '__BUILD_VERSION__': JSON.stringify(buildValues.version),
    '__BUILD_COMMIT__': JSON.stringify(buildValues.commitHash),
    '__BUILD_TIME__': JSON.stringify(buildValues.buildTime),
  },
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
