#!/usr/bin/env node
/**
 * postbuild: write dist/version — the GET /version asset (gos-as-a-service#39).
 *
 * Runs after `vite build` (dist/ is emptied at build start, so this must run
 * after). The file has no extension on purpose: the asset canister serves it
 * at exactly /version, and static/.ic-assets.json5 sets its content type to
 * application/json. An exact asset match wins over the SPA index.html fallback.
 */
import { existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { writeVersionFile } from '../../../scripts/build-info.js';

const frontendDir = join(dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = join(frontendDir, '..', '..');
const distDir = join(frontendDir, 'dist');

if (!existsSync(distDir)) {
  console.error('write-version-file: dist/ not found — run vite build first');
  process.exit(1);
}

const payload = writeVersionFile(distDir, 'realm_frontend', repoRoot);
console.log(`dist/version: ${JSON.stringify(payload)}`);
