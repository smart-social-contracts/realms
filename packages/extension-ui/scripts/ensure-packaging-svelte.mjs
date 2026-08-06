/**
 * svelte-package uses svelte2tsx, which resolves `svelte` from its own
 * node_modules. In this monorepo, npm hoists Svelte 4 for the main app, so
 * svelte2tsx ends up on the Svelte 4 compiler and chokes on {@render}.
 * Nest Svelte 5 under svelte2tsx before packaging when needed.
 */
import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const pkgRoot = join(dirname(fileURLToPath(import.meta.url)), '..');

const resolvePaths = [
	join(pkgRoot, 'node_modules'),
	join(pkgRoot, '../../node_modules')
];

let svelte2tsxDir;
try {
	svelte2tsxDir = dirname(
		require.resolve('svelte2tsx/package.json', { paths: resolvePaths })
	);
} catch {
	console.error('ensure-packaging-svelte: could not resolve svelte2tsx');
	process.exit(1);
}

const targetVersion = require(join(pkgRoot, 'node_modules/svelte/package.json')).version;

let nestedVersion;
try {
	nestedVersion = require(join(svelte2tsxDir, 'node_modules/svelte/package.json')).version;
} catch {
	nestedVersion = null;
}

if (!nestedVersion?.startsWith('5.')) {
	console.log(
		`ensure-packaging-svelte: nesting svelte@${targetVersion} under svelte2tsx (was ${nestedVersion ?? 'missing'})`
	);
	execSync(`npm install svelte@${targetVersion} --no-save --no-audit --no-fund`, {
		cwd: svelte2tsxDir,
		stdio: 'inherit'
	});
}
