import { describe, expect, it } from 'vitest';
import {
	buildBackgroundSvg,
	buildLogoSvg,
	generateBrandingAssets,
	hashSeed,
	monogramFromName,
	paletteFromSeed
} from './brandingGenerate';

describe('brandingGenerate', () => {
	it('is deterministic for the same name and manifesto', () => {
		const a = generateBrandingAssets({ realmName: 'RealmTest6', manifesto: 'Verifiable rules' });
		const b = generateBrandingAssets({ realmName: 'RealmTest6', manifesto: 'Verifiable rules' });
		expect(a).toEqual(b);
	});

	it('changes when the manifesto changes', () => {
		const a = generateBrandingAssets({ realmName: 'RealmTest6', manifesto: 'Peace' });
		const b = generateBrandingAssets({ realmName: 'RealmTest6', manifesto: 'Justice' });
		expect(a.logoDataUrl).not.toBe(b.logoDataUrl);
		expect(a.backgroundDataUrl).not.toBe(b.backgroundDataUrl);
	});

	it('returns base64 svg data URLs and an accent color', () => {
		const assets = generateBrandingAssets({ realmName: 'Agora' });
		expect(assets.logoDataUrl.startsWith('data:image/svg+xml;base64,')).toBe(true);
		expect(assets.backgroundDataUrl.startsWith('data:image/svg+xml;base64,')).toBe(true);
		expect(assets.primaryColor).toMatch(/^#[0-9a-f]{6}$/i);
	});

	it('embeds the realm monogram in the logo', () => {
		const seed = hashSeed('Helia');
		const svg = buildLogoSvg('Helia', seed, paletteFromSeed(seed));
		expect(svg).toContain('>H<');
		expect(buildBackgroundSvg('Helia', seed, paletteFromSeed(seed))).toContain('Helia');
	});

	it('takes the first letter of the realm name', () => {
		expect(monogramFromName('  syntropia')).toBe('S');
		expect(monogramFromName('')).toBe('R');
	});
});
