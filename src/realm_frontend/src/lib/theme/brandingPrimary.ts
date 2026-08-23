export const DEFAULT_PRIMARY_COLOR = '#3b82f6';

const PRIMARY_COLOR_RE = /^#[0-9a-fA-F]{6}$/;

export type PrimaryPalette = Record<'50' | '100' | '200' | '300' | '400' | '500' | '600' | '700' | '800' | '900', string>;

const SHADE_KEYS = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900'] as const;

const LIGHT_MIX: Record<'50' | '100' | '200' | '300' | '400' | '500', number> = {
	50: 0.95,
	100: 0.9,
	200: 0.75,
	300: 0.6,
	400: 0.4,
	500: 0.2
};

const DARK_MIX: Record<'700' | '800' | '900', number> = {
	700: 0.2,
	800: 0.4,
	900: 0.6
};

function hexToRgb(hex: string): { r: number; g: number; b: number } {
	return {
		r: parseInt(hex.slice(1, 3), 16),
		g: parseInt(hex.slice(3, 5), 16),
		b: parseInt(hex.slice(5, 7), 16)
	};
}

function rgbToHex(r: number, g: number, b: number): string {
	const clamp = (value: number) => Math.max(0, Math.min(255, Math.round(value)));
	return `#${[clamp(r), clamp(g), clamp(b)]
		.map((value) => value.toString(16).padStart(2, '0'))
		.join('')}`;
}

function mixWithWhite(hex: string, amount: number): string {
	const { r, g, b } = hexToRgb(hex);
	return rgbToHex(r + (255 - r) * amount, g + (255 - g) * amount, b + (255 - b) * amount);
}

function mixWithBlack(hex: string, amount: number): string {
	const { r, g, b } = hexToRgb(hex);
	return rgbToHex(r * (1 - amount), g * (1 - amount), b * (1 - amount));
}

export function parsePrimaryColor(value: unknown): string | null {
	if (typeof value !== 'string') return null;
	const trimmed = value.trim();
	if (!PRIMARY_COLOR_RE.test(trimmed)) return null;
	return trimmed.toLowerCase();
}

export function paletteFromPrimary(hex: string): PrimaryPalette {
	const base = parsePrimaryColor(hex) ?? DEFAULT_PRIMARY_COLOR;
	return {
		50: mixWithWhite(base, LIGHT_MIX[50]),
		100: mixWithWhite(base, LIGHT_MIX[100]),
		200: mixWithWhite(base, LIGHT_MIX[200]),
		300: mixWithWhite(base, LIGHT_MIX[300]),
		400: mixWithWhite(base, LIGHT_MIX[400]),
		500: mixWithWhite(base, LIGHT_MIX[500]),
		600: base,
		700: mixWithBlack(base, DARK_MIX[700]),
		800: mixWithBlack(base, DARK_MIX[800]),
		900: mixWithBlack(base, DARK_MIX[900])
	};
}

export function primaryCssVariables(hex: string): Record<string, string> {
	const palette = paletteFromPrimary(hex);
	const vars: Record<string, string> = {};
	for (const shade of SHADE_KEYS) {
		vars[`--color-primary-${shade}`] = palette[shade];
	}
	return vars;
}

export function applyBrandingPrimary(hex: string): Record<string, string> {
	const vars = primaryCssVariables(hex);
	if (typeof document === 'undefined') return vars;
	const root = document.documentElement;
	for (const [key, value] of Object.entries(vars)) {
		root.style.setProperty(key, value);
	}
	return vars;
}

export function readPrimaryCssVariables(): Record<string, string> {
	if (typeof document === 'undefined') return {};
	const root = document.documentElement;
	const style = getComputedStyle(root);
	const vars: Record<string, string> = {};
	for (const shade of SHADE_KEYS) {
		const name = `--color-primary-${shade}`;
		const value = style.getPropertyValue(name).trim();
		if (value) vars[name] = value;
	}
	return vars;
}
