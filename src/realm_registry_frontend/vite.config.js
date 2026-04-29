import { fileURLToPath, URL } from 'url';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import environment from 'vite-plugin-environment';
import dotenv from 'dotenv';
import { execSync } from 'child_process';
import { readFileSync } from 'fs';

dotenv.config({ path: '../../.env' });

// Inject canister IDs from canister_ids.json for the active DFX_NETWORK so
// the frontend can resolve per-environment URLs without hardcoding.
function injectCanisterIds() {
  const network = process.env.DFX_NETWORK || 'staging';
  try {
    const ids = JSON.parse(readFileSync('../../canister_ids.json', 'utf-8'));
    for (const [canister, envs] of Object.entries(ids)) {
      const id = envs[network] || envs['ic'] || '';
      if (id) {
        const key = `CANISTER_ID_${canister.toUpperCase().replace(/-/g, '_')}`;
        process.env[key] = process.env[key] || id;
      }
    }
  } catch (e) {
    // canister_ids.json not present (e.g. CI without checkout), skip
  }
}
injectCanisterIds();

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
  },
  ssr: {
    noExternal: [
      'svelte-i18n',
      'intl-messageformat',
      '@formatjs/icu-messageformat-parser',
      '@formatjs/icu-skeleton-parser',
      '@formatjs/fast-memoize',
    ],
  },
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
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:4943",
        changeOrigin: true,
      },
    },
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
      { find: '@icp-sdk/core/agent', replacement: '@dfinity/agent' },
      { find: '@icp-sdk/core/principal', replacement: '@dfinity/principal' },
      { find: '@icp-sdk/core/candid', replacement: '@dfinity/candid' },
    ],
    dedupe: ['@dfinity/agent'],
  },
});
