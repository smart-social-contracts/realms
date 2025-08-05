export const GEOGRAPHIC_BOUNDS = {
  north: 40.800776,
  south: 40.764046,
  east: -73.949297,
  west: -73.981762
};

export const GRID_SIZE = 20;

export const LAND_COLORS = {
  'residential': '#4ade80',
  'agricultural': '#fbbf24',
  'industrial': '#6b7280',
  'commercial': '#3b82f6',
  'unassigned': '#f3f4f6'
};

export function gridToLatLng(gridX, gridY) {
  const lng = GEOGRAPHIC_BOUNDS.west + 
    (gridX / (GRID_SIZE - 1)) * (GEOGRAPHIC_BOUNDS.east - GEOGRAPHIC_BOUNDS.west);
  
  const lat = GEOGRAPHIC_BOUNDS.south + 
    ((GRID_SIZE - 1 - gridY) / (GRID_SIZE - 1)) * (GEOGRAPHIC_BOUNDS.north - GEOGRAPHIC_BOUNDS.south);
  
  return [lng, lat];
}

export function latLngToGrid(lng, lat) {
  const gridX = Math.round(
    ((lng - GEOGRAPHIC_BOUNDS.west) / (GEOGRAPHIC_BOUNDS.east - GEOGRAPHIC_BOUNDS.west)) * (GRID_SIZE - 1)
  );
  
  const gridY = Math.round(
    (GRID_SIZE - 1) - ((lat - GEOGRAPHIC_BOUNDS.south) / (GEOGRAPHIC_BOUNDS.north - GEOGRAPHIC_BOUNDS.south)) * (GRID_SIZE - 1)
  );
  
  return [Math.max(0, Math.min(GRID_SIZE - 1, gridX)), Math.max(0, Math.min(GRID_SIZE - 1, gridY))];
}

export function landsToGeoJSON(lands) {
  const features = lands.map(land => {
    const [lng, lat] = gridToLatLng(land.x_coordinate, land.y_coordinate);
    
    const size = 0.0005;
    const coordinates = [[
      [lng - size, lat - size],
      [lng + size, lat - size], 
      [lng + size, lat + size],
      [lng - size, lat + size],
      [lng - size, lat - size]
    ]];

    return {
      type: 'Feature',
      properties: {
        id: land.id,
        x_coordinate: land.x_coordinate,
        y_coordinate: land.y_coordinate,
        land_type: land.land_type,
        owner_user_id: land.owner_user_id,
        owner_organization_id: land.owner_organization_id
      },
      geometry: {
        type: 'Polygon',
        coordinates: coordinates
      }
    };
  });

  return {
    type: 'FeatureCollection',
    features: features
  };
}
