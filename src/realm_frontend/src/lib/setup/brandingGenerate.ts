export interface BrandingPalette {
	ink: string;
	wash: string;
	accent: string;
	mist: string;
}

export interface GeneratedBranding {
	logoDataUrl: string;
	backgroundDataUrl: string;
	primaryColor: string;
}

const PALETTES: BrandingPalette[] = [
	{ ink: '#0b1120', wash: '#eef2ff', accent: '#4f46e5', mist: '#c7d2fe' },
	{ ink: '#1c1917', wash: '#faf6f1', accent: '#b45309', mist: '#fde68a' },
	{ ink: '#134e4a', wash: '#f0fdfa', accent: '#0f766e', mist: '#99f6e4' },
	{ ink: '#1e1b4b', wash: '#f5f3ff', accent: '#6d28d9', mist: '#ddd6fe' },
	{ ink: '#3f1d1d', wash: '#fff7ed', accent: '#c2410c', mist: '#fed7aa' },
	{ ink: '#0f172a', wash: '#f8fafc', accent: '#0369a1', mist: '#bae6fd' }
];

export function hashSeed(text: string): number {
	let hash = 2166136261;
	for (let i = 0; i < text.length; i += 1) {
		hash ^= text.charCodeAt(i);
		hash = Math.imul(hash, 16777619);
	}
	return hash >>> 0;
}

export function paletteFromSeed(seed: number): BrandingPalette {
	return PALETTES[seed % PALETTES.length];
}

export function monogramFromName(name: string): string {
	const letter = name.trim().replace(/[^A-Za-z0-9]/g, '').charAt(0);
	return (letter || 'R').toUpperCase();
}

function hexPoints(cx: number, cy: number, r: number, rotation: number): string {
	const points: string[] = [];
	for (let i = 0; i < 6; i += 1) {
		const angle = ((i * 60 + rotation) * Math.PI) / 180;
		points.push(`${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`);
	}
	return points.join(' ');
}

export function buildLogoSvg(realmName: string, seed: number, palette: BrandingPalette): string {
	const letter = monogramFromName(realmName);
	const rot = seed % 36;
	const r1 = 86 + (seed % 12);
	const r2 = 58 + ((seed >> 3) % 10);
	return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="${escapeXml(realmName)}">
  <defs>
    <radialGradient id="g" cx="50%" cy="38%" r="70%">
      <stop offset="0%" stop-color="${palette.mist}"/>
      <stop offset="100%" stop-color="${palette.wash}"/>
    </radialGradient>
  </defs>
  <rect width="256" height="256" fill="${palette.wash}"/>
  <circle cx="128" cy="128" r="118" fill="url(#g)"/>
  <polygon points="${hexPoints(128, 128, 108, rot)}" fill="none" stroke="${palette.ink}" stroke-width="1.2" opacity="0.35"/>
  <polygon points="${hexPoints(128, 128, 92, rot + 30)}" fill="none" stroke="${palette.accent}" stroke-width="1.4" opacity="0.55"/>
  <circle cx="128" cy="92" r="${r1}" fill="none" stroke="${palette.ink}" stroke-width="6"/>
  <circle cx="158" cy="148" r="${r1}" fill="none" stroke="${palette.ink}" stroke-width="6"/>
  <circle cx="98" cy="148" r="${r1}" fill="none" stroke="${palette.ink}" stroke-width="6"/>
  <circle cx="128" cy="128" r="${r2}" fill="none" stroke="${palette.accent}" stroke-width="3"/>
  <text x="128" y="142" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="64" fill="${palette.ink}">${letter}</text>
</svg>`;
}

export function buildBackgroundSvg(realmName: string, seed: number, palette: BrandingPalette): string {
	const rot = (seed % 24) - 12;
	const offset = 80 + (seed % 40);
	return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" role="img" aria-label="">
  <defs>
    <radialGradient id="wash" cx="50%" cy="28%" r="80%">
      <stop offset="0%" stop-color="${palette.mist}" stop-opacity="0.85"/>
      <stop offset="55%" stop-color="${palette.wash}"/>
      <stop offset="100%" stop-color="#ffffff"/>
    </radialGradient>
    <pattern id="grid" width="72" height="72" patternUnits="userSpaceOnUse" patternTransform="rotate(${rot})">
      <path d="M72 0H0V72" fill="none" stroke="${palette.ink}" stroke-width="1" opacity="0.07"/>
    </pattern>
  </defs>
  <rect width="1600" height="900" fill="url(#wash)"/>
  <rect width="1600" height="900" fill="url(#grid)"/>
  <g fill="none" stroke="${palette.ink}" stroke-width="1.2" opacity="0.12" transform="translate(800 420)">
    <polygon points="${hexPoints(0, 0, 340, rot)}"/>
    <polygon points="${hexPoints(0, 0, 260, rot + 30)}"/>
    <circle r="210"/>
    <circle r="150"/>
    <line x1="-380" y1="0" x2="380" y2="0"/>
    <line x1="0" y1="-300" x2="0" y2="300"/>
  </g>
  <g fill="none" stroke="${palette.accent}" stroke-width="1" opacity="0.18" transform="translate(${800 + offset} ${380 - offset / 2})">
    <circle r="280"/>
    <circle r="190"/>
  </g>
  <text x="80" y="820" font-family="Georgia, 'Times New Roman', serif" font-size="28" fill="${palette.ink}" opacity="0.18">${escapeXml(realmName)}</text>
</svg>`;
}

export function svgToDataUrl(svg: string): string {
	const bytes = new TextEncoder().encode(svg);
	let binary = '';
	for (const byte of bytes) binary += String.fromCharCode(byte);
	return `data:image/svg+xml;base64,${btoa(binary)}`;
}

export function generateBrandingAssets(input: {
	realmName: string;
	manifesto?: string;
}): GeneratedBranding {
	const name = input.realmName.trim() || 'Realm';
	const seed = hashSeed(`${name}\n${(input.manifesto || '').trim()}`);
	const palette = paletteFromSeed(seed);
	return {
		logoDataUrl: svgToDataUrl(buildLogoSvg(name, seed, palette)),
		backgroundDataUrl: svgToDataUrl(buildBackgroundSvg(name, seed, palette)),
		primaryColor: palette.accent
	};
}

function escapeXml(value: string): string {
	return value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}
