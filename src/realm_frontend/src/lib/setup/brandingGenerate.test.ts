import { describe, expect, it } from 'vitest';
import {
	BACKGROUND_KINDS,
	LOGO_KINDS,
	buildBackgroundSvg,
	buildLogoSvg,
	generateBrandingAssets,
	hashSeed,
	monogramFromName,
	paletteFromSeed
} from './brandingGenerate';

describe('brandingGenerate', () => {
	it('is deterministic for the same name, manifesto, and entropy', () => {
		const input = { realmName: 'RealmTest6', manifesto: 'Verifiable rules', entropy: 42 };
		expect(generateBrandingAssets(input)).toEqual(generateBrandingAssets(input));
	});

	it('changes when entropy changes, even with the same manifesto', () => {
		const a = generateBrandingAssets({ realmName: 'RealmTest6', manifesto: 'Peace', entropy: 1 });
		const b = generateBrandingAssets({ realmName: 'RealmTest6', manifesto: 'Peace', entropy: 2 });
		expect(a.logoDataUrl).not.toBe(b.logoDataUrl);
		expect(a.backgroundDataUrl).not.toBe(b.backgroundDataUrl);
	});

	it('returns base64 svg data URLs and an accent color', () => {
		const assets = generateBrandingAssets({ realmName: 'Agora', entropy: 7 });
		expect(assets.logoDataUrl.startsWith('data:image/svg+xml;base64,')).toBe(true);
		expect(assets.backgroundDataUrl.startsWith('data:image/svg+xml;base64,')).toBe(true);
		expect(assets.primaryColor).toMatch(/^#[0-9a-f]{6}$/i);
		expect(LOGO_KINDS).toContain(assets.logoKind);
		expect(BACKGROUND_KINDS).toContain(assets.backgroundKind);
	});

	it('can render every logo and background kind', () => {
		const seed = hashSeed('Helia');
		const palette = paletteFromSeed(seed);
		for (const kind of LOGO_KINDS) {
			const svg = buildLogoSvg('Helia', seed, palette, kind);
			expect(svg).toContain('<svg');
			expect(svg).toContain('>H<');
		}
		for (const kind of BACKGROUND_KINDS) {
			expect(buildBackgroundSvg('Helia', seed, palette, kind)).toContain('Helia');
		}
	});

	it('takes the first letter of the realm name', () => {
		expect(monogramFromName('  syntropia')).toBe('S');
		expect(monogramFromName('')).toBe('R');
	});
});
