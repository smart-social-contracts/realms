"""Zone API for map display."""

from typing import Any, Dict

from ggg import Zone
from kybra_simple_logging import get_logger

logger = get_logger("api.zones")

# Default H3 resolution (kept for API compatibility)
DEFAULT_H3_RESOLUTION = 7


def get_zone_aggregation(resolution: int = DEFAULT_H3_RESOLUTION) -> Dict[str, Any]:
    """
    Get zone locations for map display.
    
    Returns Zone entities directly without aggregation.
    Each Zone has pre-computed h3_index and coordinates stored at creation time.
    
    Args:
        resolution: H3 resolution level (currently unused, kept for API compatibility)
    
    Returns:
        Dictionary with zone data:
        - zones: list of {h3_index, user_count, center_lat, center_lng, location_name}
        - total_users: total users with zones
        - resolution: H3 resolution (passed through)
    """
    # TODO: Implement proper H3 cell aggregation if needed for clustering users
    # Currently returns each Zone as a separate marker for simplicity and performance
    # In order to avoid hitting the maxium cycle limit per function call, aggregation
    # must probably be implemented at the frontend or pre-computed by a separate scheduled
    # task.
    
    try:
        zones = []
        unique_users = set()
        
        for zone in Zone.instances():
            h3_index = zone.h3_index if hasattr(zone, 'h3_index') else None
            lat = zone.latitude if hasattr(zone, 'latitude') else None
            lng = zone.longitude if hasattr(zone, 'longitude') else None
            
            if not h3_index or lat is None or lng is None:
                continue
            
            zones.append({
                "h3_index": h3_index,
                "user_count": 1,
                "center_lat": lat,
                "center_lng": lng,
                "location_name": zone.name if hasattr(zone, 'name') else "Zone",
            })
            
            user_id = zone.user_id if hasattr(zone, 'user_id') else None
            if user_id:
                unique_users.add(user_id)
        
        return {
            "success": True,
            "zones": zones,
            "total_users": len(unique_users),
            "resolution": resolution,
        }
        
    except Exception as e:
        logger.error(f"Error getting zones: {e}")
        return {
            "success": False,
            "error": str(e),
            "zones": [],
            "total_users": 0,
            "resolution": resolution,
        }


def get_zone_boundaries(h3_index: str) -> Dict[str, Any]:
    """
    Get the boundary polygon for a specific H3 cell.
    
    Args:
        h3_index: H3 cell index
    
    Returns:
        Dictionary with boundary coordinates as GeoJSON-style polygon
    """
    try:
        import h3
        
        # Get boundary as list of [lat, lng] pairs
        boundary = h3.h3_to_geo_boundary(h3_index)
        
        # Convert to GeoJSON format [lng, lat]
        coordinates = [[lng, lat] for lat, lng in boundary]
        # Close the polygon
        coordinates.append(coordinates[0])
        
        return {
            "success": True,
            "h3_index": h3_index,
            "type": "Polygon",
            "coordinates": [coordinates],
        }
        
    except ImportError:
        return {"success": False, "error": "h3 library not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_human_location(human_id: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Update a human's location and compute their H3 index.
    
    Args:
        human_id: Human entity ID
        latitude: Latitude coordinate
        longitude: Longitude coordinate
    
    Returns:
        Dictionary with updated location info including H3 index
    """
    logger.info(f"Updating location for human {human_id}")
    
    try:
        human = Human[human_id]
        if not human:
            return {"success": False, "error": f"Human {human_id} not found"}
        
        # Update coordinates
        human.latitude = latitude
        human.longitude = longitude
        
        # Compute H3 index
        try:
            import h3
            h3_index = h3.geo_to_h3(latitude, longitude, DEFAULT_H3_RESOLUTION)
            human.h3_index = h3_index
        except ImportError:
            h3_index = None
            logger.warning("h3 library not available, skipping h3_index computation")
        
        return {
            "success": True,
            "human_id": human_id,
            "latitude": latitude,
            "longitude": longitude,
            "h3_index": h3_index,
        }
        
    except Exception as e:
        logger.error(f"Error updating human location: {e}")
        return {"success": False, "error": str(e)}
