import {
  DIM_OPACITY,
  hexStyle,
  hexCapForResolution,
  influenceRingsForResolution,
} from './globe-config.js';

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
  return polygons
    .sort((a, b) => (a.minDistance ?? 99) - (b.minDistance ?? 99))
    .slice(0, cap);
}

/**
 * @param {object[]} filteredRealms
 * @param {Record<string, { zones: object[] }>} realmZoneData
 * @param {{ matchingRealmIds?: Set<string> | null, dimNonMatching?: boolean }} [options]
 */
export function buildPointMarkers(
  filteredRealms,
  realmZoneData,
  { matchingRealmIds = null, dimNonMatching = false } = {}
) {
  const markers = [];

  filteredRealms.forEach((realm) => {
    const zones = realmZoneData[realm.id]?.zones;
    if (!zones?.length) return;

    const primary = [...zones].sort((a, b) => b.user_count - a.user_count)[0];
    const isDimmed =
      dimNonMatching && matchingRealmIds && !matchingRealmIds.has(realm.id);

    markers.push({
      realmId: realm.id,
      realmName: realm.name || realm.realm_name,
      lat: primary.center_lat,
      lng: primary.center_lng,
      users: primary.user_count,
      color: isDimmed ? '#64748B' : '#00E5FF',
      size: isDimmed ? 0.7 : 1,
    });
  });

  return markers;
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
