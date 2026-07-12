/**
 * Demo realms for local/empty-registry preview.
 * Used when list_realms() returns nothing so the globe redesign can be exercised.
 */

export const DUMMY_REALMS = [
  {
    id: 'aaaaa-aa',
    name: 'Berlin Commons',
    realm_name: 'Berlin Commons',
    manifesto: 'A cooperative governance experiment rooted in the heart of Europe.',
    realm_stage: 'production',
    users_count: 420,
    created_at: Math.floor(Date.now() / 1000) - 86400 * 120,
    url: '',
  },
  {
    id: 'bbbbb-bb',
    name: 'Tokyo Mesh',
    realm_name: 'Tokyo Mesh',
    manifesto: 'Neighborhood-scale decision making across the Greater Tokyo Area.',
    realm_stage: 'beta',
    users_count: 1280,
    created_at: Math.floor(Date.now() / 1000) - 86400 * 60,
    url: '',
  },
  {
    id: 'ccccc-cc',
    name: 'São Paulo Agora',
    realm_name: 'São Paulo Agora',
    manifesto: 'Civic coordination for South America’s largest metro.',
    realm_stage: 'alpha',
    users_count: 310,
    created_at: Math.floor(Date.now() / 1000) - 86400 * 30,
    url: '',
  },
  {
    id: 'ddddd-dd',
    name: 'Nairobi Nexus',
    realm_name: 'Nairobi Nexus',
    manifesto: 'East African innovation network for shared public goods.',
    realm_stage: 'beta',
    users_count: 540,
    created_at: Math.floor(Date.now() / 1000) - 86400 * 45,
    url: '',
  },
  {
    id: 'eeeee-ee',
    name: 'San Francisco Collective',
    realm_name: 'San Francisco Collective',
    manifesto: 'Bay Area builders coordinating open infrastructure.',
    realm_stage: 'production',
    users_count: 890,
    created_at: Math.floor(Date.now() / 1000) - 86400 * 200,
    url: '',
  },
  {
    id: 'fffff-ff',
    name: 'Sydney Harbour',
    realm_name: 'Sydney Harbour',
    manifesto: 'Coastal stewardship and participatory budgeting down under.',
    realm_stage: 'alpha',
    users_count: 175,
    created_at: Math.floor(Date.now() / 1000) - 86400 * 15,
    url: '',
  },
];

/** @type {Record<string, { realmId: string, realmName: string, zones: object[], totalUsers: number }>} */
export const DUMMY_ZONE_DATA = {
  'aaaaa-aa': {
    realmId: 'aaaaa-aa',
    realmName: 'Berlin Commons',
    zones: [
      { h3_index: '', center_lat: 52.52, center_lng: 13.405, user_count: 280, location_name: 'Berlin' },
      { h3_index: '', center_lat: 52.39, center_lng: 13.06, user_count: 140, location_name: 'Potsdam' },
    ],
    totalUsers: 420,
  },
  'bbbbb-bb': {
    realmId: 'bbbbb-bb',
    realmName: 'Tokyo Mesh',
    zones: [
      { h3_index: '', center_lat: 35.6762, center_lng: 139.6503, user_count: 800, location_name: 'Tokyo' },
      { h3_index: '', center_lat: 35.4437, center_lng: 139.638, user_count: 480, location_name: 'Yokohama' },
    ],
    totalUsers: 1280,
  },
  'ccccc-cc': {
    realmId: 'ccccc-cc',
    realmName: 'São Paulo Agora',
    zones: [
      { h3_index: '', center_lat: -23.5505, center_lng: -46.6333, user_count: 310, location_name: 'São Paulo' },
    ],
    totalUsers: 310,
  },
  'ddddd-dd': {
    realmId: 'ddddd-dd',
    realmName: 'Nairobi Nexus',
    zones: [
      { h3_index: '', center_lat: -1.2921, center_lng: 36.8219, user_count: 540, location_name: 'Nairobi' },
    ],
    totalUsers: 540,
  },
  'eeeee-ee': {
    realmId: 'eeeee-ee',
    realmName: 'San Francisco Collective',
    zones: [
      { h3_index: '', center_lat: 37.7749, center_lng: -122.4194, user_count: 620, location_name: 'San Francisco' },
      { h3_index: '', center_lat: 37.3382, center_lng: -121.8863, user_count: 270, location_name: 'San Jose' },
    ],
    totalUsers: 890,
  },
  'fffff-ff': {
    realmId: 'fffff-ff',
    realmName: 'Sydney Harbour',
    zones: [
      { h3_index: '', center_lat: -33.8688, center_lng: 151.2093, user_count: 175, location_name: 'Sydney' },
    ],
    totalUsers: 175,
  },
};
