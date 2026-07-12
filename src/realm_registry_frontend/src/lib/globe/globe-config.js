/** @typedef {import('./hex-data.js').HexPolygon} HexPolygon */

export const H3_RESOLUTION = 6;
/** Fewer rings = fewer polygons = faster. */
export const INFLUENCE_RINGS = 2;

export const GLOBE_BG = '#FAFAFA';
/** Local grayscale land texture (served from static/, CSP-safe). */
export const GLOBE_IMAGE_URL = '/images/globe/earth-day.jpg';
/** High-contrast grayscale fallback. */
export const GLOBE_IMAGE_URL_GRAY = '/images/globe/earth-light.jpg';

export const AUTO_ROTATE_SPEED = 0.45;
export const AUTO_ROTATE_RESUME_MS = 5000;
export const FLY_TO_ALTITUDE = 1.75;
export const FLY_TO_MS = 900;
export const DIM_OPACITY = 0.3;

/** @param {number} distance */
export function grayHexStyle(distance, { totalUsers = 0, hasMultipleRealms = false } = {}) {
  const userBoost = Math.min((totalUsers / 50) * 0.15, 0.15);

  if (distance === 0) {
    return {
      fill: '#262626',
      stroke: hasMultipleRealms ? '#171717' : '#0A0A0A',
      opacity: Math.min(0.6 + userBoost, 0.8),
      altitude: 0.012,
      dashArray: null,
      strokeWeight: 2.5,
    };
  }
  if (distance === 1) {
    return {
      fill: '#404040',
      stroke: '#262626',
      opacity: 0.3 + userBoost * 0.4,
      altitude: 0.008,
      dashArray: null,
      strokeWeight: 1.2,
    };
  }
  return {
    fill: '#737373',
    stroke: '#525252',
    opacity: 0.14,
    altitude: 0.005,
    dashArray: null,
    strokeWeight: 0.8,
  };
}
