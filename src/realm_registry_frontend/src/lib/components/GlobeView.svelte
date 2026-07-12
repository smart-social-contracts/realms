<script>
  /**
   * Pure Three.js globe (no globe.gl).
   * globe.gl kept painting a black default Phong sphere even when textures loaded;
   * this path owns the renderer + MeshBasicMaterial end-to-end.
   */
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { _ } from 'svelte-i18n';
  import {
    AmbientLight,
    BufferGeometry,
    CanvasTexture,
    Color,
    DirectionalLight,
    DoubleSide,
    Float32BufferAttribute,
    Group,
    LinearFilter,
    LinearMipmapLinearFilter,
    Mesh,
    MeshBasicMaterial,
    PerspectiveCamera,
    Raycaster,
    Scene,
    SphereGeometry,
    SRGBColorSpace,
    Vector2,
    Vector3,
    WebGLRenderer,
  } from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
  import { buildHexPolygons, buildPointMarkers } from '$lib/globe/hex-data.js';
  import {
    AUTO_ROTATE_RESUME_MS,
    AUTO_ROTATE_SPEED,
    FLY_TO_MS,
    GLOBE_BG,
    GLOBE_IMAGE_URL_GRAY,
    GLOBE_IMAGE_URL,
  } from '$lib/globe/globe-config.js';

  export let realms = [];
  export let realmZoneData = {};
  export let searchQuery = '';
  export let loading = false;

  const dispatch = createEventDispatcher();
  const GLOBE_RADIUS = 100;
  const DEG = Math.PI / 180;

  let container;
  let canvasEl;
  /** @type {import('h3-js') | null} */
  let h3 = null;
  let ready = false;
  let reducedMotion = false;
  let status = '';

  /** @type {Scene | null} */
  let scene = null;
  /** @type {PerspectiveCamera | null} */
  let camera = null;
  /** @type {WebGLRenderer | null} */
  let renderer = null;
  /** @type {OrbitControls | null} */
  let controls = null;
  /** @type {Group | null} */
  let markersGroup = null;
  /** @type {Group | null} */
  let hexGroup = null;
  /** @type {number | null} */
  let raf = null;
  let resumeTimer = null;
  let flyAnim = null;

  const raycaster = new Raycaster();
  const pointer = new Vector2();

  $: matchingRealmIds = searchQuery.trim()
    ? new Set(realms.map((r) => r.id))
    : null;
  $: dimNonMatching = Boolean(searchQuery.trim());

  function latLngToVector3(lat, lng, radius) {
    const phi = (90 - lat) * DEG;
    const theta = (lng + 180) * DEG;
    return new Vector3(
      -radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta)
    );
  }

  async function loadEarthTexture(maxAnisotropy = 4) {
    const paths = [GLOBE_IMAGE_URL_GRAY, GLOBE_IMAGE_URL];
    for (const path of paths) {
      try {
        const url = new URL(path, window.location.origin).href;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const bitmap = await createImageBitmap(blob);
        const canvas = document.createElement('canvas');
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(bitmap, 0, 0);
        bitmap.close();
        const texture = new CanvasTexture(canvas);
        texture.colorSpace = SRGBColorSpace;
        texture.generateMipmaps = true;
        texture.minFilter = LinearMipmapLinearFilter;
        texture.magFilter = LinearFilter;
        texture.anisotropy = maxAnisotropy;
        texture.needsUpdate = true;
        status = `${path.split('/').pop()} ${canvas.width}x${canvas.height}`;
        return texture;
      } catch (e) {
        console.warn('Texture failed:', path, e);
      }
    }
    const canvas = document.createElement('canvas');
    canvas.width = 2048;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#E8E8E8';
    ctx.fillRect(0, 0, 2048, 1024);
    ctx.fillStyle = '#8A8A8A';
    [
      [400, 400, 200, 240],
      [600, 600, 160, 300],
      [1100, 420, 220, 260],
      [1360, 340, 300, 200],
      [1640, 600, 140, 180],
      [1800, 760, 220, 110],
    ].forEach(([x, y, rx, ry]) => {
      ctx.beginPath();
      ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
      ctx.fill();
    });
    const texture = new CanvasTexture(canvas);
    texture.generateMipmaps = true;
    texture.minFilter = LinearMipmapLinearFilter;
    texture.magFilter = LinearFilter;
    texture.needsUpdate = true;
    status = 'fallback';
    return texture;
  }

  function clearGroup(group) {
    if (!group) return;
    while (group.children.length) {
      const child = group.children.pop();
      child.geometry?.dispose?.();
      if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
      else child.material?.dispose?.();
    }
  }

  function hexToMesh(polygon) {
    const coords = polygon.geometry?.coordinates?.[0];
    if (!coords || coords.length < 4) return null;

    const altitude = GLOBE_RADIUS * (1 + (polygon.altitude || 0.01));
    const vertices = [];
    const center = new Vector3();
    const ring = coords.slice(0, -1).map(([lng, lat]) => {
      const v = latLngToVector3(lat, lng, altitude);
      center.add(v);
      return v;
    });
    if (!ring.length) return null;
    center.multiplyScalar(1 / ring.length);

    for (let i = 0; i < ring.length; i++) {
      const a = ring[i];
      const b = ring[(i + 1) % ring.length];
      vertices.push(center.x, center.y, center.z, a.x, a.y, a.z, b.x, b.y, b.z);
    }

    const geometry = new BufferGeometry();
    geometry.setAttribute('position', new Float32BufferAttribute(vertices, 3));
    geometry.computeVertexNormals();

    const color = new Color(polygon.fillColor || '#525252');
    const material = new MeshBasicMaterial({
      color,
      transparent: true,
      opacity: Math.max(0.12, polygon.opacity || 0.35),
      side: DoubleSide,
      depthWrite: false,
    });
    const mesh = new Mesh(geometry, material);
    mesh.userData = { realmId: polygon.realmIds?.[0], type: 'hex' };
    return mesh;
  }

  function updateLayers() {
    if (!ready || !h3 || !markersGroup || !hexGroup) return;

    clearGroup(hexGroup);
    clearGroup(markersGroup);

    const polygons = buildHexPolygons(realms, realmZoneData, h3, {
      matchingRealmIds,
      dimNonMatching,
    });
    // Cap for performance — prefer center/near rings (already styled)
    polygons.slice(0, 800).forEach((p) => {
      const mesh = hexToMesh(p);
      if (mesh) hexGroup.add(mesh);
    });

    const points = buildPointMarkers(realms, realmZoneData, {
      matchingRealmIds,
      dimNonMatching,
    });
    points.forEach((p) => {
      const pos = latLngToVector3(p.lat, p.lng, GLOBE_RADIUS * 1.02);
      const geom = new SphereGeometry(Math.max(1.8, p.size * 2.2), 16, 16);
      const mat = new MeshBasicMaterial({ color: p.color || '#171717' });
      const mesh = new Mesh(geom, mat);
      mesh.position.copy(pos);
      mesh.userData = { realmId: p.realmId, type: 'marker', name: p.realmName };
      markersGroup.add(mesh);

      // Soft halo
      const halo = new Mesh(
        new SphereGeometry(Math.max(3.2, p.size * 3.5), 16, 16),
        new MeshBasicMaterial({
          color: '#171717',
          transparent: true,
          opacity: 0.12,
          depthWrite: false,
        })
      );
      halo.position.copy(pos);
      halo.userData = { realmId: p.realmId, type: 'marker' };
      markersGroup.add(halo);
    });
  }

  function pauseAutoRotate() {
    if (!controls) return;
    controls.autoRotate = false;
    if (resumeTimer) clearTimeout(resumeTimer);
    resumeTimer = setTimeout(() => {
      if (controls && !reducedMotion) controls.autoRotate = true;
    }, AUTO_ROTATE_RESUME_MS);
  }

  export function flyTo(lat, lng) {
    if (!camera || !controls) return;
    pauseAutoRotate();
    const target = latLngToVector3(lat, lng, GLOBE_RADIUS);
    const start = camera.position.clone();
    const end = target.clone().normalize().multiplyScalar(start.length());
    const t0 = performance.now();
    if (flyAnim) cancelAnimationFrame(flyAnim);

    const step = (now) => {
      const t = Math.min(1, (now - t0) / FLY_TO_MS);
      const e = t * (2 - t);
      camera.position.lerpVectors(start, end, e);
      controls.update();
      if (t < 1) flyAnim = requestAnimationFrame(step);
      else flyAnim = null;
    };
    flyAnim = requestAnimationFrame(step);
  }

  export function flyToRealm(realm) {
    const zones = realmZoneData[realm.id]?.zones;
    if (!zones?.length) return;
    const primary = [...zones].sort((a, b) => b.user_count - a.user_count)[0];
    flyTo(primary.center_lat, primary.center_lng);
  }

  function onPointerDown(event) {
    if (!renderer || !camera || !container) return;
    pauseAutoRotate();
    const rect = container.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(
      [...(markersGroup?.children || []), ...(hexGroup?.children || [])],
      false
    );
    const hit = hits.find((h) => h.object.userData?.realmId);
    if (hit?.object?.userData?.realmId) {
      dispatch('select', { realmId: hit.object.userData.realmId });
    }
  }

  function resize() {
    if (!container || !camera || !renderer) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }

  function animate() {
    raf = requestAnimationFrame(animate);
    controls?.update();
    if (renderer && scene && camera) renderer.render(scene, camera);
  }

  $: if (ready && (realms, realmZoneData, searchQuery)) {
    updateLayers();
  }

  onMount(async () => {
    if (!browser || !container || !canvasEl) return;

    reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    h3 = await import('h3-js');

    scene = new Scene();
    scene.background = new Color(GLOBE_BG);

    camera = new PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 40, 260);

    renderer = new WebGLRenderer({ canvas: canvasEl, antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.setSize(container.clientWidth, container.clientHeight, false);

    // Lights unused by MeshBasicMaterial but harmless if we add any lit objects later
    scene.add(new AmbientLight(0xffffff, 1));
    scene.add(new DirectionalLight(0xffffff, 0.4));

    const maxAniso = renderer.capabilities.getMaxAnisotropy?.() || 8;
    const texture = await loadEarthTexture(Math.min(maxAniso, 16));
    const earth = new Mesh(
      new SphereGeometry(GLOBE_RADIUS, 96, 96),
      new MeshBasicMaterial({ map: texture, color: 0xffffff })
    );
    // Align prime meridian roughly like typical globe textures
    earth.rotation.y = -Math.PI / 2;
    scene.add(earth);

    hexGroup = new Group();
    markersGroup = new Group();
    scene.add(hexGroup);
    scene.add(markersGroup);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enableZoom = true;
    controls.zoomSpeed = 0.85;
    controls.enablePan = false;
    controls.autoRotate = !reducedMotion;
    controls.autoRotateSpeed = AUTO_ROTATE_SPEED * 2.2;
    controls.minDistance = 130;
    controls.maxDistance = 420;
    controls.minPolarAngle = 0.2;
    controls.maxPolarAngle = Math.PI - 0.2;

    container.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('resize', resize);

    ready = true;
    updateLayers();
    animate();

    return () => {
      window.removeEventListener('resize', resize);
      container.removeEventListener('pointerdown', onPointerDown);
    };
  });

  onDestroy(() => {
    if (resumeTimer) clearTimeout(resumeTimer);
    if (flyAnim) cancelAnimationFrame(flyAnim);
    if (raf) cancelAnimationFrame(raf);
    controls?.dispose();
    clearGroup(hexGroup);
    clearGroup(markersGroup);
    renderer?.dispose();
    scene = null;
    camera = null;
    renderer = null;
    controls = null;
  });
</script>

<div class="globe-view" aria-label={$_('globe.aria_label')} bind:this={container}>
  <canvas class="globe-canvas" bind:this={canvasEl}></canvas>
  {#if loading}
    <div class="globe-loading">
      <div class="spinner"></div>
      <span>{$_('globe.loading')}</span>
    </div>
  {/if}
</div>

<style>
  .globe-view {
    position: absolute;
    inset: 0;
    overflow: hidden;
    background: var(--bg);
  }

  .globe-canvas {
    width: 100%;
    height: 100%;
    display: block;
  }

  .globe-loading {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    background: rgba(250, 250, 250, 0.7);
    color: var(--text-tertiary);
    font-size: 0.8125rem;
    pointer-events: none;
  }

  .spinner {
    width: 28px;
    height: 28px;
    border: 2px solid var(--border);
    border-top-color: var(--text-secondary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
