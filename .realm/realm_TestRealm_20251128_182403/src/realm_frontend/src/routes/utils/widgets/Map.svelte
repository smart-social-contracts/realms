<script>
	import maplibregl from 'maplibre-gl';
	import { onMount } from 'svelte';

	export let geometry; // Accept geometry as a prop

	let map;

	onMount(() => {
		console.log('=== MAP COMPONENT START ===');
		console.log('Map component mounted with geometry:', JSON.stringify(geometry, null, 2));
		
		if (!geometry) {
			console.error('Geometry data is required for the Map component');
			return;
		}

		if (!geometry.type) {
			console.error('Invalid geometry data - missing type:', JSON.stringify(geometry, null, 2));
			return;
		}

		if (geometry.type === 'FeatureCollection' && !geometry.features) {
			console.error('Invalid FeatureCollection - missing features:', JSON.stringify(geometry, null, 2));
			return;
		}

		if (geometry.type === 'Feature' && !geometry.geometry) {
			console.error('Invalid Feature - missing geometry:', JSON.stringify(geometry, null, 2));
			return;
		}

		console.log('Initializing map with valid geometry');

		const map = new maplibregl.Map({
			container: 'map',
			style: {
				version: 8,
				sources: {
					'osm-tiles': {
						type: 'raster',
						tiles: [
							'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
							'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
							'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png'
						],
						tileSize: 256
					}
				},
				layers: [
					{
						id: 'osm-tiles',
						type: 'raster',
						source: 'osm-tiles',
						minzoom: 0,
						maxzoom: 19
					}
				]
			},
			center: [0, 0],
			zoom: 2
		});

		// Add zoom and rotation controls
		map.addControl(new maplibregl.NavigationControl(), 'top-right');

		// Add fullscreen control
		map.addControl(new maplibregl.FullscreenControl(), 'top-right');

		map.on('load', () => {
			console.log('Map loaded, adding geometry data');

			// Add the source for the geometry data
			map.addSource('geometry', {
				type: 'geojson',
				data: geometry // Use the FeatureCollection directly
			});

			// Add a filled layer with dynamic coloring based on land_type
			map.addLayer({
				id: 'geometry-layer',
				type: 'fill',
				source: 'geometry',
				paint: {
					'fill-color': [
						'case',
						['==', ['get', 'land_type'], 'residential'], '#4ade80',
						['==', ['get', 'land_type'], 'agricultural'], '#fbbf24', 
						['==', ['get', 'land_type'], 'industrial'], '#6b7280',
						['==', ['get', 'land_type'], 'commercial'], '#3b82f6',
						'#f3f4f6'
					],
					'fill-opacity': 0.7
				}
			});

			// Add an outline to the geometry
			map.addLayer({
				id: 'geometry-outline',
				type: 'line',
				source: 'geometry',
				paint: {
					'line-color': '#374151',
					'line-width': 1
				}
			});

			// Add click handler for land parcels
			map.on('click', 'geometry-layer', (e) => {
				const properties = e.features[0].properties;
				const popup = new maplibregl.Popup()
					.setLngLat(e.lngLat)
					.setHTML(`
						<div class="p-2">
							<strong>Land Parcel ${properties.id}</strong><br/>
							Grid: (${properties.x_coordinate}, ${properties.y_coordinate})<br/>
							Type: ${properties.land_type}<br/>
							${properties.owner_user_id ? `Owner: User ${properties.owner_user_id}` : 
							  properties.owner_organization_id ? `Owner: Org ${properties.owner_organization_id}` : 
							  'Unowned'}
						</div>
					`)
					.addTo(map);
			});

			// Change cursor on hover
			map.on('mouseenter', 'geometry-layer', () => {
				map.getCanvas().style.cursor = 'pointer';
			});

			map.on('mouseleave', 'geometry-layer', () => {
				map.getCanvas().style.cursor = '';
			});

			// Fit the map to the geometry bounds
			const bounds = new maplibregl.LngLatBounds();
			
			// Handle coordinates based on geometry type
			if (geometry.type === 'FeatureCollection') {
				geometry.features.forEach(feature => {
					const coords = feature.geometry.coordinates;
					if (feature.geometry.type === 'MultiPolygon') {
						coords.forEach(polygon => {
							polygon.forEach(ring => {
								ring.forEach(coord => {
									bounds.extend(coord);
								});
							});
						});
					} else if (feature.geometry.type === 'Polygon') {
						coords.forEach(ring => {
							ring.forEach(coord => {
								bounds.extend(coord);
							});
						});
					}
				});
			} else if (geometry.type === 'Feature') {
				const coords = geometry.geometry.coordinates;
				if (geometry.geometry.type === 'MultiPolygon') {
					coords.forEach(polygon => {
						polygon.forEach(ring => {
							ring.forEach(coord => {
								bounds.extend(coord);
							});
						});
					});
				} else if (geometry.geometry.type === 'Polygon') {
					coords.forEach(ring => {
						ring.forEach(coord => {
							bounds.extend(coord);
						});
					});
				}
			}

			// Fit bounds with padding
			if (!bounds.isEmpty()) {
				map.fitBounds(bounds, {
					padding: 50,
					maxZoom: 16
				});
			}
		});
	});
</script>

<div id="map" class="h-[400px] w-full rounded-lg"></div>

<style>
	@import 'maplibre-gl/dist/maplibre-gl.css';
</style>
