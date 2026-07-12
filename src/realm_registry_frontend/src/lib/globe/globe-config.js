/** Zoom-adaptive H3 + map styling for the registry map. */

/** Base resolution used when fetching zone data from backends. */
export const ZONE_DATA_RESOLUTION = 6;

export const MAP_BG = '#FAFAFA';
export const FLY_TO_MS = 900;
export const DIM_OPACITY = 0.35;

/** Leaflet/MapLibre zoom → H3 display resolution (coarse far, fine near). */
export function h3ResolutionForZoom(zoom) {
  if (zoom < 3) return 2;
  if (zoom < 5) return 3;
  if (zoom < 7) return 4;
  if (zoom < 9) return 5;
  if (zoom < 11) return 6;
  if (zoom < 13) return 7;
  return 8;
}

/** Fewer influence rings when hexes are already large. */
export function influenceRingsForResolution(resolution) {
  if (resolution <= 2) return 0;
  if (resolution <= 3) return 1;
  if (resolution <= 5) return 2;
  if (resolution <= 7) return 3;
  return 2;
}

/** Max hex polygons to render at each resolution (performance). */
export function hexCapForResolution(resolution) {
  if (resolution <= 2) return 80;
  if (resolution <= 3) return 160;
  if (resolution <= 4) return 320;
  if (resolution <= 5) return 500;
  if (resolution <= 6) return 800;
  if (resolution <= 7) return 1200;
  return 1600;
}

/**
 * Soft teal/gray hex styling — close to staging IC map, light Realms aesthetic.
 * @param {number} distance
 */
export function hexStyle(distance, { totalUsers = 0, hasMultipleRealms = false, h3Resolution = 6 } = {}) {
  const userBoost = Math.min((totalUsers / 50) * 0.1, 0.12);
  const fine = h3Resolution >= 6;

  if (distance === 0) {
    return {
      fill: hasMultipleRealms ? '#5B8A8A' : '#6BA3A3',
      stroke: '#1A1A1A',
      opacity: Math.min((fine ? 0.42 : 0.34) + userBoost, 0.65),
      weight: fine ? 1.6 : 1.2,
    };
  }
  if (distance === 1) {
    return {
      fill: '#8BB8B8',
      stroke: '#3A3A3A',
      opacity: (fine ? 0.22 : 0.16) + userBoost * 0.35,
      weight: fine ? 1.1 : 0.9,
    };
  }
  return {
    fill: '#A8C9C9',
    stroke: '#5A5A5A',
    opacity: fine ? 0.12 : 0.08,
    weight: 0.7,
  };
}

/** @deprecated use hexStyle */
export function grayHexStyle(distance, opts = {}) {
  return hexStyle(distance, opts);
}

/**
 * Abstract Realms basemap: land / water / roads only.
 * Strips political borders, all place/water labels, and shields.
 * @param {object} style
 */
export function stripPoliticalLayers(style) {
  if (!style?.layers) return style;
  const next = { ...style, layers: [] };
  for (const layer of style.layers) {
    const id = String(layer.id || '').toLowerCase();
    const sourceLayer = String(layer['source-layer'] || '').toLowerCase();
    const type = String(layer.type || '').toLowerCase();

    const isBoundary =
      sourceLayer.includes('boundary') ||
      sourceLayer === 'admin' ||
      id.includes('boundary') ||
      id.includes('admin') ||
      id.includes('disputed');

    const isLabel =
      type === 'symbol' ||
      id.includes('label') ||
      id.includes('name') ||
      id.includes('shield') ||
      id.includes('airport') ||
      sourceLayer.includes('place') ||
      sourceLayer.includes('housenumber') ||
      sourceLayer === 'poi' ||
      sourceLayer.includes('mountain_peak') ||
      sourceLayer.includes('water_name') ||
      sourceLayer.includes('transportation_name');

    if (isBoundary || isLabel) continue;
    next.layers.push(layer);
  }
  // Neutral lighting — no day/night terminator on the globe
  delete next.light;
  return next;
}
