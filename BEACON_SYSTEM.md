# Beacon-Based Location System

## Overview
The Campus Security & Emergency Response system uses **beacon-based indoor positioning** instead of continuous GPS tracking. This approach is more practical for campus environments and provides better battery efficiency.

## Architecture

### Beacon Model
Each physical beacon (iBeacon/Eddystone standard) has:
- **beacon_id** (unique): Hardware identifier (e.g., "BEACON-001")
- **uuid, major, minor**: iBeacon standard fields for BLE discovery
- **latitude, longitude**: Fixed location coordinates
- **building, floor**: Descriptive location metadata
- **location_name**: Human-readable name (e.g., "Library Main Entrance")
- **is_active**: Operational status

### Guard Location Tracking
Guards are identified by their nearest beacon via:
- **current_beacon** (FK to Beacon): Which beacon the guard is near
- **last_beacon_update**: Timestamp of last beacon assignment

No continuous GPS polling; guards update beacon position when moving to new areas.

### Incident Flow
1. **Student triggers SOS** at a beacon (sends beacon_id)
2. **Incident created** with beacon reference
3. **Alert system activated**:
   - Finds all active guards
   - Calculates distance between incident beacon and guard beacons
   - Auto-sends alerts to top 3 nearest guards
4. **Guard alerts** include beacon-to-beacon distance

## API Endpoints

### Guard Beacon Assignment
```http
POST /api/guards/{id}/set_beacon/
Content-Type: application/json
Authorization: Token <TOKEN>

{
  "beacon_id": "BEACON-001"
}
```

Response:
```json
{
  "detail": "Guard assigned to beacon Library Main Entrance",
  "guard": {
    "id": 1,
    "user": "guard@example.com",
    "is_active": true,
    "is_available": true,
    "current_beacon": {
      "id": 5,
      "beacon_id": "BEACON-001",
      "location_name": "Library Main Entrance",
      "building": "Main Library",
      "floor": "G",
      "latitude": 37.7749,
      "longitude": -122.4194
    },
    "last_beacon_update": "2024-01-15T10:30:00Z",
    "last_active_at": "2024-01-15T10:30:00Z"
  }
}
```

### Create Incident (with Beacon)
```http
POST /api/incidents/
Content-Type: application/json
Authorization: Token <STUDENT_TOKEN>

{
  "beacon": 5,
  "incident_type": "EMERGENCY",
  "description": "Medical emergency near library"
}
```

The system automatically:
1. Creates incident at specified beacon
2. Finds guards at nearby beacons
3. Creates GuardAlert records for top 3 nearest guards
4. Calculates beacon-to-beacon distance for each alert

## Distance Calculation

**Haversine Formula** calculates straight-line distance between beacon coordinates:
- Accepts beacons in same building on different floors
- Accepts beacons within 1km radius by default
- Prioritizes same-building assignments

## Django Admin

All beacon and guard management done via Django admin:
- **Create/edit beacons**: Campus locations with coordinates
- **Assign guards to beacons**: Manage current_beacon field
- **View alerts**: See all GuardAlert records with distances
- **Monitor incidents**: Track all emergency reports

No dedicated admin APIs needed; use Django's built-in admin interface.

## Advantages Over GPS

| Aspect | GPS | Beacons |
|--------|-----|---------|
| Indoor accuracy | Poor (walls block signal) | Excellent (10-50m) |
| Battery drain | High (continuous polling) | Minimal (passive detection) |
| Privacy | Continuous tracking | Location snapshot only |
| Implementation | Requires app background service | Simple registration |
| Deployment | Citywide coverage needed | Campus-only setup |

## Guard Mobile App Integration

Guards interact with system via:
1. **Scan beacon on arrival** at new location
2. **API call**: `POST /api/guards/{id}/set_beacon/` with beacon_id
3. **View incidents nearby**: All incidents at or near their current beacon
4. **Receive alerts**: Push notifications for incidents at nearby beacons
5. **Acknowledge/decline**: Via `/api/alerts/{id}/acknowledge/` or `/decline/`

No background location services needed; just beacon scanning.

## Future Enhancements

- [ ] Automatic beacon detection via BLE scanning (iOS/Android SDKs)
- [ ] Beacon signal strength for distance estimation
- [ ] Multi-beacon triangulation for improved accuracy
- [ ] Guard patrol route planning based on beacon network
- [ ] Heatmap visualization of incident hotspots

## Testing

Create test data via Django admin:
1. Create 3-5 beacons with different building/floor combos
2. Assign guards to specific beacons
3. Create incident at one beacon
4. Verify alerts created to guards at nearby beacons
5. Check GuardAlert distance calculations

See `test.http` for complete API testing examples.
