"""Zone API for H3 hexagonal spatial aggregation of users."""

from typing import Any, Dict
from collections import defaultdict

from ggg.human import Human
from ggg.zone import Zone
from kybra_simple_logging import get_logger

logger = get_logger("api.zones")

# Default H3 resolution (7 = ~1.2km hex edge, good for city-level)
DEFAULT_H3_RESOLUTION = 7

# Safety limit to prevent instruction limit exceeded errors
MAX_ENTITIES_TO_PROCESS = 1000


def get_zone_aggregation(resolution: int = DEFAULT_H3_RESOLUTION) -> Dict[str, Any]:
    """
    Get aggregated user counts per H3 hexagonal cell.
    
    Uses Zone entities as the primary source. Each Zone has pre-computed
    h3_index and coordinates stored at creation time.
    
    Args:
        resolution: H3 resolution level (0-15). Default 7 (~1.2km hex edge)
                   Note: Currently uses stored h3_index regardless of resolution param.
    
    Returns:
        Dictionary with zone data:
        - zones: list of {h3_index, user_count, center_lat, center_lng, location_name}
        - total_users: total users with zones
        - resolution: H3 resolution used
    """
    logger.info(f"Getting zone aggregation at resolution {resolution}")
    
    try:
        # Aggregate zones by H3 index using pre-stored values (no h3 library needed)
        # zone_data[h3_index] = {user_count, names[], lat, lng}
        zone_data = defaultdict(lambda: {"user_count": 0, "names": [], "lat": None, "lng": None})
        unique_users = set()
        
        # Collect Zone entities - they have pre-computed h3_index
        zone_count = 0
        for zone in Zone.instances():
            zone_count += 1
            if zone_count > MAX_ENTITIES_TO_PROCESS:
                logger.warning(f"Zone entity limit reached ({MAX_ENTITIES_TO_PROCESS})")
                break
            
            # Read pre-stored values directly (no h3 computation)
            h3_index = zone.h3_index if hasattr(zone, 'h3_index') else None
            if not h3_index:
                continue
                
            lat = zone.latitude if hasattr(zone, 'latitude') else None
            lng = zone.longitude if hasattr(zone, 'longitude') else None
            name = zone.name if hasattr(zone, 'name') else 'Zone'
            user_id = zone.user_id if hasattr(zone, 'user_id') else None
            
            zone_data[h3_index]["user_count"] += 1
            zone_data[h3_index]["names"].append(name)
            if lat is not None and zone_data[h3_index]["lat"] is None:
                zone_data[h3_index]["lat"] = lat
            if lng is not None and zone_data[h3_index]["lng"] is None:
                zone_data[h3_index]["lng"] = lng
            
            if user_id:
                unique_users.add(user_id)
        
        logger.info(f"Processed {zone_count} Zone entities")
        
        # Also check Human entities with pre-stored h3_index
        human_count = 0
        for human in Human.instances():
            human_count += 1
            if human_count > MAX_ENTITIES_TO_PROCESS:
                logger.warning(f"Human entity limit reached ({MAX_ENTITIES_TO_PROCESS})")
                break
            
            user_id = human.user_id if hasattr(human, 'user_id') else None
            
            # Skip if already counted via Zone
            if user_id and user_id in unique_users:
                continue
            
            # Use pre-stored h3_index if available
            h3_index = human.h3_index if hasattr(human, 'h3_index') else None
            if not h3_index:
                continue
                
            lat = human.latitude if hasattr(human, 'latitude') else None
            lng = human.longitude if hasattr(human, 'longitude') else None
            name = human.name if hasattr(human, 'name') else 'User'
            
            zone_data[h3_index]["user_count"] += 1
            zone_data[h3_index]["names"].append(name)
            if lat is not None and zone_data[h3_index]["lat"] is None:
                zone_data[h3_index]["lat"] = lat
            if lng is not None and zone_data[h3_index]["lng"] is None:
                zone_data[h3_index]["lng"] = lng
            
            if user_id:
                unique_users.add(user_id)
        
        logger.info(f"Processed {human_count} Human entities")
        
        # Convert to list
        zones = []
        for h3_index, data in zone_data.items():
            # Skip if no coordinates
            if data["lat"] is None or data["lng"] is None:
                continue
            
            # Create location name from zone names
            location_name = ", ".join(data["names"][:3])
            if len(data["names"]) > 3:
                location_name += f" +{len(data['names']) - 3} more"
            
            zones.append({
                "h3_index": h3_index,
                "user_count": data["user_count"],
                "center_lat": data["lat"],
                "center_lng": data["lng"],
                "location_name": location_name or "Zone",
            })
        
        total_users = len(unique_users)
        logger.info(f"Found {len(zones)} zones with {total_users} users")
        
        return {
            "success": True,
            "zones": zones,
            "total_users": total_users,
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
