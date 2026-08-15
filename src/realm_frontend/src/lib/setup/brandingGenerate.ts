export interface BrandingPalette {
	ink: string;
	wash: string;
	accent: string;
	mist: string;
}

export type LogoKind = 'orbits' | 'seal' | 'diamond' | 'crest' | 'arcs' | 'constellation';
export type BackgroundKind = 'grid' | 'aurora' | 'rings' | 'hatch' | 'stars' | 'horizon';

export const LOGO_KINDS: LogoKind[] = ['orbits', 'seal', 'diamond', 'crest', 'arcs', 'constellation'];
export const BACKGROUND_KINDS: BackgroundKind[] = [
	'grid',
	'aurora',
	'rings',
	'hatch',
	'stars',
	'horizon'
];

export interface GeneratedBranding {
	logoDataUrl: string;
	backgroundDataUrl: string;
	primaryColor: string;
	logoKind: LogoKind;
	backgroundKind: BackgroundKind;
}

const PALETTES: BrandingPalette[] = [
	{ ink: '#0b1120', wash: '#eef2ff', accent: '#4f46e5', mist: '#c7d2fe' },
	{ ink: '#1c1917', wash: '#faf6f1', accent: '#b45309', mist: '#fde68a' },
	{ ink: '#134e4a', wash: '#f0fdfa', accent: '#0f766e', mist: '#99f6e4' },
	{ ink: '#1e1b4b', wash: '#f5f3ff', accent: '#6d28d9', mist: '#ddd6fe' },
	{ ink: '#3f1d1d', wash: '#fff7ed', accent: '#c2410c', mist: '#fed7aa' },
	{ ink: '#0f172a', wash: '#f8fafc', accent: '#0369a1', mist: '#bae6fd' },
	{ ink: '#3b0764', wash: '#fdf4ff', accent: '#a21caf', mist: '#f5d0fe' },
	{ ink: '#14532d', wash: '#f0fdf4', accent: '#15803d', mist: '#bbf7d0' }
];

export function hashSeed(text: string): number {
	let hash = 2166136261;
	for (let i = 0; i < text.length; i += 1) {
		hash ^= text.charCodeAt(i);
		hash = Math.imul(hash, 16777619);
	}
	return hash >>> 0;
}

export function randomEntropy(): number {
	const cryptoObj = globalThis.crypto;
	if (cryptoObj?.getRandomValues) {
		const buf = new Uint32Array(1);
		cryptoObj.getRandomValues(buf);
		return buf[0] >>> 0;
	}
	return (Math.floor(Math.random() * 0xffffffff) ^ Date.now()) >>> 0;
}

export function paletteFromSeed(seed: number): BrandingPalette {
	return PALETTES[seed % PALETTES.length];
}

export function logoKindFromSeed(seed: number): LogoKind {
	return LOGO_KINDS[seed % LOGO_KINDS.length];
}

export function backgroundKindFromSeed(seed: number): BackgroundKind {
	return BACKGROUND_KINDS[(seed >>> 8) % BACKGROUND_KINDS.length];
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

function starPoints(cx: number, cy: number, outer: number, inner: number, points: number, rot: number): string {
	const coords: string[] = [];
	for (let i = 0; i < points * 2; i += 1) {
		const r = i % 2 === 0 ? outer : inner;
		const angle = ((i * (180 / points) + rot) * Math.PI) / 180;
		coords.push(`${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`);
	}
	return coords.join(' ');
}

function letter(name: string, palette: BrandingPalette, y = 142, size = 64): string {
	return `<text x="128" y="${y}" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="${size}" fill="${palette.ink}">${monogramFromName(name)}</text>`;
}

function wash(palette: BrandingPalette, id: string): string {
	return `<defs>
    <radialGradient id="${id}" cx="50%" cy="38%" r="70%">
      <stop offset="0%" stop-color="${palette.mist}"/>
      <stop offset="100%" stop-color="${palette.wash}"/>
    </radialGradient>
  </defs>
  <rect width="256" height="256" fill="${palette.wash}"/>
  <circle cx="128" cy="128" r="118" fill="url(#${id})"/>`;
}

function logoOrbits(name: string, seed: number, palette: BrandingPalette): string {
	const r1 = 86 + (seed % 12);
	const r2 = 58 + ((seed >> 3) % 10);
	return `${wash(palette, 'g')}
  <circle cx="128" cy="92" r="${r1}" fill="none" stroke="${palette.ink}" stroke-width="6"/>
  <circle cx="158" cy="148" r="${r1}" fill="none" stroke="${palette.ink}" stroke-width="6"/>
  <circle cx="98" cy="148" r="${r1}" fill="none" stroke="${palette.ink}" stroke-width="6"/>
  <circle cx="128" cy="128" r="${r2}" fill="none" stroke="${palette.accent}" stroke-width="3"/>
  ${letter(name, palette)}`;
}

function logoSeal(name: string, seed: number, palette: BrandingPalette): string {
	const ticks = 16 + (seed % 8);
	let marks = '';
	for (let i = 0; i < ticks; i += 1) {
		const a = (i / ticks) * Math.PI * 2;
		const x1 = 128 + Math.cos(a) * 98;
		const y1 = 128 + Math.sin(a) * 98;
		const x2 = 128 + Math.cos(a) * 108;
		const y2 = 128 + Math.sin(a) * 108;
		marks += `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${palette.ink}" stroke-width="2"/>`;
	}
	return `${wash(palette, 'g')}
  <circle cx="128" cy="128" r="104" fill="none" stroke="${palette.ink}" stroke-width="8"/>
  <circle cx="128" cy="128" r="86" fill="none" stroke="${palette.accent}" stroke-width="2"/>
  ${marks}
  ${letter(name, palette, 144, 72)}`;
}

function logoDiamond(name: string, seed: number, palette: BrandingPalette): string {
	const rot = seed % 20;
	return `${wash(palette, 'g')}
  <polygon points="${starPoints(128, 128, 102, 48, 4, rot)}" fill="none" stroke="${palette.ink}" stroke-width="5"/>
  <polygon points="${starPoints(128, 128, 68, 28, 4, rot + 45)}" fill="${palette.mist}" stroke="${palette.accent}" stroke-width="2"/>
  ${letter(name, palette)}`;
}

function logoCrest(name: string, seed: number, palette: BrandingPalette): string {
	const dip = 210 + (seed % 16);
	return `${wash(palette, 'g')}
  <path d="M128 36 L210 68 V128 C210 176 168 ${dip} 128 228 C88 ${dip} 46 176 46 128 V68 Z" fill="${palette.mist}" stroke="${palette.ink}" stroke-width="5"/>
  <path d="M128 58 L188 82 V128 C188 164 158 196 128 210 C98 196 68 164 68 128 V82 Z" fill="none" stroke="${palette.accent}" stroke-width="2"/>
  ${letter(name, palette, 138, 56)}`;
}

function logoArcs(name: string, seed: number, palette: BrandingPalette): string {
	const sweep = 200 + (seed % 40);
	return `${wash(palette, 'g')}
  <path d="M48 168 A88 88 0 0 1 208 96" fill="none" stroke="${palette.ink}" stroke-width="10" stroke-linecap="round"/>
  <path d="M56 196 A96 96 0 0 1 214 128" fill="none" stroke="${palette.accent}" stroke-width="5" stroke-linecap="round"/>
  <path d="M72 ${sweep} A70 70 0 0 1 188 72" fill="none" stroke="${palette.ink}" stroke-width="2" opacity="0.45"/>
  ${letter(name, palette, 168, 48)}`;
}

function logoConstellation(name: string, seed: number, palette: BrandingPalette): string {
	const pts = [
		[128, 46],
		[198, 88],
		[186, 176],
		[70, 176],
		[58, 88],
		[128, 128]
	];
	const shift = (seed % 17) - 8;
	const moved = pts.map(([x, y], i) => [x + (i % 2 === 0 ? shift : -shift), y] as const);
	const dots = moved
		.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="5" fill="${palette.ink}"/>`)
		.join('');
	const lines = [
		[0, 1],
		[1, 2],
		[2, 5],
		[5, 3],
		[3, 4],
		[4, 0],
		[0, 5]
	]
		.map(([a, b]) => {
			const [x1, y1] = moved[a];
			const [x2, y2] = moved[b];
			return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${palette.accent}" stroke-width="1.6"/>`;
		})
		.join('');
	return `${wash(palette, 'g')}${lines}${dots}${letter(name, palette, 148, 44)}`;
}

const LOGO_BUILDERS: Record<LogoKind, (name: string, seed: number, palette: BrandingPalette) => string> =
	{
		orbits: logoOrbits,
		seal: logoSeal,
		diamond: logoDiamond,
		crest: logoCrest,
		arcs: logoArcs,
		constellation: logoConstellation
	};

export function buildLogoSvg(
	realmName: string,
	seed: number,
	palette: BrandingPalette,
	kind: LogoKind = logoKindFromSeed(seed)
): string {
	const body = LOGO_BUILDERS[kind](realmName, seed, palette);
	return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="${escapeXml(realmName)}">${body}</svg>`;
}

function bgGrid(name: string, seed: number, palette: BrandingPalette): string {
	const rot = (seed % 24) - 12;
	const offset = 80 + (seed % 40);
	return `<rect width="1600" height="900" fill="url(#wash)"/>
  <rect width="1600" height="900" fill="url(#grid)"/>
  <g fill="none" stroke="${palette.ink}" stroke-width="1.2" opacity="0.12" transform="translate(800 420)">
    <polygon points="${hexPoints(0, 0, 340, rot)}"/>
    <polygon points="${hexPoints(0, 0, 260, rot + 30)}"/>
    <circle r="210"/>
    <line x1="-380" y1="0" x2="380" y2="0"/>
  </g>
  <g fill="none" stroke="${palette.accent}" stroke-width="1" opacity="0.18" transform="translate(${800 + offset} ${380 - offset / 2})">
    <circle r="280"/>
  </g>
  <text x="80" y="820" font-family="Georgia, 'Times New Roman', serif" font-size="28" fill="${palette.ink}" opacity="0.18">${escapeXml(name)}</text>`;
}

function bgAurora(name: string, seed: number, palette: BrandingPalette): string {
	const x = 400 + (seed % 600);
	return `<rect width="1600" height="900" fill="${palette.wash}"/>
  <ellipse cx="${x}" cy="220" rx="520" ry="220" fill="${palette.mist}" opacity="0.7"/>
  <ellipse cx="${1600 - x}" cy="640" rx="480" ry="260" fill="${palette.accent}" opacity="0.12"/>
  <ellipse cx="800" cy="400" rx="360" ry="180" fill="${palette.mist}" opacity="0.35"/>
  <text x="80" y="820" font-family="Georgia, 'Times New Roman', serif" font-size="28" fill="${palette.ink}" opacity="0.16">${escapeXml(name)}</text>`;
}

function bgRings(name: string, seed: number, palette: BrandingPalette): string {
	const cx = 720 + (seed % 180);
	let rings = '';
	for (let i = 1; i <= 8; i += 1) {
		rings += `<circle cx="${cx}" cy="400" r="${80 + i * 70}" fill="none" stroke="${i % 2 ? palette.ink : palette.accent}" stroke-width="1" opacity="${(0.16 - i * 0.012).toFixed(3)}"/>`;
	}
	return `<rect width="1600" height="900" fill="url(#wash)"/>${rings}
  <text x="80" y="820" font-family="Georgia, 'Times New Roman', serif" font-size="28" fill="${palette.ink}" opacity="0.16">${escapeXml(name)}</text>`;
}

function bgHatch(name: string, seed: number, palette: BrandingPalette): string {
	const rot = 18 + (seed % 28);
	return `<rect width="1600" height="900" fill="url(#wash)"/>
  <pattern id="hatch" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(${rot})">
    <line x1="0" y1="0" x2="0" y2="28" stroke="${palette.ink}" stroke-width="1" opacity="0.08"/>
  </pattern>
  <rect width="1600" height="900" fill="url(#hatch)"/>
  <polygon points="${hexPoints(1100, 280, 260, rot)}" fill="none" stroke="${palette.accent}" stroke-width="1.2" opacity="0.2"/>
  <text x="80" y="820" font-family="Georgia, 'Times New Roman', serif" font-size="28" fill="${palette.ink}" opacity="0.16">${escapeXml(name)}</text>`;
}

function bgStars(name: string, seed: number, palette: BrandingPalette): string {
	let dots = '';
	let n = seed || 1;
	for (let i = 0; i < 48; i += 1) {
		n = Math.imul(n, 1664525) + 1013904223;
		const x = (n >>> 0) % 1600;
		n = Math.imul(n, 1664525) + 1013904223;
		const y = (n >>> 0) % 900;
		const r = 1 + ((n >>> 8) % 3);
		dots += `<circle cx="${x}" cy="${y}" r="${r}" fill="${palette.ink}" opacity="0.22"/>`;
	}
	return `<rect width="1600" height="900" fill="url(#wash)"/>${dots}
  <polygon points="${starPoints(1180, 260, 90, 38, 5, seed % 40)}" fill="none" stroke="${palette.accent}" stroke-width="1.2" opacity="0.28"/>
  <text x="80" y="820" font-family="Georgia, 'Times New Roman', serif" font-size="28" fill="${palette.ink}" opacity="0.16">${escapeXml(name)}</text>`;
}

function bgHorizon(name: string, seed: number, palette: BrandingPalette): string {
	const rise = 480 + (seed % 120);
	return `<rect width="1600" height="900" fill="${palette.wash}"/>
  <path d="M0 ${rise} C 400 ${rise - 80} 900 ${rise + 90} 1600 ${rise - 20} L1600 900 L0 900 Z" fill="${palette.mist}" opacity="0.7"/>
  <path d="M0 ${rise + 40} C 500 ${rise + 10} 1000 ${rise + 110} 1600 ${rise + 30} L1600 900 L0 900 Z" fill="${palette.accent}" opacity="0.08"/>
  <circle cx="${400 + (seed % 700)}" cy="${200 + (seed % 80)}" r="70" fill="${palette.mist}" opacity="0.55"/>
  <text x="80" y="820" font-family="Georgia, 'Times New Roman', serif" font-size="28" fill="${palette.ink}" opacity="0.16">${escapeXml(name)}</text>`;
}

const BACKGROUND_BUILDERS: Record<
	BackgroundKind,
	(name: string, seed: number, palette: BrandingPalette) => string
> = {
	grid: bgGrid,
	aurora: bgAurora,
	rings: bgRings,
	hatch: bgHatch,
	stars: bgStars,
	horizon: bgHorizon
};

export function buildBackgroundSvg(
	realmName: string,
	seed: number,
	palette: BrandingPalette,
	kind: BackgroundKind = backgroundKindFromSeed(seed)
): string {
	const rot = (seed % 24) - 12;
	const body = BACKGROUND_BUILDERS[kind](realmName, seed, palette);
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
  ${body}
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
	entropy?: number;
}): GeneratedBranding {
	const name = input.realmName.trim() || 'Realm';
	const entropy = input.entropy ?? randomEntropy();
	const seed = hashSeed(`${name}\n${(input.manifesto || '').trim()}\n${entropy}`);
	const palette = paletteFromSeed(seed);
	const logoKind = logoKindFromSeed(seed);
	const backgroundKind = backgroundKindFromSeed(hashSeed(`bg:${entropy}:${name}`));
	return {
		logoDataUrl: svgToDataUrl(buildLogoSvg(name, seed, palette, logoKind)),
		backgroundDataUrl: svgToDataUrl(buildBackgroundSvg(name, seed, palette, backgroundKind)),
		primaryColor: palette.accent,
		logoKind,
		backgroundKind
	};
}

function escapeXml(value: string): string {
	return value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}
