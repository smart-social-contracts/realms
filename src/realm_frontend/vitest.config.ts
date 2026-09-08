import { defineConfig } from 'vitest/config';

// Lightweight unit-test config (no SvelteKit plugin) for plain TS modules
// such as the crypto sharing helpers.
export default defineConfig({
	define: {
		__REALMS_TEST_BUILD__: true
	},
	test: {
		environment: 'node',
		include: ['src/**/*.test.ts']
	}
});
