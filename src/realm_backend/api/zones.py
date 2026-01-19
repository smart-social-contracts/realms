"""Zone API for H3 hexagonal spatial aggregation of users."""

from typing import Any, Dict
from collections import defaultdict

from ggg.human import Human
from ggg.zone import Zone
from kybra_simple_logging import get_logger

logger = get_logger("api.zones")

# Default H3 resolution (7 = ~1.2km hex edge, good for city-level)
DEFAULT_H3_RESOLUTION = 7


def get_zone_aggregation(resolution: int = DEFAULT_H3_RESOLUTION) -> Dict[str, Any]:
    """
    Get aggregated user counts per H3 hexagonal cell.
    
    Uses Zone entities as the primary source. Each Zone represents a user's
    zone of influence with an H3 index and coordinates.
    
    Args:
        resolution: H3 resolution level (0-15). Default 7 (~1.2km hex edge)
                   Lower = larger hexes, Higher = smaller hexes
    
    Returns:
        Dictionary with zone data:
        - zones: list of {h3_index, user_count, center_lat, center_lng, location_name}
        - total_users: total users with zones
        - resolution: H3 resolution used
    """
    logger.info(f"Getting zone aggregation at resolution {resolution}")
    
    try:
        # Try to import h3 - it may not be available in all environments
        try:
            import h3
            h3_available = True
        except ImportError:
            logger.warning("h3 library not available")
            h3_available = False
        
        # Aggregate zones by H3 index
        # zone_data[h3_index] = {user_count, names[], lat, lng}
        zone_data = defaultdict(lambda: {"user_count": 0, "names": [], "lat": None, "lng": None})
        total_users = 0
        unique_users = set()
        
        # First, collect all Zone entities
        for zone in Zone.instances():
            h3_index = getattr(zone, 'h3_index', None)
            lat = getattr(zone, 'latitude', None)
            lng = getattr(zone, 'longitude', None)
            name = getattr(zone, 'name', 'Zone')
            user = getattr(zone, 'user', None)
            user_id = getattr(zone, 'user_id', None) or (user.id if user else None)
            
            # Skip zones without h3_index - try to compute from lat/lng
            if not h3_index and lat is not None and lng is not None and h3_available:
                try:
                    h3_index = h3.geo_to_h3(lat, lng, resolution)
                except Exception as e:
                    logger.warning(f"Failed to compute H3 index for zone: {e}")
                    continue
            
            if not h3_index:
                continue
            
            # Re-index to requested resolution if different
            zone_resolution = getattr(zone, 'resolution', None)
            if h3_available and zone_resolution and int(zone_resolution) != resolution:
                try:
                    # Get center of original cell and re-index at new resolution
                    center_lat, center_lng = h3.h3_to_geo(h3_index)
                    h3_index = h3.geo_to_h3(center_lat, center_lng, resolution)
                except Exception as e:
                    logger.warning(f"Failed to re-index zone: {e}")
            
            zone_data[h3_index]["user_count"] += 1
            zone_data[h3_index]["names"].append(name)
            if lat is not None:
                zone_data[h3_index]["lat"] = lat
            if lng is not None:
                zone_data[h3_index]["lng"] = lng
            
            if user_id:
                unique_users.add(user_id)
        
        total_users = len(unique_users)
        
        # Also include Human entities that have location data
        # (they may not have a Zone entity but still have coordinates)
        logger.info("Checking Human entities for location data")
        for human in Human.instances():
            lat = getattr(human, 'latitude', None)
            lng = getattr(human, 'longitude', None)
            # Get the linked User ID (not the Human ID) for deduplication
            user = getattr(human, 'user', None)
            user_id = getattr(human, 'user_id', None) or (user.id if user else None)
            
            # Skip if this human's user was already counted via a Zone entity
            if user_id and user_id in unique_users:
                continue
            
            if lat is not None and lng is not None and h3_available:
                try:
                    h3_index = h3.geo_to_h3(lat, lng, resolution)
                    zone_data[h3_index]["user_count"] += 1
                    zone_data[h3_index]["names"].append(getattr(human, 'name', 'User'))
                    if zone_data[h3_index]["lat"] is None:
                        zone_data[h3_index]["lat"] = lat
                    if zone_data[h3_index]["lng"] is None:
                        zone_data[h3_index]["lng"] = lng
                    total_users += 1
                    if user_id:
                        unique_users.add(user_id)
                except Exception as e:
                    logger.warning(f"Failed to get H3 index for ({lat}, {lng}): {e}")
        
        # Convert to list with center coordinates
        zones = []
        for h3_index, data in zone_data.items():
            try:
                # Use stored lat/lng or compute from h3 cell center
                if data["lat"] is not None and data["lng"] is not None:
                    center_lat, center_lng = data["lat"], data["lng"]
                elif h3_available:
                    center_lat, center_lng = h3.h3_to_geo(h3_index)
                else:
                    continue
                
                # Create location name from zone names
                location_name = ", ".join(data["names"][:3])  # Limit to first 3 names
                if len(data["names"]) > 3:
                    location_name += f" +{len(data['names']) - 3} more"
                
                zones.append({
                    "h3_index": h3_index,
                    "user_count": data["user_count"],
                    "center_lat": center_lat,
                    "center_lng": center_lng,
                    "location_name": location_name or "Zone",
                })
            except Exception as e:
                logger.warning(f"Failed to get center for {h3_index}: {e}")
        
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
