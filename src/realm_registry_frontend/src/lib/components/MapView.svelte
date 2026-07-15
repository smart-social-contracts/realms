<script>
  /**
   * MapLibre 3D globe — vector tiles (sharp zoom) + no political borders + zoom-adaptive H3.
   * Uses MapLibre's globe projection so the planet stays a sphere, not a flat map.
   */
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import { buildHexPolygons, buildPointMarkers } from '$lib/globe/hex-data.js';
  import {
    buildHexHoverPopupHtml,
    buildMarkerHoverPopupHtml,
  } from '$lib/globe/realm-hover-popup.js';
  import {
    FLY_TO_MS,
    h3ResolutionForZoom,
    influenceRingsForResolution,
    MAP_BG,
    softenGlobeBasemap,
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
  /** Far-side pins use DOM Markers — MapLibre depth-occludes circle layers. */
  const MARKER_COVERED_OPACITY = 0.48;

  let container;
  /** @type {import('maplibre-gl').Map | null} */
  let map = null;
  /** @type {typeof import('maplibre-gl') | null} */
  let maplibregl = null;
  /** @type {import('h3-js') | null} */
  let h3 = null;
  /** @type {Map<string, import('maplibre-gl').Marker>} */
  let markerById = new Map();
  /** @type {Map<string, object>} */
  let hexByIndex = new Map();
  /** @type {import('maplibre-gl').Popup | null} */
  let hoverPopup = null;
  let hoveredHexIndex = '';
  let hoveredMarkerId = '';
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

  function translate(key, opts = {}) {
    return get(_)(key, opts);
  }

  function clearHoverPopup() {
    hoveredHexIndex = '';
    hoveredMarkerId = '';
    hoverPopup?.remove();
  }

  function showHoverPopup(lngLat, html) {
    if (!map || !hoverPopup || !html) return;
    hoverPopup.setLngLat(lngLat).setHTML(html).addTo(map);
  }

  function attachMarkerHover(el, point) {
    const onEnter = () => {
      if (!map) return;
      hoveredMarkerId = point.realmId;
      hoveredHexIndex = '';
      showHoverPopup(
        [point.lng, point.lat],
        buildMarkerHoverPopupHtml(point, translate)
      );
    };
    const onLeave = () => {
      if (hoveredMarkerId === point.realmId) clearHoverPopup();
    };
    el.addEventListener('mouseenter', onEnter);
    el.addEventListener('mouseleave', onLeave);
    el.addEventListener('focus', onEnter);
    el.addEventListener('blur', onLeave);
  }

  function clearHtmlMarkers() {
    for (const marker of markerById.values()) marker.remove();
    markerById.clear();
  }

  function syncHtmlMarkers(points) {
    if (!map || !maplibregl) return;
    const seen = new Set();

    for (const p of points) {
      seen.add(p.realmId);
      let marker = markerById.get(p.realmId);
      const size = Math.round(12 * (p.size || 1));

      if (!marker) {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'realm-globe-marker';
        el.setAttribute('aria-label', p.realmName || p.realmId);
        el.style.backgroundColor = p.color;
        el.style.width = `${size}px`;
        el.style.height = `${size}px`;
        el.addEventListener('click', (e) => {
          e.stopPropagation();
          dispatch('select', { realmId: p.realmId });
        });
        attachMarkerHover(el, p);
        marker = new maplibregl.Marker({
          element: el,
          anchor: 'center',
          opacity: 1,
          opacityWhenCovered: MARKER_COVERED_OPACITY,
          subpixelPositioning: true,
        })
          .setLngLat([p.lng, p.lat])
          .addTo(map);
        markerById.set(p.realmId, marker);
      } else {
        marker.setLngLat([p.lng, p.lat]);
        const el = marker.getElement();
        el.style.backgroundColor = p.color;
        el.style.width = `${size}px`;
        el.style.height = `${size}px`;
        el.setAttribute('aria-label', p.realmName || p.realmId);
      }
    }

    for (const [id, marker] of [...markerById.entries()]) {
      if (seen.has(id)) continue;
      marker.remove();
      markerById.delete(id);
    }
  }

  function ensureLayers() {
    if (!map || map.getSource(HEX_SOURCE)) return;

    map.addSource(HEX_SOURCE, { type: 'geojson', data: emptyFeatureCollection() });

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

    hexByIndex = new Map(polygons.map((polygon) => [polygon.hexIndex, polygon]));

    const hexSource = map.getSource(HEX_SOURCE);
    if (hexSource) hexSource.setData(polygonsToGeoJSON(polygons));
    syncHtmlMarkers(points);
  }

  function onZoomEnd() {
    if (!map) return;
    const next = h3ResolutionForZoom(map.getZoom());
    if (next !== currentH3Res) updateLayers();
  }

  function onMapClick(e) {
    if (!map || !map.getLayer(HEX_FILL)) return;
    const hits = map.queryRenderedFeatures(e.point, { layers: [HEX_FILL] });
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
          0.12,
          4,
          0.04,
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

  // Comma-op truthiness is unsafe here: empty searchQuery is falsy and skipped repaints.
  $: if (ready) {
    void realms;
    void realmZoneData;
    void searchQuery;
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
      let style = stripPoliticalLayers(await styleRes.json());
      style = softenGlobeBasemap(style, { surfaceOpacity: 0.18, waterDarken: 0.45 });
      style.projection = { type: 'globe' };
      style.sky = {
        'atmosphere-blend': [
          'interpolate',
          ['linear'],
          ['zoom'],
          0,
          0.12,
          4,
          0.04,
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

      hoverPopup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        maxWidth: '300px',
        className: 'realm-hover-popup',
        offset: 18,
      });

      map.on('mousemove', HEX_FILL, (e) => {
        if (!map || !hoverPopup) return;
        const hit = e.features?.find((f) => f.properties?.hexIndex);
        if (!hit?.properties?.hexIndex) return;

        const hexIndex = String(hit.properties.hexIndex);
        map.getCanvas().style.cursor = 'pointer';

        if (hexIndex !== hoveredHexIndex) {
          hoveredHexIndex = hexIndex;
          hoveredMarkerId = '';
          const polygon = hexByIndex.get(hexIndex);
          if (polygon) {
            showHoverPopup(e.lngLat, buildHexHoverPopupHtml(polygon, translate));
          }
        } else {
          hoverPopup.setLngLat(e.lngLat);
        }
      });

      map.on('mouseenter', HEX_FILL, () => {
        if (map) map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', HEX_FILL, () => {
        if (map) map.getCanvas().style.cursor = 'grab';
        clearHoverPopup();
      });
    } catch (err) {
      console.error('Map init failed', err);
      mapError = err?.message || 'Failed to load map';
    }

    return () => {
      if (resumeTimer) clearTimeout(resumeTimer);
      if (rotateRaf) cancelAnimationFrame(rotateRaf);
      clearHoverPopup();
      hoverPopup = null;
      clearHtmlMarkers();
      map?.remove();
      map = null;
    };
  });

  onDestroy(() => {
    if (resumeTimer) clearTimeout(resumeTimer);
    if (rotateRaf) cancelAnimationFrame(rotateRaf);
    clearHoverPopup();
    hoverPopup = null;
    clearHtmlMarkers();
    map?.remove();
    map = null;
  });
</script>

<div
  class="map-view"
  data-tour="globe"
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

  @media (max-width: 767px) {
    .map-view :global(.maplibregl-ctrl-attrib),
    .map-view :global(.maplibregl-ctrl-scale) {
      display: none !important;
    }
  }

  /* Realm pins — electric blue + glow; DOM so far-side ones show through */
  .map-view :global(.realm-globe-marker) {
    display: block;
    padding: 0;
    border: 2px solid rgba(255, 255, 255, 0.95);
    border-radius: 50%;
    background-color: #00e5ff;
    box-shadow:
      0 0 6px 2px rgba(0, 229, 255, 0.95),
      0 0 14px 5px rgba(0, 180, 255, 0.55),
      0 0 28px 10px rgba(0, 140, 255, 0.28);
    cursor: pointer;
    transform: translateZ(0);
    animation: pin-glow 2.4s ease-in-out infinite;
  }

  .map-view :global(.realm-globe-marker.maplibregl-marker-covered) {
    animation: none;
    box-shadow:
      0 0 4px 1px rgba(0, 229, 255, 0.55),
      0 0 10px 3px rgba(0, 180, 255, 0.28);
    cursor: pointer;
  }

  .map-view :global(.realm-globe-marker:hover),
  .map-view :global(.realm-globe-marker:focus-visible) {
    animation: none;
    box-shadow:
      0 0 8px 3px rgba(0, 229, 255, 1),
      0 0 18px 7px rgba(0, 180, 255, 0.7),
      0 0 36px 14px rgba(0, 140, 255, 0.35);
    outline: none;
  }

  @keyframes pin-glow {
    0%,
    100% {
      box-shadow:
        0 0 6px 2px rgba(0, 229, 255, 0.95),
        0 0 14px 5px rgba(0, 180, 255, 0.55),
        0 0 28px 10px rgba(0, 140, 255, 0.28);
    }
    50% {
      box-shadow:
        0 0 8px 3px rgba(0, 229, 255, 1),
        0 0 20px 8px rgba(0, 180, 255, 0.7),
        0 0 36px 14px rgba(0, 140, 255, 0.4);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .map-view :global(.realm-globe-marker) {
      animation: none;
    }
  }

  .map-view :global(.realm-hover-popup .maplibregl-popup-content) {
    padding: 0;
    background: transparent;
    box-shadow: none;
    pointer-events: none;
  }

  .map-view :global(.realm-hover-popup .maplibregl-popup-tip) {
    display: none;
  }

  .map-view :global(.realm-hover-card) {
    min-width: 220px;
    max-width: 280px;
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid rgba(0, 229, 255, 0.28);
    background: rgba(10, 14, 22, 0.94);
    backdrop-filter: blur(14px);
    box-shadow:
      0 10px 28px rgba(0, 0, 0, 0.42),
      0 0 0 1px rgba(255, 255, 255, 0.04) inset,
      0 0 24px rgba(0, 229, 255, 0.12);
    color: #e8edf5;
    font-family: var(--font-family, inherit);
    line-height: 1.45;
  }

  .map-view :global(.realm-hover-header) {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
  }

  .map-view :global(.realm-hover-title) {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
    color: #f8fafc;
    letter-spacing: -0.01em;
  }

  .map-view :global(.realm-hover-stage) {
    flex-shrink: 0;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .map-view :global(.realm-hover-locations) {
    margin-bottom: 6px;
    font-size: 0.75rem;
    color: #94a3b8;
  }

  .map-view :global(.realm-hover-stat) {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
    font-size: 0.75rem;
    color: #cbd5e1;
  }

  .map-view :global(.realm-hover-stat.muted) {
    color: #94a3b8;
  }

  .map-view :global(.realm-hover-stat-icon) {
    color: #00e5ff;
    font-size: 0.5rem;
  }

  .map-view :global(.realm-hover-influence) {
    margin-bottom: 6px;
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #67e8f9;
  }

  .map-view :global(.realm-hover-manifesto) {
    margin: 8px 0 0;
    padding-top: 8px;
    border-top: 1px solid rgba(148, 163, 184, 0.18);
    font-size: 0.75rem;
    color: #94a3b8;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .map-view :global(.realm-hover-footer) {
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid rgba(0, 229, 255, 0.14);
    font-size: 0.6875rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    color: #67e8f9;
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
