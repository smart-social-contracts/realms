"""Zone API for H3 hexagonal spatial aggregation of users."""

from typing import Any, Dict
from collections import defaultdict

from ggg.human import Human
from kybra_simple_logging import get_logger

logger = get_logger("api.zones")

# Default H3 resolution (7 = ~1.2km hex edge, good for city-level)
DEFAULT_H3_RESOLUTION = 7


def get_zone_aggregation(resolution: int = DEFAULT_H3_RESOLUTION) -> Dict[str, Any]:
    """
    Get aggregated user counts per H3 hexagonal cell.
    
    Args:
        resolution: H3 resolution level (0-15). Default 7 (~1.2km hex edge)
                   Lower = larger hexes, Higher = smaller hexes
    
    Returns:
        Dictionary with zone data:
        - zones: list of {h3_index, user_count, center_lat, center_lng}
        - total_users: total users with location data
        - resolution: H3 resolution used
    """
    logger.info(f"Getting zone aggregation at resolution {resolution}")
    
    try:
        # Try to import h3 - it may not be available in all environments
        try:
            import h3
        except ImportError:
            logger.warning("h3 library not available, returning empty zones")
            return {
                "success": True,
                "zones": [],
                "total_users": 0,
                "resolution": resolution,
                "error": "h3 library not installed"
            }
        
        # Aggregate users by H3 index
        zone_counts = defaultdict(int)
        users_with_location = 0
        
        for human in Human.instances():
            lat = getattr(human, 'latitude', None)
            lng = getattr(human, 'longitude', None)
            
            if lat is not None and lng is not None:
                try:
                    # Get H3 index for this location at specified resolution
                    h3_index = h3.geo_to_h3(lat, lng, resolution)
                    zone_counts[h3_index] += 1
                    users_with_location += 1
                except Exception as e:
                    logger.warning(f"Failed to get H3 index for ({lat}, {lng}): {e}")
        
        # Convert to list with center coordinates
        zones = []
        for h3_index, count in zone_counts.items():
            try:
                center_lat, center_lng = h3.h3_to_geo(h3_index)
                zones.append({
                    "h3_index": h3_index,
                    "user_count": count,
                    "center_lat": center_lat,
                    "center_lng": center_lng,
                })
            except Exception as e:
                logger.warning(f"Failed to get center for {h3_index}: {e}")
        
        logger.info(f"Found {len(zones)} zones with {users_with_location} users")
        
        return {
            "success": True,
            "zones": zones,
            "total_users": users_with_location,
            "resolution": resolution,
        }
        
    except Exception as e:
        logger.error(f"Error getting zone aggregation: {e}")
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
