import { describe, expect, it } from 'vitest';
import { dismissAppSplash } from './app-splash';

describe('dismissAppSplash', () => {
	it('returns false when the splash node is missing', () => {
		const root = {
			getElementById: () => null
		};
		expect(dismissAppSplash(root)).toBe(false);
	});

	it('removes #app-splash even if later hydration work never reaches onMount', () => {
		let gone = false;
		const el = {
			remove() {
				gone = true;
			}
		};
		const root = {
			getElementById: (id: string) => (id === 'app-splash' ? el : null)
		};
		expect(dismissAppSplash(root)).toBe(true);
		expect(gone).toBe(true);
		expect(dismissAppSplash(root)).toBe(true);
	});
});
