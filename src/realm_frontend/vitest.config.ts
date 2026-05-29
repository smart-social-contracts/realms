import { defineConfig } from 'vitest/config';

// Lightweight unit-test config (no SvelteKit plugin) for plain TS modules
// such as the crypto sharing helpers.
export default defineConfig({
	test: {
		environment: 'node',
		include: ['src/**/*.test.ts']
	}
});
