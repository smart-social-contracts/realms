import {
  DIM_OPACITY,
  hexStyle,
  hexCapForResolution,
  influenceRingsForResolution,
} from './globe-config.js';
import { stageMarkerColor } from '../realm-stages.js';

/**
 * @typedef {object} HexRealmEntry
 * @property {object} realm
 * @property {number} users
 * @property {number} distance
 * @property {boolean} isCenter
 * @property {boolean} isHQ
 * @property {string[]} locations
 */

/**
 * @typedef {object} HexPolygon
 * @property {string} hexIndex
 * @property {HexRealmEntry[]} realms
 * @property {number} totalUsers
 * @property {string} fillColor
 * @property {string} strokeColor
 * @property {number} opacity
 * @property {number} weight
 * @property {string[]} realmIds
 * @property {number} minDistance
 * @property {object} geometry
 */

/**
 * @param {object[]} filteredRealms
 * @param {Record<string, { zones: object[] }>} realmZoneData
 * @param {object} h3
 * @param {{ matchingRealmIds?: Set<string> | null, dimNonMatching?: boolean, h3Resolution?: number, influenceRings?: number }} [options]
 * @returns {HexPolygon[]}
 */
export function buildHexPolygons(
  filteredRealms,
  realmZoneData,
  h3,
  {
    matchingRealmIds = null,
    dimNonMatching = false,
    h3Resolution = 4,
    influenceRings = influenceRingsForResolution(h3Resolution),
  } = {}
) {
  /** @type {Record<string, { realms: HexRealmEntry[], totalUsers: number }>} */
  const hexData = {};

  filteredRealms.forEach((realm) => {
    const realZoneData = realmZoneData[realm.id];
    if (!realZoneData?.zones?.length) return;

    realZoneData.zones.forEach((zone) => {
      let centerHexIndex;
      try {
        centerHexIndex = h3.latLngToCell(zone.center_lat, zone.center_lng, h3Resolution);
      } catch {
        try {
          centerHexIndex = h3.cellToParent?.(zone.h3_index, h3Resolution) ?? zone.h3_index;
        } catch {
          centerHexIndex = zone.h3_index;
        }
      }

      let influenceHexes;
      try {
        influenceHexes =
          influenceRings > 0 ? h3.gridDisk(centerHexIndex, influenceRings) : [centerHexIndex];
      } catch {
        influenceHexes =
          influenceRings > 0 && h3.kRing
            ? h3.kRing(centerHexIndex, influenceRings)
            : [centerHexIndex];
      }

      influenceHexes.forEach((hexIndex) => {
        let distance;
        try {
          distance = h3.gridDistance(centerHexIndex, hexIndex);
        } catch {
          distance = hexIndex === centerHexIndex ? 0 : 1;
        }

        if (!hexData[hexIndex]) {
          hexData[hexIndex] = { realms: [], totalUsers: 0 };
        }

        const existingEntry = hexData[hexIndex].realms.find((r) => r.realm.id === realm.id);
        if (existingEntry) {
          if (distance < existingEntry.distance) {
            existingEntry.distance = distance;
            existingEntry.isCenter = distance === 0;
            existingEntry.isHQ = distance === 0;
          }
          if (distance === 0) {
            existingEntry.users += zone.user_count;
          }
        } else {
          hexData[hexIndex].realms.push({
            realm,
            users: distance === 0 ? zone.user_count : 0,
            distance,
            isCenter: distance === 0,
            isHQ: distance === 0,
            locations: distance === 0 ? [zone.location_name || 'Zone'] : [],
          });
        }

        if (distance === 0) {
          hexData[hexIndex].totalUsers += zone.user_count;
        }
      });
    });
  });

  const polygons = [];

  for (const [hexIndex, data] of Object.entries(hexData)) {
    let ring;
    try {
      // formatAsGeoJson=true → [lng, lat]
      ring = h3.cellToBoundary(hexIndex, true).map(([lng, lat]) => [lng, lat]);
    } catch {
      try {
        ring = h3.cellToBoundary(hexIndex).map(([lat, lng]) => [lng, lat]);
      } catch {
        continue;
      }
    }
    if (ring.length) ring.push(ring[0]);

    const sortedRealms = [...data.realms].sort((a, b) => b.users - a.users);
    const minDistance = Math.min(...data.realms.map((r) => r.distance));
    const hasMultipleRealms = data.realms.length > 1;
    const style = hexStyle(minDistance, {
      totalUsers: data.totalUsers,
      hasMultipleRealms,
      h3Resolution,
    });

    const realmIds = data.realms.map((r) => r.realm.id);
    const isDimmed =
      dimNonMatching &&
      matchingRealmIds &&
      !realmIds.some((id) => matchingRealmIds.has(id));

    const opacity = isDimmed ? style.opacity * DIM_OPACITY : style.opacity;

    polygons.push({
      hexIndex,
      realms: sortedRealms,
      totalUsers: data.totalUsers,
      geometry: { type: 'Polygon', coordinates: [ring] },
      fillColor: style.fill,
      strokeColor: style.stroke,
      opacity,
      weight: style.weight,
      minDistance,
      realmIds,
    });
  }

  const cap = hexCapForResolution(h3Resolution);
  // Always keep every HQ / capital cell (distance 0). Only influence-ring
  // hexes are subject to the performance cap — otherwise dense realms
  // (e.g. Dominion) crowd out smaller Live realms like the E2E capitals.
  const hq = polygons.filter((p) => (p.minDistance ?? 99) === 0);
  const influence = polygons
    .filter((p) => (p.minDistance ?? 99) > 0)
    .sort((a, b) => (a.minDistance ?? 99) - (b.minDistance ?? 99));
  const influenceBudget = Math.max(0, cap - hq.length);
  return hq.concat(influence.slice(0, influenceBudget));
}

/**
 * Capital / HQ zone for a realm: highest user_count, stable tie-break on name.
 * @param {object[]} zones
 */
export function resolveCapitalZone(zones) {
  if (!zones?.length) return null;
  return [...zones].sort((a, b) => {
    const byUsers = (b.user_count || 0) - (a.user_count || 0);
    if (byUsers !== 0) return byUsers;
    return String(a.location_name || '').localeCompare(String(b.location_name || ''));
  })[0];
}

/**
 * Geometric center of the capital hex at the current display resolution.
 * Falls back to stored lat/lng when H3 cannot resolve the cell.
 * @param {object} zone
 * @param {object | null} h3
 * @param {number} h3Resolution
 * @returns {{ lat: number, lng: number, hexIndex: string | null }}
 */
export function capitalHexCenter(zone, h3, h3Resolution) {
  const fallback = {
    lat: Number(zone.center_lat),
    lng: Number(zone.center_lng),
    hexIndex: zone.h3_index || null,
  };
  if (!h3 || !Number.isFinite(fallback.lat) || !Number.isFinite(fallback.lng)) {
    return fallback;
  }

  let hexIndex = null;
  try {
    hexIndex = h3.latLngToCell(fallback.lat, fallback.lng, h3Resolution);
  } catch {
    try {
      if (zone.h3_index && h3.cellToParent) {
        hexIndex = h3.cellToParent(zone.h3_index, h3Resolution);
      } else {
        hexIndex = zone.h3_index || null;
      }
    } catch {
      hexIndex = zone.h3_index || null;
    }
  }

  if (!hexIndex) return fallback;

  try {
    const [lat, lng] = h3.cellToLatLng(hexIndex);
    return { lat, lng, hexIndex };
  } catch {
    return { ...fallback, hexIndex };
  }
}

/**
 * Prefer a distinct capital hex when several realms would otherwise stack on
 * the same cell. Falls back to a small screen-pixel fan only if no alternate
 * zone hex is available — pins stay at true hex centers whenever possible.
 * @param {object[]} markers
 * @param {Record<string, { zones: object[] }>} realmZoneData
 * @param {object | null} h3
 * @param {number} h3Resolution
 * @param {number} [radiusPx]
 */
export function separateCoincidentMarkers(
  markers,
  realmZoneData,
  h3,
  h3Resolution,
  radiusPx = 12
) {
  const keyOf = (m) =>
    m.hexIndex || `${Number(m.lat).toFixed(5)},${Number(m.lng).toFixed(5)}`;

  /** @type {Map<string, object[]>} */
  let groups = new Map();
  const regroup = () => {
    groups = new Map();
    for (const marker of markers) {
      const key = keyOf(marker);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(marker);
    }
  };
  regroup();

  for (const group of [...groups.values()]) {
    if (group.length < 2) continue;
    // Keep the first realm on the shared capital; move the rest to another
    // of their zones whose display hex differs.
    for (let i = 1; i < group.length; i++) {
      const marker = group[i];
      const zones = realmZoneData[marker.realmId]?.zones || [];
      const occupied = new Set(
        markers.filter((m) => m !== marker).map((m) => keyOf(m))
      );
      const ranked = [...zones].sort((a, b) => {
        const byUsers = (b.user_count || 0) - (a.user_count || 0);
        if (byUsers !== 0) return byUsers;
        return String(a.location_name || '').localeCompare(
          String(b.location_name || '')
        );
      });
      const alternate = ranked.find((zone) => {
        const center = capitalHexCenter(zone, h3, h3Resolution);
        const key = center.hexIndex ||
          `${center.lat.toFixed(5)},${center.lng.toFixed(5)}`;
        return !occupied.has(key);
      });
      if (!alternate) continue;
      const center = capitalHexCenter(alternate, h3, h3Resolution);
      marker.lat = center.lat;
      marker.lng = center.lng;
      marker.hexIndex = center.hexIndex;
      marker.location = alternate.location_name;
      marker.users = alternate.user_count;
    }
  }

  regroup();
  for (const group of groups.values()) {
    if (group.length < 2) {
      group[0].pixelOffset = [0, 0];
      continue;
    }
    group.forEach((marker, index) => {
      const angle = (2 * Math.PI * index) / group.length - Math.PI / 2;
      marker.pixelOffset = [
        Math.round(Math.cos(angle) * radiusPx),
        Math.round(Math.sin(angle) * radiusPx),
      ];
    });
  }

  return markers;
}

/**
 * @param {object[]} filteredRealms
 * @param {Record<string, { zones: object[] }>} realmZoneData
 * @param {{ matchingRealmIds?: Set<string> | null, dimNonMatching?: boolean, h3?: object | null, h3Resolution?: number }} [options]
 */
export function buildPointMarkers(
  filteredRealms,
  realmZoneData,
  {
    matchingRealmIds = null,
    dimNonMatching = false,
    h3 = null,
    h3Resolution = 4,
  } = {}
) {
  const markers = [];

  filteredRealms.forEach((realm) => {
    const zones = realmZoneData[realm.id]?.zones;
    if (!zones?.length) return;

    const capital = resolveCapitalZone(zones);
    if (!capital) return;

    const center = capitalHexCenter(capital, h3, h3Resolution);
    const isDimmed =
      dimNonMatching && matchingRealmIds && !matchingRealmIds.has(realm.id);

    markers.push({
      realmId: realm.id,
      realmName: realm.name || realm.realm_name,
      lat: center.lat,
      lng: center.lng,
      hexIndex: center.hexIndex,
      users: capital.user_count,
      totalUsers: realm.users_count || capital.user_count,
      location: capital.location_name,
      stage: realm.realm_stage,
      manifesto: realm.manifesto,
      color: stageMarkerColor(realm.realm_stage, { dimmed: isDimmed }),
      size: isDimmed ? 0.7 : 1,
      pixelOffset: [0, 0],
    });
  });

  return separateCoincidentMarkers(
    markers,
    realmZoneData,
    h3,
    h3Resolution
  );
}

/**
 * @param {object[]} realms
 * @param {Record<string, { zones: object[] }>} realmZoneData
 */
export function computeKpis(realms, realmZoneData) {
  const totalRealms = realms.length;
  const totalUsers = realms.reduce((sum, r) => sum + (r.users_count || 0), 0);

  const locationClusters = new Set();
  Object.values(realmZoneData).forEach((data) => {
    data.zones?.forEach((zone) => {
      const latBucket = Math.round(zone.center_lat);
      const lngBucket = Math.round(zone.center_lng);
      locationClusters.add(`${latBucket},${lngBucket}`);
    });
  });

  const stageCounts = {};
  realms.forEach((r) => {
    const stage = r.realm_stage || 'alpha';
    stageCounts[stage] = (stageCounts[stage] || 0) + 1;
  });

  return {
    totalRealms,
    totalUsers,
    locationClusters: locationClusters.size,
    stageCounts,
  };
}
