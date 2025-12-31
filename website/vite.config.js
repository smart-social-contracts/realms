import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { execSync } from 'child_process'
import { readFileSync } from 'fs'

// Get build-time values for local development
function getBuildTimeValues() {
  let version = 'dev';
  let commitHash = 'local';
  const buildTime = new Date().toISOString().replace('T', ' ').substring(0, 19);
  
  try {
    version = readFileSync('../version.txt', 'utf-8').trim();
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
  plugins: [react()],
  define: {
    '__BUILD_VERSION__': JSON.stringify(buildValues.version),
    '__BUILD_COMMIT__': JSON.stringify(buildValues.commitHash),
    '__BUILD_TIME__': JSON.stringify(buildValues.buildTime),
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    host: true,
  },
})
