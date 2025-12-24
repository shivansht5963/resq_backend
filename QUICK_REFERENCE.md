# Beacon System - Developer Quick Reference

## What Changed?

| Aspect | Before | After |
|--------|--------|-------|
| **Location Tracking** | GPS coordinates (continuous) | Beacon ID (snapshot) |
| **Guard Position** | last_known_latitude/longitude | current_beacon (FK) |
| **Incident Location** | incident.latitude/longitude | incident.beacon (FK) |
| **Distance Calc** | Haversine on coordinates | Haversine on beacon coords |
| **API Endpoint** | PUT /guards/{id}/update_location/ | POST /guards/{id}/set_beacon/ |
| **Distance Radius** | 5km | 1km (same building priority) |

## Key Models

### Beacon (incidents/models.py)
```python
class Beacon(models.Model):
    beacon_id = models.CharField(unique=True)           # "BEACON-001"
    uuid = models.CharField()                           # iBeacon UUID
    major = models.IntegerField()                       # iBeacon major
    minor = models.IntegerField()                       # iBeacon minor
    latitude = models.FloatField()                      # 37.7749
    longitude = models.FloatField()                     # -122.4194
    location_name = models.CharField()                  # "Library Entrance"
    building = models.CharField()                       # "Main Library"
    floor = models.CharField()                          # "G" or "1"
    is_active = models.BooleanField(default=True)      # operational?
```

### GuardProfile (security/models.py)
```python
class GuardProfile(models.Model):
    user = models.OneToOneField(User)
    current_beacon = models.ForeignKey(Beacon, null=True)  # Where guard is
    last_beacon_update = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField()                  # on duty?
    is_available = models.BooleanField()               # can respond?
```

### GuardAlert (security/models.py)
```python
class GuardAlert(models.Model):
    incident = models.ForeignKey(Incident)
    guard = models.ForeignKey(GuardProfile)
    distance_km = models.FloatField()                  # calculated
    priority_rank = models.IntegerField()              # 1, 2, or 3
    status = models.CharField(choices=[
        'SENT', 'ACKNOWLEDGED', 'DECLINED', 'EXPIRED'
    ])
    acknowledged_at = models.DateTimeField(null=True)
```

## Key Functions

### Find Nearest Guards by Beacon
```python
# security/utils.py
from security.utils import get_top_n_nearest_guards

nearest_guards = get_top_n_nearest_guards(
    incident_beacon=incident.beacon,
    n=3,                              # top 3
    max_distance_km=1.0               # 1km radius
)

# Returns: [(GuardProfile, distance_km), ...]
# Example: [(guard1, 0.2), (guard2, 0.5), (guard3, 0.8)]
```

### Create Incident with Auto-Alerts
```python
# incidents/views.py - performed in perform_create()
incident = Incident.objects.create(
    student=request.user,
    beacon=beacon_obj,
    incident_type='EMERGENCY'
)

# Auto-alerts created to top 3 nearest guards
# GuardAlert records created with distance_km
```

### Assign Guard to Beacon
```python
# security/views.py - POST /api/guards/{id}/set_beacon/
guard_profile = GuardProfile.objects.get(id=1)
beacon = Beacon.objects.get(beacon_id='BEACON-001')

guard_profile.current_beacon = beacon
guard_profile.last_beacon_update = timezone.now()
guard_profile.save()
```

## API Examples

### 1. Create Test Beacon (Admin)
```bash
curl -X POST http://localhost:8000/api/beacons/ \
  -H "Authorization: Token ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "BEACON-001",
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "major": 100,
    "minor": 1,
    "latitude": 37.7749,
    "longitude": -122.4194,
    "location_name": "Library Entrance",
    "building": "Main Library",
    "floor": "G",
    "is_active": true
  }'
```

### 2. Assign Guard to Beacon
```bash
curl -X POST http://localhost:8000/api/guards/1/set_beacon/ \
  -H "Authorization: Token GUARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"beacon_id": "BEACON-001"}'
```

### 3. Create Incident (Triggers Alerts)
```bash
curl -X POST http://localhost:8000/api/incidents/ \
  -H "Authorization: Token STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "beacon": 1,
    "incident_type": "EMERGENCY",
    "description": "Help needed"
  }'
```

Response includes auto-created alerts to 3 nearest guards.

### 4. View Alerts as Guard
```bash
curl -X GET http://localhost:8000/api/alerts/ \
  -H "Authorization: Token GUARD_TOKEN"
```

Returns alerts for current guard with distance_km.

### 5. Acknowledge Alert
```bash
curl -X POST http://localhost:8000/api/alerts/1/acknowledge/ \
  -H "Authorization: Token GUARD_TOKEN"
```

## Testing Workflow

### Step 1: Create Beacons
Django admin → Incidents → Beacons → Add Beacon
- Create 3-5 beacons at different buildings

### Step 2: Assign Guards
Django admin → Security → Guard Profiles → Select Guard
- Set current_beacon for each guard profile

### Step 3: Create Incident
```http
POST http://localhost:8000/api/incidents/
Authorization: Token STUDENT_TOKEN
{
  "beacon": 1,
  "incident_type": "EMERGENCY",
  "description": "Test incident"
}
```

### Step 4: Verify Alerts
```http
GET http://localhost:8000/api/alerts/
Authorization: Token GUARD_TOKEN
```

Should see alerts for 3 nearest guards with calculated distances.

## Common Mistakes

### ❌ Trying to use old GPS fields
```python
# WRONG - these fields don't exist anymore
guard.last_known_latitude = 37.7749  # ERROR!
incident.longitude = -122.4194        # ERROR!
```

### ✓ Correct beacon-based approach
```python
# RIGHT - use beacon FK
guard.current_beacon = beacon_obj
incident.beacon = beacon_obj
```

### ❌ Creating incident without beacon
```python
# WRONG
incident = Incident.objects.create(
    student=user
    # No beacon!
)
# No alerts will be created
```

### ✓ Always set beacon
```python
# RIGHT
incident = Incident.objects.create(
    student=user,
    beacon=beacon_obj  # Required for alerts
)
```

### ❌ Forgetting to activate beacon
```python
# WRONG - beacon won't be used for alerts
beacon.is_active = False
beacon.save()

incident = Incident.objects.create(beacon=beacon)
# Alert system skips inactive beacons
```

### ✓ Verify beacon is active
```python
# RIGHT
assert beacon.is_active == True
incident = Incident.objects.create(beacon=beacon)
```

## Useful Queries

```python
# Get all guards at a specific beacon
guards_at_beacon = GuardProfile.objects.filter(
    current_beacon__beacon_id='BEACON-001',
    is_active=True,
    is_available=True
)

# Get all alerts for an incident
incident_alerts = GuardAlert.objects.filter(
    incident_id=123
).order_by('priority_rank')

# Find unacknowledged alerts
pending_alerts = GuardAlert.objects.filter(
    status='SENT'
)

# Get recent incidents
recent = Incident.objects.filter(
    created_at__gte=timezone.now() - timedelta(hours=1)
).order_by('-created_at')

# Get incidents in a specific building
building_incidents = Incident.objects.filter(
    beacon__building='Main Library'
)

# Distance histogram
from django.db.models import F, FloatField
from django.db.models.functions import Trunc
alerts_by_distance = GuardAlert.objects.values('distance_km')
```

## File Locations for Quick Edit

| File | Purpose |
|------|---------|
| `incidents/models.py` | Beacon, Incident models |
| `security/models.py` | GuardProfile, GuardAlert models |
| `security/utils.py` | Distance calculation logic |
| `incidents/views.py` | Incident creation + alert generation |
| `security/views.py` | Guard beacon assignment endpoint |
| `security/serializers.py` | API response formatting |
| `test.http` | API testing examples |

## Performance Notes

- **Beacon queries:** Indexed by beacon_id (fast)
- **Guard filtering:** Indexed by current_beacon + is_active (fast)
- **Distance calculation:** O(n) where n=guards (acceptable for campus scale)
- **Alert creation:** Batch create for top 3 (efficient)

## Next Development Tasks

1. [ ] Implement automatic BLE beacon scanning (mobile SDK)
2. [ ] Add Celery tasks for async alert delivery
3. [ ] Setup FCM for push notifications
4. [ ] Create React Native mobile app
5. [ ] Add heatmap visualization
6. [ ] Implement audit logging
7. [ ] Setup comprehensive testing (pytest)
8. [ ] Add API rate limiting
9. [ ] Setup CI/CD pipeline
10. [ ] Migrate to PostgreSQL (production)

---

**Last Updated:** 2024-01-15  
**Beacon System Version:** 1.0.0
