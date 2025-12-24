"""
Utility functions for guard and location calculations (Beacon-based).
Guards are located via nearby beacons instead of continuous GPS tracking.
"""
from math import radians, sin, cos, sqrt, atan2
from security.models import GuardProfile
from incidents.models import Beacon


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def find_nearest_guards_by_beacon(incident_beacon, max_distance_km=1.0):
    """
    Find nearest available guards by their assigned beacons.
    Uses beacon-to-beacon distance instead of GPS coordinates.
    
    Args:
        incident_beacon: Beacon instance where incident occurred
        max_distance_km: Maximum search radius in km (default 1.0km for nearby beacons)
    
    Returns:
        List of (GuardProfile, distance_km) tuples sorted by distance
    """
    guards = GuardProfile.objects.filter(
        is_active=True, 
        user__is_active=True,
        current_beacon__isnull=False  # Only guards with assigned beacon
    )
    
    nearest_guards = []
    
    for guard in guards:
        guard_beacon = guard.current_beacon
        
        # Calculate distance between beacons using their coordinates
        if guard_beacon and guard_beacon.latitude and guard_beacon.longitude:
            if incident_beacon.latitude and incident_beacon.longitude:
                distance = haversine_distance(
                    incident_beacon.latitude,
                    incident_beacon.longitude,
                    guard_beacon.latitude,
                    guard_beacon.longitude
                )
                
                # Consider guards within max_distance_km or same building
                if (distance <= max_distance_km or 
                    (incident_beacon.building and guard_beacon.building and
                     incident_beacon.building == guard_beacon.building)):
                    nearest_guards.append((guard, distance))
    
    # Sort by distance
    nearest_guards.sort(key=lambda x: x[1])
    
    return nearest_guards


def get_top_n_nearest_guards(incident_beacon, n=3, max_distance_km=1.0):
    """
    Get top N nearest guards by beacon location.
    
    Args:
        incident_beacon: Beacon instance where incident occurred
        n: Number of guards to return (default 3)
        max_distance_km: Maximum search radius in km (default 1.0km)
    
    Returns:
        List of top N (GuardProfile, distance_km) tuples
    """
    nearest = find_nearest_guards_by_beacon(incident_beacon, max_distance_km)
    return nearest[:n]
