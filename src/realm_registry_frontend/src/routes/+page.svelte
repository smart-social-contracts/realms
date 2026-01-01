<script>
  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';

  let backend;
  let realms = [];
  let loading = true;
  let error = null;
  let searchQuery = '';
  let filteredRealms = [];
  let showCreateModal = false;
  let viewMode = 'list'; // 'list' or 'map'
  let mapContainer;
  let map;
  let L;
  let h3;
  let hexLayer = null;
  let markerLayer = null; // Layer for location markers (visible only when zoomed out)
  const H3_RESOLUTION = 6; // Resolution 6 = ~3.2km hex edge (good for city level)
  const MARKER_HIDE_ZOOM = 5; // Hide markers when zoom >= this level (hexes become visible)

  // Get commit hash from meta tag
  let commitHash = '';
  // Get commit datetime from meta tag
  let commitDatetime = '';
  // Get version from meta tag
  let version = '';

  onMount(async () => {
    if (browser) {
      // Only import backend in browser context
      const { backend: b } = await import("$lib/canisters");
      backend = b;
      await loadRealms();
      
      // Get version info from meta tags
      const commitHashMeta = document.querySelector('meta[name="commit-hash"]');
      if (commitHashMeta) {
        commitHash = commitHashMeta.getAttribute('content') || '';
        // Format to show only first 7 characters if it's a full hash
        if (commitHash && commitHash !== 'COMMIT_HASH_PLACEHOLDER' && commitHash.length > 7) {
          commitHash = commitHash.substring(0, 7);
        }
      }
      
      const commitDatetimeMeta = document.querySelector('meta[name="commit-datetime"]');
      if (commitDatetimeMeta) {
        commitDatetime = commitDatetimeMeta.getAttribute('content') || '';
      }
      
      const versionMeta = document.querySelector('meta[name="version"]');
      if (versionMeta) {
        version = versionMeta.getAttribute('content') || '';
      }
      
      // Use build-time values as fallback for local development
      // @ts-ignore - Vite injects this at build time
      if (!version || version === 'VERSION_PLACEHOLDER') {
        version = typeof __BUILD_VERSION__ !== 'undefined' ? __BUILD_VERSION__ : 'dev';
      }
      // @ts-ignore - Vite injects this at build time
      if (!commitHash || commitHash === 'COMMIT_HASH_PLACEHOLDER') {
        commitHash = typeof __BUILD_COMMIT__ !== 'undefined' ? __BUILD_COMMIT__ : 'local';
      }
      // @ts-ignore - Vite injects this at build time
      if (!commitDatetime || commitDatetime === 'COMMIT_DATETIME_PLACEHOLDER') {
        commitDatetime = typeof __BUILD_TIME__ !== 'undefined' ? __BUILD_TIME__ : new Date().toISOString().replace('T', ' ').substring(0, 19);
      }
    }
  });

  async function loadRealms() {
    try {
      loading = true;
      error = null;
      const response = await backend.list_realms();
      realms = response || [];
      filteredRealms = realms;
      loading = false;
      // Fetch user counts from each realm's status endpoint
      fetchUserCounts();
    } catch (err) {
      error = err.message || 'Failed to load realms';
      loading = false;
    }
  }

  function isLocalDevelopment() {
    return window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1');
  }

  async function fetchUserCounts() {
    // Fetch user counts from each realm's backend via Candid
    const { Actor, HttpAgent } = await import('@dfinity/agent');
    const { Principal } = await import('@dfinity/principal');
    
    // Minimal IDL for the status method - only need users_count from the response
    const { IDL } = await import('@dfinity/candid');
    
    const statusIdlFactory = ({ IDL }) => {
      const StatusData = IDL.Record({
        'status': IDL.Text,
        'demo_mode': IDL.Bool,
        'transfers_count': IDL.Nat,
        'codexes_count': IDL.Nat,
        'proposals_count': IDL.Nat,
        'realms_count': IDL.Nat,
        'version': IDL.Text,
        'extensions': IDL.Vec(IDL.Text),
        'disputes_count': IDL.Nat,
        'commit': IDL.Text,
        'instruments_count': IDL.Nat,
        'organizations_count': IDL.Nat,
        'mandates_count': IDL.Nat,
        'tasks_count': IDL.Nat,
        'votes_count': IDL.Nat,
        'licenses_count': IDL.Nat,
        'users_count': IDL.Nat,
        'trades_count': IDL.Nat,
      });
      const ApiResponse = IDL.Record({
        'data': IDL.Variant({ 'status': StatusData }),
        'success': IDL.Bool,
      });
      return IDL.Service({
        'status': IDL.Func([], [ApiResponse], ['query']),
      });
    };
    
    const host = isLocalDevelopment() 
      ? 'http://localhost:8000' 
      : 'https://icp0.io';
    
    const updates = await Promise.allSettled(
      realms.map(async (realm) => {
        try {
          const agent = new HttpAgent({ host });
          
          // Fetch root key for local development
          if (isLocalDevelopment()) {
            await agent.fetchRootKey();
          }
          
          const actor = Actor.createActor(statusIdlFactory, {
            agent,
            canisterId: Principal.fromText(realm.id),
          });
          
          const response = await actor.status();
          if (response.success && response.data.status) {
            const usersCount = Number(response.data.status.users_count);
            return { id: realm.id, users_count: usersCount };
          }
        } catch (e) {
          console.debug(`Could not fetch status for ${realm.id}:`, e.message);
        }
        return null;
      })
    );
    
    // Update realms with fetched counts
    updates.forEach(result => {
      if (result.status === 'fulfilled' && result.value) {
        const { id, users_count } = result.value;
        realms = realms.map(r => r.id === id ? { ...r, users_count } : r);
        filteredRealms = filteredRealms.map(r => r.id === id ? { ...r, users_count } : r);
      }
    });
  }

  function formatTimeAgo(timestamp) {
    const now = Date.now();
    const date = new Date(timestamp * 1000);
    const seconds = Math.floor((now - date.getTime()) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    if (seconds < 2592000) return `${Math.floor(seconds / 604800)}w ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function formatFullDate(timestamp) {
    return new Date(timestamp * 1000).toLocaleString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      // Brief visual feedback could be added here
    });
  }


  // formatDate kept for backwards compatibility
  function formatDate(timestamp) {
    return formatTimeAgo(timestamp);
  }

  function truncateId(id) {
    if (!id || id.length <= 16) return id;
    return `${id.slice(0, 8)}...${id.slice(-4)}`;
  }

  function ensureProtocol(url) {
    if (!url) return '';
    // If URL already has a protocol, return as-is
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    // Use http for localhost, https for production
    const isLocal = url.includes('localhost') || url.includes('127.0.0.1');
    return isLocal ? `http://${url}` : `https://${url}`;
  }


  function searchRealms() {
    if (!searchQuery.trim()) {
      filteredRealms = realms;
      return;
    }
    
    const query = searchQuery.toLowerCase();
    filteredRealms = realms.filter(realm => 
      realm.id.toLowerCase().includes(query) || 
      realm.name.toLowerCase().includes(query)
    );
  }

  $: searchQuery, searchRealms();

  // Initialize map when switching to map view
  async function initMap() {
    if (!browser || !mapContainer || map) return;
    
    // Dynamically import Leaflet and h3-js
    L = await import('leaflet');
    h3 = await import('h3-js');
    
    // Create map centered on world view
    map = L.map(mapContainer).setView([20, 0], 2);
    
    // Add CartoDB Positron tiles (minimal grayscale, no labels)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);
    
    // Add scale control (metric only)
    L.control.scale({
      metric: true,
      imperial: false,
      position: 'bottomright',
    }).addTo(map);
    
    // Add zoom event listener to show/hide markers based on zoom level
    map.on('zoomend', () => {
      if (!markerLayer) return;
      const zoom = map.getZoom();
      if (zoom >= MARKER_HIDE_ZOOM && map.hasLayer(markerLayer)) {
        map.removeLayer(markerLayer);
      } else if (zoom < MARKER_HIDE_ZOOM && !map.hasLayer(markerLayer)) {
        markerLayer.addTo(map);
      }
    });
    
    // Add hex zones and markers for realms with coordinates
    addRealmHexZones();
  }

  // Generate a color for a realm based on its index
  function getRealmColor(index) {
    const colors = [
      '#3B82F6', // blue
      '#10B981', // green
      '#F59E0B', // amber
      '#EF4444', // red
      '#8B5CF6', // violet
      '#EC4899', // pink
      '#06B6D4', // cyan
      '#F97316', // orange
    ];
    return colors[index % colors.length];
  }

  // Demo coordinates for realms - each realm can have multiple locations worldwide
  // Some locations overlap to show shared influence zones
  const demoCoordinates = [
    // Realm 1: Global presence - Europe, Americas, Asia (with overlaps in Paris & Tokyo)
    [
      { lat: 48.8566, lng: 2.3522 },    // Paris (HQ)
      { lat: 40.7128, lng: -74.0060 },  // New York
      { lat: 35.6762, lng: 139.6503 },  // Tokyo
      { lat: -33.8688, lng: 151.2093 }, // Sydney
    ],
    // Realm 2: European focus with Paris overlap
    [
      { lat: 48.9, lng: 2.4 },          // Near Paris (overlap with Realm 1)
      { lat: 51.5074, lng: -0.1278 },   // London
      { lat: 52.5200, lng: 13.4050 },   // Berlin
      { lat: 41.9028, lng: 12.4964 },   // Rome
    ],
    // Realm 3: Asian-Pacific with Tokyo overlap
    [
      { lat: 35.7, lng: 139.7 },        // Near Tokyo (overlap with Realm 1)
      { lat: 37.5665, lng: 126.9780 },  // Seoul
      { lat: 22.3193, lng: 114.1694 },  // Hong Kong
      { lat: 1.3521, lng: 103.8198 },   // Singapore
    ],
    // Realm 4: Americas focus
    [
      { lat: 34.0522, lng: -118.2437 }, // Los Angeles
      { lat: 41.8781, lng: -87.6298 },  // Chicago
      { lat: -23.5505, lng: -46.6333 }, // São Paulo
      { lat: 19.4326, lng: -99.1332 },  // Mexico City
    ],
    // Realm 5: Middle East & Africa with European overlap
    [
      { lat: 51.6, lng: -0.2 },         // Near London (overlap with Realm 2)
      { lat: 25.2048, lng: 55.2708 },   // Dubai
      { lat: -33.9249, lng: 18.4241 },  // Cape Town
      { lat: 30.0444, lng: 31.2357 },   // Cairo
    ],
    // Realm 6: South Asia & Oceania
    [
      { lat: 28.6139, lng: 77.2090 },   // New Delhi
      { lat: 13.0827, lng: 80.2707 },   // Chennai
      { lat: -37.8136, lng: 144.9631 }, // Melbourne
      { lat: -41.2865, lng: 174.7762 }, // Wellington
    ],
    // Realm 7: Northern Europe & Russia
    [
      { lat: 59.3293, lng: 18.0686 },   // Stockholm
      { lat: 60.1699, lng: 24.9384 },   // Helsinki
      { lat: 55.7558, lng: 37.6173 },   // Moscow
      { lat: 52.4, lng: 13.5 },         // Near Berlin (overlap with Realm 2)
    ],
    // Realm 8: Southeast Asia with Singapore overlap
    [
      { lat: 1.4, lng: 103.9 },         // Near Singapore (overlap with Realm 3)
      { lat: 13.7563, lng: 100.5018 },  // Bangkok
      { lat: 14.5995, lng: 120.9842 },  // Manila
      { lat: -6.2088, lng: 106.8456 },  // Jakarta
    ],
  ];

  // Add H3 hex zones for realms with multi-realm tracking per hex
  function addRealmHexZones() {
    if (!map || !L || !h3) return;
    
    // Clear existing hex layer
    if (hexLayer) {
      map.removeLayer(hexLayer);
      hexLayer = null;
    }
    
    // Clear existing markers and polygons
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker || layer instanceof L.Polygon) {
        map.removeLayer(layer);
      }
    });
    
    // First pass: collect all hex cells and track which realms influence each
    // hexData[h3Index] = { realms: [{realm, color, users, distance, locationName}], totalUsers }
    const hexData = {};
    
    // Location names for popups
    const locationNames = {
      '48.8566,2.3522': 'Paris', '40.7128,-74.006': 'New York', '35.6762,139.6503': 'Tokyo',
      '-33.8688,151.2093': 'Sydney', '48.9,2.4': 'Paris Area', '51.5074,-0.1278': 'London',
      '52.52,13.405': 'Berlin', '41.9028,12.4964': 'Rome', '35.7,139.7': 'Tokyo Area',
      '37.5665,126.978': 'Seoul', '22.3193,114.1694': 'Hong Kong', '1.3521,103.8198': 'Singapore',
      '34.0522,-118.2437': 'Los Angeles', '41.8781,-87.6298': 'Chicago', '-23.5505,-46.6333': 'São Paulo',
      '19.4326,-99.1332': 'Mexico City', '51.6,-0.2': 'London Area', '25.2048,55.2708': 'Dubai',
      '-33.9249,18.4241': 'Cape Town', '30.0444,31.2357': 'Cairo', '28.6139,77.209': 'New Delhi',
      '13.0827,80.2707': 'Chennai', '-37.8136,144.9631': 'Melbourne', '-41.2865,174.7762': 'Wellington',
      '59.3293,18.0686': 'Stockholm', '60.1699,24.9384': 'Helsinki', '55.7558,37.6173': 'Moscow',
      '52.4,13.5': 'Berlin Area', '1.4,103.9': 'Singapore Area', '13.7563,100.5018': 'Bangkok',
      '14.5995,120.9842': 'Manila', '-6.2088,106.8456': 'Jakarta',
    };
    
    filteredRealms.forEach((realm, index) => {
      const color = getRealmColor(index);
      const baseUsers = realm.users_count || 50; // Default demo users
      
      // Get all locations for this realm (multiple if using demo coordinates)
      const hasCoords = realm.latitude != null && realm.longitude != null;
      const locations = hasCoords 
        ? [{ lat: realm.latitude, lng: realm.longitude }]
        : demoCoordinates[index % demoCoordinates.length] || [];
      
      // Distribute users across all locations
      const usersPerLocation = Math.ceil(baseUsers / locations.length);
      
      locations.forEach((coords, locIndex) => {
        const influenceRings = Math.min(Math.ceil(Math.log2(usersPerLocation + 1)) + 1, 4);
        const isHQ = locIndex === 0; // First location is headquarters
        
        // Get center hex and all influence hexes for this location
        const centerH3 = h3.latLngToCell(coords.lat, coords.lng, H3_RESOLUTION);
        const allHexes = h3.gridDisk(centerH3, influenceRings);
        
        // Get location name
        const locKey = `${coords.lat},${coords.lng}`;
        const locationName = locationNames[locKey] || `Location ${locIndex + 1}`;
        
        // Distribute users across hexes (more in center, less at edges)
        allHexes.forEach(hexIndex => {
          const distance = h3.gridDistance(centerH3, hexIndex);
          
          // Calculate users in this hex (inverse of distance, with randomization)
          const distanceFactor = 1 - (distance / (influenceRings + 1));
          const usersInHex = Math.round(usersPerLocation * distanceFactor * distanceFactor * (0.5 + Math.random() * 0.5) / (influenceRings + 1));
          
          if (!hexData[hexIndex]) {
            hexData[hexIndex] = { realms: [], totalUsers: 0 };
          }
          
          // Check if this realm already has an entry for this hex (from another location)
          const existingEntry = hexData[hexIndex].realms.find(r => r.realm.name === realm.name);
          if (existingEntry) {
            existingEntry.users += usersInHex;
            if (distance === 0 && isHQ) existingEntry.isHQ = true;
            if (!existingEntry.locations.includes(locationName)) {
              existingEntry.locations.push(locationName);
            }
          } else {
            hexData[hexIndex].realms.push({
              realm: realm,
              color: color,
              users: usersInHex,
              distance: distance,
              isCenter: distance === 0,
              isHQ: distance === 0 && isHQ,
              locations: [locationName],
            });
          }
          hexData[hexIndex].totalUsers += usersInHex;
        });
      });
    });
    
    // Second pass: render all hex cells with combined realm info
    Object.entries(hexData).forEach(([hexIndex, data]) => {
      const boundary = h3.cellToBoundary(hexIndex);
      const latLngs = boundary.map(coord => [coord[0], coord[1]]);
      
      // Determine dominant color (realm with most users in this hex)
      const sortedRealms = [...data.realms].sort((a, b) => b.users - a.users);
      const dominantRealm = sortedRealms[0];
      
      // Mix colors if multiple realms (use gradient effect via opacity)
      const hasMultipleRealms = data.realms.length > 1;
      const minDistance = Math.min(...data.realms.map(r => r.distance));
      const isAnyCenter = data.realms.some(r => r.isCenter);
      
      // Calculate opacity based on total users
      const opacity = Math.min(0.15 + (data.totalUsers / 50) * 0.4, 0.7);
      
      // Create hex polygon
      const hexPolygon = L.polygon(latLngs, {
        color: hasMultipleRealms ? '#525252' : dominantRealm.color,
        weight: isAnyCenter ? 2.5 : (minDistance <= 1 ? 1.5 : 1),
        fillColor: dominantRealm.color,
        fillOpacity: opacity,
        dashArray: isAnyCenter ? null : (minDistance > 2 ? '4, 4' : '2, 2'),
      }).addTo(map);
      
      // Create popup showing ALL realms in this hex with location info
      const realmsList = sortedRealms.map(r => `
        <div style="display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #E5E5E5;">
          <div style="width: 12px; height: 12px; border-radius: 3px; background: ${r.color}; flex-shrink: 0;"></div>
          <div style="flex: 1;">
            <strong style="font-size: 13px; color: #171717;">${r.realm.name}</strong>
            <span style="font-size: 11px; color: #737373; margin-left: 6px;">${r.users} users</span>
            ${r.locations && r.locations.length > 0 ? `<div style="font-size: 10px; color: #A3A3A3; margin-top: 2px;">📍 ${r.locations.join(', ')}</div>` : ''}
          </div>
          ${r.isHQ ? '<span style="font-size: 10px; background: #171717; color: white; padding: 2px 6px; border-radius: 4px;">HQ</span>' : (r.isCenter ? '<span style="font-size: 10px; background: #E5E5E5; padding: 2px 6px; border-radius: 4px;">Base</span>' : '')}
        </div>
      `).join('');
      
      const popupContent = `
        <div style="min-width: 220px; font-family: Inter, sans-serif;">
          <div style="background: #F5F5F5; margin: -12px -14px 10px; padding: 10px 14px; border-radius: 12px 12px 0 0;">
            <strong style="font-size: 14px; color: #171717;">
              ${data.totalUsers} users in this zone
            </strong>
            <p style="margin: 4px 0 0; font-size: 11px; color: #737373;">
              ${data.realms.length} realm${data.realms.length > 1 ? 's' : ''} with influence
            </p>
          </div>
          <div style="margin-bottom: 8px;">
            ${realmsList}
          </div>
          <p style="margin: 8px 0 0; font-size: 10px; color: #A3A3A3;">
            H3: <code style="font-size: 9px;">${hexIndex}</code>
          </p>
        </div>
      `;
      
      hexPolygon.bindPopup(popupContent);
    });
    
    // Add circle markers at each realm location center (visible only when zoomed out)
    // Clear existing marker layer
    if (markerLayer) {
      map.removeLayer(markerLayer);
    }
    markerLayer = L.layerGroup();
    
    filteredRealms.forEach((realm, index) => {
      const color = getRealmColor(index);
      const hasCoords = realm.latitude != null && realm.longitude != null;
      const locations = hasCoords 
        ? [{ lat: realm.latitude, lng: realm.longitude }]
        : demoCoordinates[index % demoCoordinates.length] || [];
      
      locations.forEach((coords, locIndex) => {
        // Add an outer glow effect
        L.circleMarker([coords.lat, coords.lng], {
          radius: 28,
          fillColor: color,
          color: color,
          weight: 0,
          fillOpacity: 0.3,
        }).addTo(markerLayer);
        
        // Create a large, highly visible circle marker
        const circleMarker = L.circleMarker([coords.lat, coords.lng], {
          radius: 20,
          fillColor: color,
          color: '#FFFFFF',
          weight: 4,
          opacity: 1,
          fillOpacity: 0.85,
        }).addTo(markerLayer);
        
        // Add realm name tooltip
        const isHQ = locIndex === 0;
        circleMarker.bindTooltip(`${realm.name}${isHQ ? ' (HQ)' : ''}`, {
          permanent: false,
          direction: 'top',
          className: 'realm-tooltip',
        });
      });
    });
    
    // Show/hide markers based on current zoom level
    const currentZoom = map.getZoom();
    if (currentZoom < MARKER_HIDE_ZOOM) {
      markerLayer.addTo(map);
    }
    
    // Fit map to show all hex zones (world view since realms are scattered globally)
    if (filteredRealms.length > 0) {
      const allCoords = [];
      filteredRealms.forEach((realm, index) => {
        const hasCoords = realm.latitude != null && realm.longitude != null;
        if (hasCoords) {
          allCoords.push([realm.latitude, realm.longitude]);
        } else {
          // Add all demo locations for this realm
          const locations = demoCoordinates[index % demoCoordinates.length] || [];
          locations.forEach(loc => allCoords.push([loc.lat, loc.lng]));
        }
      });
      if (allCoords.length > 0) {
        const bounds = L.latLngBounds(allCoords);
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 3 });
      }
    }
  }

  // Update hex zones when filtered realms change
  $: if (viewMode === 'map' && map && filteredRealms && h3) {
    addRealmHexZones();
  }

  // Initialize map when view mode changes to map
  $: if (viewMode === 'map' && mapContainer && !map) {
    initMap();
  }

  // Cleanup on destroy
  onDestroy(() => {
    if (map) {
      map.remove();
      map = null;
    }
  });
</script>

<svelte:head>
  <title>Realm Registry</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
</svelte:head>

<div class="container">
  <header class="header">
    <div class="header-content">
      <img src="/images/logo_horizontal.svg" alt="Realms Logo" class="header-logo" />
    </div>
  </header>

  <div class="controls">
    <div class="search-section">
      <div class="search-wrapper">
        <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.35-4.35"></path>
        </svg>
        <input
          type="text"
          placeholder="Search realms by name or ID..."
          bind:value={searchQuery}
          class="search-input"
        />
        {#if searchQuery}
          <button class="search-clear" on:click={() => searchQuery = ''} aria-label="Clear search">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"></path>
            </svg>
          </button>
        {/if}
      </div>
    </div>
    
    <div class="view-toggle">
      <button 
        class="toggle-btn" 
        class:active={viewMode === 'list'}
        on:click={() => viewMode = 'list'}
        aria-label="List view"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7"></rect>
          <rect x="14" y="3" width="7" height="7"></rect>
          <rect x="14" y="14" width="7" height="7"></rect>
          <rect x="3" y="14" width="7" height="7"></rect>
        </svg>
      </button>
      <button 
        class="toggle-btn"
        class:active={viewMode === 'map'}
        on:click={() => viewMode = 'map'}
        aria-label="Map view"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
          <line x1="8" y1="2" x2="8" y2="18"></line>
          <line x1="16" y1="6" x2="16" y2="22"></line>
        </svg>
      </button>
    </div>
    
    <button 
      class="btn btn-primary add-btn"
      on:click={() => showCreateModal = true}
    >
      Create Realm
    </button>
  </div>

  {#if showCreateModal}
    <div class="modal-overlay" on:click={() => showCreateModal = false}>
      <div class="modal-content" on:click|stopPropagation>
        <button class="modal-close" on:click={() => showCreateModal = false}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"></path>
          </svg>
        </button>
        
        <h2 class="modal-title">Create a Realm</h2>
        <p class="modal-subtitle">Deploy your own governance system in minutes</p>
        
        <div class="instruction-step">
          <div class="step-number">1</div>
          <div class="step-content">
            <h3>Install the CLI</h3>
            <div class="code-block">
              <code>pip install realms-gos</code>
              <button class="copy-btn" on:click={() => copyToClipboard('pip install realms-gos')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
        
        <div class="instruction-step">
          <div class="step-number">2</div>
          <div class="step-content">
            <h3>Create and Deploy</h3>
            <div class="code-block">
              <code>realms realm create --deploy --network staging</code>
              <button class="copy-btn" on:click={() => copyToClipboard('realms realm create --deploy --network staging')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer" class="docs-link">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            View Documentation
          </a>
        </div>
      </div>
    </div>
  {/if}

  {#if error}
    <div class="error-banner">
      <span>❌ {error}</span>
      <button on:click={() => error = null}>✕</button>
    </div>
  {/if}

  <main class="main-content">
    {#if loading}
      <div class="loading-grid">
        {#each [1, 2, 3] as _}
          <div class="skeleton-card">
            <div class="skeleton-icon"></div>
            <div class="skeleton-title"></div>
            <div class="skeleton-text"></div>
            <div class="skeleton-text short"></div>
            <div class="skeleton-buttons">
              <div class="skeleton-btn"></div>
              <div class="skeleton-btn"></div>
            </div>
          </div>
        {/each}
      </div>
    {:else if filteredRealms.length === 0}
      <div class="empty-state">
        {#if searchQuery}
          <h2>🔍 No Results</h2>
          <p>No realms found matching "{searchQuery}"</p>
        {:else}
          <h2>📋 No Realms</h2>
          <p>No realms have been registered yet.</p>
          <button 
            class="btn btn-primary"
            on:click={() => showCreateModal = true}
          >
            Create Realm
          </button>
        {/if}
      </div>
    {:else}
      {#if viewMode === 'list'}
        <div class="realms-grid">
          {#each filteredRealms as realm}
            <div class="realm-card">
              {#if realm.url}
                <div 
                  class="realm-card-bg" 
                  style="background-image: url('{ensureProtocol(realm.url)}/images/default_welcome.jpg')"
                ></div>
              {/if}
              <div class="card-accent"></div>
              <div class="realm-header">
                <div class="realm-logo-container">
                  {#if realm.logo}
                    <img src={realm.logo} alt="{realm.name} logo" class="realm-logo" />
                  {:else}
                    <div class="realm-logo-fallback">
                      <span>{realm.name.charAt(0).toUpperCase()}</span>
                    </div>
                  {/if}
                </div>
                <div class="user-badge" class:has-users={realm.users_count > 0}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                  </svg>
                  <span>{realm.users_count || 0}</span>
                </div>
              </div>
              
              <div class="realm-content">
                <h3 class="realm-name">{realm.name}</h3>
                
                <p class="realm-info" title="{formatFullDate(realm.created_at)}">
                  <code>{realm.id}</code>
                  <span class="info-separator">·</span>
                  <span>{formatTimeAgo(realm.created_at)}</span>
                </p>
              </div>
              
              <div class="realm-actions">
                {#if realm.url}
                  <button 
                    class="btn btn-dark btn-sm btn-full"
                    on:click={() => window.open(ensureProtocol(realm.url) + '/welcome', '_blank')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                      <polyline points="15 3 21 3 21 9"></polyline>
                      <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                    Visit
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="map-view">
          <div class="map-container" bind:this={mapContainer}></div>
          <button class="map-back-btn" on:click={() => viewMode = 'list'} title="Back to list view">
            ← Back to List
          </button>
          <div class="map-info">
            <span>Showing {filteredRealms.length} realms</span>
          </div>
        </div>
      {/if}
      
      <div class="stats">
        <p>Showing {filteredRealms.length} of {realms.length} realms</p>
      </div>
    {/if}
  </main>
  
  <!-- Footer -->
  <footer class="footer">
    <!-- Built on Internet Computer section -->
    <div class="footer-ic">
      <a href="https://internetcomputer.org" target="_blank" rel="noopener noreferrer" class="ic-link">
        <img src="/images/internet-computer-icp-logo.svg" alt="Internet Computer Logo" width="24" height="24" class="ic-logo" />
        <span>Built on the Internet Computer</span>
      </a>
    </div>
    
    <!-- GitHub link -->
    <div class="footer-links">
      <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer" class="github-link">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
      </a>
    </div>
    
    <!-- Version info with dynamic data -->
    <div class="footer-version">
      <span>
        Realm Registry {version} ({commitHash}) - {commitDatetime}{typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname.endsWith('.localhost')) ? ' - Local deployment' : ''}
      </span>
    </div>
  </footer>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
    background: #FAFAFA;
    min-height: 100vh;
    color: #171717;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .header {
    text-align: center;
    margin-bottom: 2rem;
    color: #171717;
  }

  .logo {
    height: 3rem;
    margin-bottom: 1rem;
  }

  .header-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
  }

  .header-logo {
    height: 120px;
    width: auto;
  }

  .header h1 {
    font-size: 2.5rem;
    margin: 0;
    font-weight: 700;
    color: #171717;
  }

  .subtitle {
    font-size: 1.2rem;
    margin: 1rem 0 0 0;
    color: #525252;
    font-weight: 400;
  }

  .controls {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .search-section {
    flex: 1;
    min-width: 300px;
  }

  .search-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 1rem;
    color: #A3A3A3;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    padding: 1rem 2.5rem 1rem 3rem;
    font-size: 1rem;
    border: 1px solid #E5E5E5;
    border-radius: 0.75rem;
    background: #FFFFFF;
    color: #171717;
    font-family: inherit;
    transition: all 0.2s ease;
  }

  .search-input:focus {
    outline: none;
    border-color: #525252;
    box-shadow: 0 0 0 3px rgba(82, 82, 82, 0.1);
  }

  .search-input:focus + .search-icon,
  .search-wrapper:focus-within .search-icon {
    color: #525252;
  }

  .search-clear {
    position: absolute;
    right: 0.75rem;
    background: none;
    border: none;
    padding: 0.25rem;
    cursor: pointer;
    color: #A3A3A3;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .search-clear:hover {
    color: #525252;
    background: #F5F5F5;
  }

  .add-btn {
    white-space: nowrap;
  }

  .view-toggle {
    display: flex;
    background: #F5F5F5;
    border-radius: 0.5rem;
    padding: 0.25rem;
    gap: 0.25rem;
  }

  .toggle-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 0.75rem;
    border: none;
    background: transparent;
    color: #737373;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .toggle-btn:hover {
    color: #525252;
    background: rgba(255, 255, 255, 0.5);
  }

  .toggle-btn.active {
    background: #FFFFFF;
    color: #171717;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  }

  .map-view {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 100;
  }

  .map-container {
    width: 100%;
    height: 100%;
    border-radius: 0;
    overflow: hidden;
    z-index: 1;
  }

  .map-back-btn {
    position: absolute;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    padding: 12px 20px;
    background: #FFFFFF;
    color: #171717;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    transition: all 0.2s;
  }

  .map-back-btn:hover {
    background: #F5F5F5;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  }

  .map-info {
    position: absolute;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1000;
    padding: 10px 20px;
    background: rgba(255, 255, 255, 0.95);
    color: #525252;
    border-radius: 20px;
    font-size: 13px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  :global(.leaflet-popup-content-wrapper) {
    border-radius: 0.75rem !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
  }

  :global(.leaflet-popup-content) {
    margin: 12px 14px !important;
  }

  :global(.realm-tooltip) {
    background: rgba(23, 23, 23, 0.9) !important;
    border: none !important;
    border-radius: 6px !important;
    color: white !important;
    font-family: Inter, sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 6px 10px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
  }

  :global(.realm-tooltip::before) {
    border-top-color: rgba(23, 23, 23, 0.9) !important;
  }

  .add-form {
    background: #FFFFFF;
    padding: 2rem;
    border-radius: 0.75rem;
    margin-bottom: 2rem;
    border: 1px solid #E5E5E5;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .add-form h3 {
    margin: 0 0 1rem 0;
    color: #171717;
    font-weight: 600;
  }

  .form-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .form-input {
    flex: 1;
    min-width: 200px;
    padding: 0.75rem;
    border: 1px solid #E5E5E5;
    border-radius: 0.375rem;
    font-size: 1rem;
    background: #FFFFFF;
    color: #171717;
    font-family: inherit;
  }

  .form-input:focus {
    outline: none;
    border-color: #525252;
    box-shadow: 0 0 0 3px rgba(82, 82, 82, 0.1);
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
  }

  .error-banner {
    background: #FAFAFA;
    color: #737373;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid #D4D4D4;
  }

  .error-banner button {
    background: none;
    border: none;
    color: #737373;
    cursor: pointer;
    font-size: 1.2rem;
  }

  .main-content {
    flex: 1;
    background: #FFFFFF;
    border-radius: 0.75rem;
    padding: 2rem;
    border: 1px solid #E5E5E5;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .loading, .empty-state {
    text-align: center;
    padding: 3rem;
  }

  .loading-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
  }

  .skeleton-card {
    background: #FFFFFF;
    border-radius: 1rem;
    padding: 1.5rem;
    border: 1px solid #E5E5E5;
  }

  .skeleton-icon {
    width: 72px;
    height: 72px;
    border-radius: 1rem;
    background: linear-gradient(90deg, #F5F5F5 25%, #E5E5E5 50%, #F5F5F5 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    margin: 0 auto 1rem;
  }

  .skeleton-title {
    height: 24px;
    width: 60%;
    border-radius: 6px;
    background: linear-gradient(90deg, #F5F5F5 25%, #E5E5E5 50%, #F5F5F5 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    margin: 0 auto 0.75rem;
  }

  .skeleton-text {
    height: 16px;
    width: 80%;
    border-radius: 4px;
    background: linear-gradient(90deg, #F5F5F5 25%, #E5E5E5 50%, #F5F5F5 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    margin: 0 auto 0.5rem;
  }

  .skeleton-text.short {
    width: 50%;
  }

  .skeleton-buttons {
    display: flex;
    gap: 0.75rem;
    justify-content: center;
    margin-top: 1.5rem;
  }

  .skeleton-btn {
    height: 36px;
    width: 100px;
    border-radius: 6px;
    background: linear-gradient(90deg, #F5F5F5 25%, #E5E5E5 50%, #F5F5F5 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #F5F5F5;
    border-top: 4px solid #525252;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .realms-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .realm-card {
    background: #FFFFFF;
    border-radius: 1rem;
    padding: 0;
    border: 1px solid #E5E5E5;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.08);
    position: relative;
    overflow: hidden;
    transition: all 0.2s ease;
  }

  .realm-card-bg {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-size: cover;
    background-position: center;
    opacity: 0.2;
    z-index: 0;
    pointer-events: none;
  }

  .realm-card:hover {
    border-color: #D4D4D4;
    box-shadow: 0 8px 25px -5px rgba(0, 0, 0, 0.1), 0 4px 10px -5px rgba(0, 0, 0, 0.04);
    transform: translateY(-2px);
  }

  .card-accent {
    height: 4px;
    background: linear-gradient(90deg, #404040 0%, #737373 100%);
    position: relative;
    z-index: 1;
  }

  .realm-header {
    padding: 1.5rem 1.5rem 0;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    position: relative;
    z-index: 1;
  }

  .realm-logo-container {
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .realm-logo {
    width: 72px;
    height: 72px;
    object-fit: contain;
    border-radius: 1rem;
    background: #F5F5F5;
    padding: 0.5rem;
  }

  .realm-logo-fallback {
    width: 72px;
    height: 72px;
    border-radius: 1rem;
    background: linear-gradient(135deg, #525252 0%, #737373 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
    font-size: 1.75rem;
    font-weight: 600;
  }

  .user-badge {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.75rem;
    border-radius: 2rem;
    background: #F5F5F5;
    color: #737373;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .user-badge.has-users {
    background: #DCFCE7;
    color: #166534;
  }

  .user-badge svg {
    opacity: 0.8;
  }

  .realm-content {
    padding: 1rem 1.5rem;
    text-align: center;
    position: relative;
    z-index: 1;
  }

  .realm-name {
    margin: 0 0 0.5rem;
    color: #171717;
    font-size: 1.35rem;
    font-weight: 600;
  }

  .realm-info {
    margin: 0;
    font-size: 0.8rem;
    color: #737373;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .realm-info code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.75rem;
    color: #525252;
  }

  .info-separator {
    color: #A3A3A3;
  }

  .realm-id {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #F5F5F5;
    padding: 0.35rem 0.75rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
  }

  .realm-id code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.75rem;
    color: #737373;
  }

  .copy-id-btn {
    background: none;
    border: none;
    padding: 0.2rem;
    cursor: pointer;
    color: #A3A3A3;
    border-radius: 4px;
    display: flex;
    align-items: center;
    transition: all 0.15s ease;
  }

  .copy-id-btn:hover {
    color: #525252;
    background: #E5E5E5;
  }

  .realm-meta {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    text-align: left;
  }

  .realm-meta p {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #525252;
  }

  .meta-label {
    font-weight: 500;
    color: #737373;
    font-size: 0.8rem;
  }

  .realm-meta svg {
    color: #A3A3A3;
    flex-shrink: 0;
  }

  .realm-meta code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.8rem;
    color: #525252;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .health-indicator {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    background: rgba(255,255,255,0.8);
    border: 1px solid #e1e5e9;
  }

  .health-icon {
    font-size: 0.9rem;
  }

  .health-label {
    font-weight: 500;
    color: #495057;
  }

  .realm-id {
    background: #e9ecef;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.875rem;
    color: #6c757d;
  }

  .realm-details {
    margin-bottom: 1.5rem;
  }

  .realm-details p {
    margin: 0.5rem 0;
    font-size: 0.9rem;
  }

  .realm-url code {
    background: #f8f9fa;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
  }

  .realm-actions {
    display: flex;
    gap: 0.75rem;
    padding: 1rem 1.5rem 1.5rem;
    border-top: 1px solid #F5F5F5;
    position: relative;
    z-index: 1;
  }

  .btn {
    padding: 0.65rem 1.25rem;
    border: 1px solid transparent;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s ease-in-out;
    font-weight: 500;
    font-family: inherit;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .btn-sm {
    padding: 0.5rem 1rem;
    font-size: 0.8rem;
    flex: 1;
  }

  .btn-primary {
    background: #171717;
    color: #FFFFFF;
    border-color: #171717;
  }

  .btn-primary:hover {
    background: #262626;
    border-color: #262626;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .btn-accent {
    background: #2563EB;
    color: #FFFFFF;
    border-color: #2563EB;
  }

  .btn-accent:hover {
    background: #1D4ED8;
    border-color: #1D4ED8;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.25), 0 2px 4px -1px rgba(37, 99, 235, 0.15);
  }

  .btn-dark {
    background: #171717;
    color: #FFFFFF;
    border-color: #171717;
  }

  .btn-dark:hover {
    background: #404040;
    border-color: #404040;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1);
  }

  .btn-full {
    width: 100%;
    justify-content: center;
  }

  .btn-ghost {
    background: transparent;
    color: #525252;
    border-color: #E5E5E5;
  }

  .btn-ghost:hover {
    background: #F5F5F5;
    border-color: #D4D4D4;
    color: #171717;
  }

  .btn-secondary {
    background: #FFFFFF;
    color: #171717;
    border-color: #E5E5E5;
  }

  .btn-secondary:hover {
    background: #F5F5F5;
    border-color: #D4D4D4;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .btn-danger {
    background: #DC2626;
    color: #FFFFFF;
    border-color: #DC2626;
  }

  .btn-danger:hover {
    background: #B91C1C;
    border-color: #B91C1C;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.12), 0 2px 4px -1px rgba(220, 38, 38, 0.08);
  }

  .drawer-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1000;
    display: flex;
    justify-content: flex-end;
    animation: fadeIn 0.3s ease-out;
  }

  .drawer {
    width: 500px;
    height: 100%;
    background: #FFFFFF;
    border-left: 1px solid #E5E5E5;
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
    transform: translateX(100%);
    transition: transform 0.3s ease;
    overflow-y: auto;
  }


  .drawer-header {
    padding: 2rem;
    border-bottom: 1px solid #E5E5E5;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .drawer-header h2 {
    margin: 0;
    color: #171717;
    font-weight: 600;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #6c757d;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .close-btn:hover {
    background: rgba(0,0,0,0.1);
  }

  .drawer-content {
    padding: 2rem;
  }

  .drawer-content label {
    font-weight: 600;
    color: #171717;
    display: block;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
  }

  .drawer-content p {
    margin: 0 0 1.5rem 0;
    color: #525252;
    word-break: break-all;
    font-size: 0.875rem;
  }

  .status-section, .sharing-section, .actions-section {
    margin-bottom: 2rem;
  }

  .status-section h3, .sharing-section h3 {
    margin: 0 0 1rem 0;
    color: #2c3e50;
    font-size: 1.1rem;
  }

  .status-card, .sharing-card {
    background: #f8f9fa;
    border: 1px solid #e1e5e9;
    border-radius: 8px;
    padding: 1rem;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: white;
    border-radius: 6px;
    border: 1px solid #dee2e6;
  }

  .status-icon {
    font-size: 1.2rem;
  }

  .status-text {
    font-weight: 600;
    color: #495057;
  }

  .status-details p {
    margin: 0.5rem 0;
    font-size: 0.9rem;
    color: #6c757d;
  }

  .public-link {
    margin-bottom: 1.5rem;
  }

  .public-link label, .qr-code label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: #495057;
    font-size: 0.9rem;
  }

  .link-input {
    display: flex;
    gap: 0.5rem;
  }

  .link-field {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 0.85rem;
    font-family: monospace;
    background: white;
  }

  .qr-container {
    text-align: center;
    padding: 1rem;
    background: white;
    border-radius: 6px;
    border: 1px solid #dee2e6;
  }

  .qr-image {
    max-width: 150px;
    height: auto;
    border-radius: 4px;
  }

  .actions-section {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }

  .stats {
    text-align: center;
    color: #6c757d;
    font-size: 0.9rem;
    padding-top: 1rem;
    border-top: 1px solid #e1e5e9;
  }

  /* Footer Styles */
  .footer {
    margin-top: 3rem;
    padding: 1.5rem;
    border-top: 1px solid #E5E5E5;
    background: #FFFFFF;
    border-radius: 0.75rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .footer-ic {
    display: flex;
    justify-content: center;
    margin-bottom: 0.75rem;
  }

  .ic-link {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #737373;
    text-decoration: none;
    transition: color 0.15s ease-in-out;
    font-size: 0.875rem;
  }

  .ic-link:hover {
    color: #171717;
  }

  .ic-logo {
    width: 24px;
    height: 24px;
  }

  .footer-links {
    display: flex;
    justify-content: center;
    margin-top: 1rem;
  }

  .github-link {
    color: #737373;
    transition: all 0.15s ease-in-out;
    padding: 0.5rem;
    border-radius: 6px;
    text-decoration: none;
  }

  .github-link:hover {
    color: #171717;
    background: rgba(0,0,0,0.05);
  }

  .footer-version {
    text-align: center;
    margin-top: 0.75rem;
  }

  .footer-version span {
    font-size: 0.75rem;
    color: #A3A3A3;
  }

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
    }

    .header {
      margin-bottom: 1rem;
    }

    .header h1 {
      font-size: 2rem;
    }

    .header-content {
      flex-direction: column;
    }

    .header-logo {
      height: 50px;
    }

    .controls {
      flex-direction: column;
      align-items: stretch;
      margin-bottom: 1rem;
    }

    .main-content {
      padding: 1rem;
    }

    .form-row {
      flex-direction: column;
    }

    .realms-grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .realm-header {
      padding: 1rem 1rem 0;
    }

    .realm-logo, .realm-logo-fallback {
      width: 56px;
      height: 56px;
    }

    .realm-content {
      padding: 0.75rem 1rem;
    }

    .realm-name {
      font-size: 1.1rem;
    }

    .realm-actions {
      padding: 0.75rem 1rem 1rem;
    }

    .card-accent {
      height: 3px;
    }
  }

  /* Modal Styles */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    animation: fadeIn 0.2s ease-out;
  }

  .modal-content {
    background: #FFFFFF;
    border-radius: 1rem;
    padding: 2rem;
    max-width: 520px;
    width: 100%;
    position: relative;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .modal-close {
    position: absolute;
    top: 1rem;
    right: 1rem;
    background: none;
    border: none;
    cursor: pointer;
    color: #A3A3A3;
    padding: 0.5rem;
    border-radius: 0.5rem;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .modal-close:hover {
    background: #F5F5F5;
    color: #525252;
  }

  .modal-title {
    margin: 0 0 0.5rem 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #171717;
  }

  .modal-subtitle {
    margin: 0 0 2rem 0;
    color: #737373;
    font-size: 0.95rem;
  }

  .instruction-step {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .step-number {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    background: #171717;
    color: #FFFFFF;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.875rem;
  }

  .step-content {
    flex: 1;
  }

  .step-content h3 {
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #171717;
  }

  .code-block {
    background: #1E1E1E;
    border-radius: 0.5rem;
    padding: 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .code-block code {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 0.875rem;
    color: #E5E5E5;
    white-space: nowrap;
    overflow-x: auto;
  }

  .copy-btn {
    flex-shrink: 0;
    background: transparent;
    border: none;
    cursor: pointer;
    color: #737373;
    padding: 0.375rem;
    border-radius: 0.375rem;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .copy-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #FFFFFF;
  }

  .modal-footer {
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid #E5E5E5;
    display: flex;
    justify-content: center;
  }

  .docs-link {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: #525252;
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    transition: all 0.15s ease;
  }

  .docs-link:hover {
    background: #F5F5F5;
    color: #171717;
  }

  @media (max-width: 768px) {
    .modal-content {
      padding: 1.5rem;
      max-width: 100%;
    }

    .modal-title {
      font-size: 1.25rem;
    }

    .code-block {
      padding: 0.75rem;
    }

    .code-block code {
      font-size: 0.75rem;
    }
  }
</style>
