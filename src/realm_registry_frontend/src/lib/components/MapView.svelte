<script>
  /**
   * MapLibre 3D globe — vector tiles (sharp zoom) + no political borders + zoom-adaptive H3.
   * Uses MapLibre's globe projection so the planet stays a sphere, not a flat map.
   */
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { _ } from 'svelte-i18n';
  import { buildHexPolygons, buildPointMarkers } from '$lib/globe/hex-data.js';
  import {
    FLY_TO_MS,
    h3ResolutionForZoom,
    influenceRingsForResolution,
    MAP_BG,
    stripPoliticalLayers,
  } from '$lib/globe/globe-config.js';

  export let realms = [];
  export let realmZoneData = {};
  export let searchQuery = '';
  export let loading = false;

  const dispatch = createEventDispatcher();
  const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';
  const HEX_SOURCE = 'realm-hexes';
  const HEX_FILL = 'realm-hex-fill';
  const HEX_LINE = 'realm-hex-line';
  const MARKER_SOURCE = 'realm-markers';
  const MARKER_LAYER = 'realm-markers-circle';
  const MARKER_HALO = 'realm-markers-halo';

  let container;
  /** @type {import('maplibre-gl').Map | null} */
  let map = null;
  /** @type {typeof import('maplibre-gl') | null} */
  let maplibregl = null;
  /** @type {import('h3-js') | null} */
  let h3 = null;
  let ready = false;
  let currentH3Res = -1;
  let mapError = '';
  let reducedMotion = false;
  let autoRotate = true;
  let resumeTimer = null;
  let rotateRaf = null;
  const AUTO_ROTATE_DEG_PER_FRAME = 0.012;
  const AUTO_ROTATE_RESUME_MS = 5000;
  /** Below this zoom the view is globe-like; above it MapLibre flattens toward mercator. */
  const GLOBE_VIEW_MAX_ZOOM = 5.5;

  // Realms prop is already filtered by search; never dim the globe while typing.
  $: matchingRealmIds = null;
  $: dimNonMatching = false;

  function emptyFeatureCollection() {
    return { type: 'FeatureCollection', features: [] };
  }

  function polygonsToGeoJSON(polygons) {
    return {
      type: 'FeatureCollection',
      features: polygons.map((p) => ({
        type: 'Feature',
        id: p.hexIndex,
        properties: {
          fill: p.fillColor,
          stroke: p.strokeColor,
          opacity: p.opacity,
          weight: p.weight,
          realmId: p.realmIds?.[0] || '',
          hexIndex: p.hexIndex,
        },
        geometry: p.geometry,
      })),
    };
  }

  function markersToGeoJSON(points) {
    return {
      type: 'FeatureCollection',
      features: points.map((p) => ({
        type: 'Feature',
        properties: {
          realmId: p.realmId,
          name: p.realmName,
          color: p.color,
          users: p.users,
        },
        geometry: {
          type: 'Point',
          coordinates: [p.lng, p.lat],
        },
      })),
    };
  }

  function ensureLayers() {
    if (!map || map.getSource(HEX_SOURCE)) return;

    map.addSource(HEX_SOURCE, { type: 'geojson', data: emptyFeatureCollection() });
    map.addSource(MARKER_SOURCE, { type: 'geojson', data: emptyFeatureCollection() });

    map.addLayer({
      id: HEX_FILL,
      type: 'fill',
      source: HEX_SOURCE,
      paint: {
        'fill-color': ['get', 'fill'],
        'fill-opacity': ['get', 'opacity'],
      },
    });

    map.addLayer({
      id: HEX_LINE,
      type: 'line',
      source: HEX_SOURCE,
      paint: {
        'line-color': ['get', 'stroke'],
        'line-width': ['get', 'weight'],
        'line-opacity': 0.85,
      },
    });

    map.addLayer({
      id: MARKER_HALO,
      type: 'circle',
      source: MARKER_SOURCE,
      paint: {
        'circle-radius': [
          'interpolate',
          ['linear'],
          ['zoom'],
          2,
          10,
          8,
          8,
          12,
          6,
        ],
        'circle-color': '#F59E0B',
        'circle-opacity': 0.18,
      },
    });

    map.addLayer({
      id: MARKER_LAYER,
      type: 'circle',
      source: MARKER_SOURCE,
      paint: {
        'circle-radius': [
          'interpolate',
          ['linear'],
          ['zoom'],
          2,
          5,
          8,
          4.5,
          12,
          3.5,
        ],
        'circle-color': ['get', 'color'],
        'circle-stroke-width': 2,
        'circle-stroke-color': '#FFFFFF',
      },
    });
  }

  function updateLayers() {
    if (!ready || !map || !h3) return;

    const zoom = map.getZoom();
    currentH3Res = h3ResolutionForZoom(zoom);
    const influenceRings = influenceRingsForResolution(currentH3Res);

    const polygons = buildHexPolygons(realms, realmZoneData, h3, {
      matchingRealmIds,
      dimNonMatching,
      h3Resolution: currentH3Res,
      influenceRings,
    });

    const points = buildPointMarkers(realms, realmZoneData, {
      matchingRealmIds,
      dimNonMatching,
    });

    const hexSource = map.getSource(HEX_SOURCE);
    const markerSource = map.getSource(MARKER_SOURCE);
    if (hexSource) hexSource.setData(polygonsToGeoJSON(polygons));
    if (markerSource) markerSource.setData(markersToGeoJSON(points));
  }

  function onZoomEnd() {
    if (!map) return;
    const next = h3ResolutionForZoom(map.getZoom());
    if (next !== currentH3Res) updateLayers();
  }

  function onMapClick(e) {
    if (!map) return;
    const layers = [MARKER_LAYER, HEX_FILL].filter((id) => map.getLayer(id));
    if (!layers.length) return;
    const hits = map.queryRenderedFeatures(e.point, { layers });
    const hit = hits.find((f) => f.properties?.realmId);
    if (hit?.properties?.realmId) {
      dispatch('select', { realmId: hit.properties.realmId });
    }
  }

  function pauseAutoRotate() {
    autoRotate = false;
    if (resumeTimer) clearTimeout(resumeTimer);
    resumeTimer = setTimeout(() => {
      if (!reducedMotion && map && map.getZoom() <= GLOBE_VIEW_MAX_ZOOM) {
        autoRotate = true;
      }
    }, AUTO_ROTATE_RESUME_MS);
  }

  function tickRotate() {
    rotateRaf = requestAnimationFrame(tickRotate);
    if (!map || !autoRotate || reducedMotion) return;
    if (map.getZoom() > GLOBE_VIEW_MAX_ZOOM) return;
    const center = map.getCenter();
    map.setCenter([center.lng + AUTO_ROTATE_DEG_PER_FRAME, center.lat]);
  }

  function applyGlobeLook() {
    if (!map) return;
    map.setProjection({ type: 'globe' });
    // Soft atmosphere that fades as you zoom into regional detail
    try {
      map.setSky?.({
        'atmosphere-blend': [
          'interpolate',
          ['linear'],
          ['zoom'],
          0,
          0.55,
          4,
          0.2,
          6,
          0,
        ],
      });
    } catch {
      // Older builds without sky support
    }
    // Flat, even lighting — no day/night terminator
    try {
      map.setLight?.({
        anchor: 'viewport',
        position: [1.15, 210, 30],
        intensity: 0,
        color: '#ffffff',
      });
    } catch {
      // ignore
    }
  }

  export function flyTo(lat, lng, zoom = 11) {
    if (!map) return;
    pauseAutoRotate();
    map.flyTo({
      center: [lng, lat],
      zoom,
      duration: FLY_TO_MS,
      essential: true,
    });
  }

  export function flyToRealm(realm) {
    const zones = realmZoneData[realm.id]?.zones;
    if (!zones?.length) return;
    const primary = [...zones].sort((a, b) => b.user_count - a.user_count)[0];
    // Zoom in far enough that fine H3 (res 6–7) becomes visible
    flyTo(primary.center_lat, primary.center_lng, 11);
  }

  $: if (ready && (realms, realmZoneData, searchQuery)) {
    updateLayers();
  }

  onMount(async () => {
    if (!browser || !container) return;

    reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    try {
      maplibregl = await import('maplibre-gl');
      await import('maplibre-gl/dist/maplibre-gl.css');
      h3 = await import('h3-js');

      const styleRes = await fetch(STYLE_URL);
      if (!styleRes.ok) throw new Error(`Basemap style HTTP ${styleRes.status}`);
      const style = stripPoliticalLayers(await styleRes.json());
      style.projection = { type: 'globe' };
      style.sky = {
        'atmosphere-blend': [
          'interpolate',
          ['linear'],
          ['zoom'],
          0,
          0.55,
          4,
          0.2,
          6,
          0,
        ],
      };
      // Even lighting (no terminator); intensity 0 disables directional shade
      style.light = {
        anchor: 'viewport',
        position: [1.15, 210, 30],
        intensity: 0,
        color: '#ffffff',
      };

      const desktop = window.matchMedia('(min-width: 768px)').matches;
      // Higher zoom ⇒ larger planet on screen under globe projection.
      const initialZoom = desktop ? 2.65 : 2.05;

      map = new maplibregl.Map({
        container,
        style,
        center: [10, 18],
        zoom: initialZoom,
        minZoom: desktop ? 1.6 : 1.1,
        maxZoom: 16,
        attributionControl: { compact: true },
        pitchWithRotate: false,
        dragRotate: false,
        canvasContextAttributes: { antialias: true },
      });

      map.addControl(
        new maplibregl.ScaleControl({ maxWidth: 120, unit: 'metric' }),
        'bottom-right'
      );

      map.getCanvas().style.cursor = 'grab';

      map.on('style.load', () => {
        applyGlobeLook();
      });

      map.on('load', () => {
        applyGlobeLook();
        ensureLayers();
        ready = true;
        updateLayers();
        if (!reducedMotion) {
          autoRotate = true;
          tickRotate();
        }
      });

      map.on('zoomend', onZoomEnd);
      map.on('moveend', () => {
        onZoomEnd();
      });
      map.on('mousedown', pauseAutoRotate);
      map.on('touchstart', pauseAutoRotate);
      map.on('wheel', pauseAutoRotate);
      map.on('click', onMapClick);
      map.on('mouseenter', MARKER_LAYER, () => {
        if (map) map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', MARKER_LAYER, () => {
        if (map) map.getCanvas().style.cursor = 'grab';
      });
      map.on('mouseenter', HEX_FILL, () => {
        if (map) map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', HEX_FILL, () => {
        if (map) map.getCanvas().style.cursor = 'grab';
      });
    } catch (err) {
      console.error('Map init failed', err);
      mapError = err?.message || 'Failed to load map';
    }

    return () => {
      if (resumeTimer) clearTimeout(resumeTimer);
      if (rotateRaf) cancelAnimationFrame(rotateRaf);
      map?.remove();
      map = null;
    };
  });

  onDestroy(() => {
    if (resumeTimer) clearTimeout(resumeTimer);
    if (rotateRaf) cancelAnimationFrame(rotateRaf);
    map?.remove();
    map = null;
  });
</script>

<div
  class="map-view"
  style="background: {MAP_BG}"
  aria-label={$_('globe.aria_label')}
  bind:this={container}
>
  {#if loading}
    <div class="map-loading">
      <div class="spinner"></div>
      <span>{$_('globe.loading')}</span>
    </div>
  {/if}
  {#if mapError}
    <div class="map-error">{mapError}</div>
  {/if}
</div>

<style>
  .map-view {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }

  .map-view :global(.maplibregl-map) {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  .map-view :global(.maplibregl-ctrl-group) {
    border: 1px solid var(--border, #e5e5e5);
    box-shadow: none;
    border-radius: 8px;
    overflow: hidden;
  }

  .map-view :global(.maplibregl-ctrl-group button) {
    width: 32px;
    height: 32px;
  }

  .map-view :global(.maplibregl-ctrl-attrib) {
    font-size: 10px;
    background: rgba(250, 250, 250, 0.85);
  }

  .map-view :global(.maplibregl-ctrl-scale) {
    margin: 0 12px 28px 0;
    border-color: #a3a3a3;
    border-width: 1px 1px 2px;
    background: rgba(250, 250, 250, 0.72);
    color: #737373;
    font-size: 10px;
    font-family: var(--font-family, inherit);
    height: 14px;
    line-height: 12px;
    padding: 0 4px;
    border-radius: 2px;
  }

  .map-loading,
  .map-error {
    position: absolute;
    inset: 0;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    pointer-events: none;
    color: var(--text-tertiary, #737373);
    font-size: 0.8125rem;
  }

  .map-loading {
    background: rgba(250, 250, 250, 0.55);
  }

  .map-error {
    color: #b91c1c;
    background: rgba(250, 250, 250, 0.9);
    pointer-events: auto;
    padding: 1rem;
    text-align: center;
  }

  .spinner {
    width: 28px;
    height: 28px;
    border: 2px solid var(--border, #e5e5e5);
    border-top-color: var(--text-secondary, #525252);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
