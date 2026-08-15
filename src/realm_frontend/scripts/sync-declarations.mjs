#!/usr/bin/env node
/**
 * Copy the repo's generated candid declarations into $lib so vite bundles them.
 *
 * publish_build.py and deploy_canisters.sh already do this before their own
 * vite build, so a plain `npm run build` used to bundle whatever stale copy was
 * committed under $lib -- producing an actor missing the backend's newer
 * methods, which only fails at runtime as "x is not a function".
 *
 * No-op when src/declarations is absent: deploy_canisters.sh deletes it after
 * copying so vite cannot resolve two competing copies.
 */
import { cpSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const source = resolve(here, '../../declarations');
const target = resolve(here, '../src/lib/declarations');

if (!existsSync(source)) {
	console.log('[sync-declarations] no src/declarations, skipping');
	process.exit(0);
}

mkdirSync(target, { recursive: true });

for (const entry of readdirSync(source, { withFileTypes: true })) {
	if (!entry.isDirectory()) continue;
	// index.js carries canister IDs injected by the deploy scripts; only the
	// candid interface itself is safe to overwrite.
	for (const file of readdirSync(join(source, entry.name))) {
		if (!file.includes('.did')) continue;
		mkdirSync(join(target, entry.name), { recursive: true });
		cpSync(join(source, entry.name, file), join(target, entry.name, file));
	}
}

console.log(`[sync-declarations] synced candid from ${source}`);
