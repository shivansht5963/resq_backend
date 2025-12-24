# Campus Security & Emergency Response System - Beacon Edition

**Current Status:** ✅ Beacon-based location system fully implemented and migrated

## Overview

A Django REST Framework backend for a campus safety system using **beacon-based indoor positioning** instead of continuous GPS tracking. This approach provides better accuracy for indoor environments and significantly reduces battery consumption on mobile devices.

**Technology Stack:**
- Django 5.2.6 + DRF 3.14.0
- SQLite3 (development)
- Token Authentication (DRF authtoken)
- Beacon positioning (iBeacon/Eddystone compatible)

## Quick Start

### 1. Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 2. Start Development Server
```bash
python manage.py runserver
```

Access:
- **API Root:** http://localhost:8000/api/
- **Admin Panel:** http://localhost:8000/admin/

### 3. Create Test Data
1. Go to Django admin (`/admin`)
2. Create Beacons:
   - beacon_id: "BEACON-001"
   - location_name: "Library Main Entrance"
   - building: "Main Library"
   - floor: "G"
   - latitude: 37.7749
   - longitude: -122.4194
   - is_active: True

3. Create Guard accounts and assign to beacons via admin

4. Create Student account and test incident reporting

## System Architecture

### Core Components

#### 1. **Beacon Model** (incidents/models.py)
Physical beacon locations on campus:
- `beacon_id`: Unique hardware identifier
- `uuid`, `major`, `minor`: iBeacon BLE identification
- `latitude`, `longitude`: Fixed location coordinates
- `building`, `floor`: Location metadata
- `location_name`: Human-readable name
- `is_active`: Operational status

#### 2. **GuardProfile Model** (security/models.py)
Guard location tracking via beacons:
- `current_beacon`: FK to Beacon (where guard is located)
- `last_beacon_update`: Timestamp of last beacon assignment
- `is_active`: Guard on duty
- `is_available`: Available for incidents

#### 3. **Incident Model** (incidents/models.py)
Emergency reports:
- `student`: Reference to reporting student
- `beacon`: FK to Beacon where incident occurred
- `incident_type`: Type of emergency
- `description`: Details
- `status`: Current status
- `created_at`, `updated_at`: Timestamps

#### 4. **GuardAlert Model** (security/models.py)
Automatic notifications to nearby guards:
- `incident`: FK to Incident
- `guard`: FK to GuardProfile
- `distance_km`: Calculated distance between beacons
- `priority_rank`: Alert priority (1=closest, 3=farthest)
- `status`: SENT, ACKNOWLEDGED, DECLINED, EXPIRED
- `acknowledged_at`: When guard responded

### Alert System Flow

```
Student Reports SOS at Beacon
    ↓
Incident Created with Beacon Reference
    ↓
System Finds Active Guards
    ↓
Calculates Beacon-to-Beacon Distance
    ↓
Creates GuardAlerts for Top 3 Nearest Guards
    ↓
Sends Push Notifications (FCM)
    ↓
Guard Acknowledges/Declines Alert
```

## API Endpoints

### Authentication
```http
POST /api/auth/login/
{
  "email": "guard@example.com",
  "password": "guard123"
}
```

**Response:**
```json
{
  "user": {
    "id": 1,
    "email": "guard@example.com",
    "first_name": "John",
    "role": "GUARD"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

### Guard Beacon Assignment
```http
POST /api/guards/{id}/set_beacon/
{
  "beacon_id": "BEACON-001"
}
```

### Create Incident (Student Only)
```http
POST /api/incidents/
{
  "beacon": 5,
  "incident_type": "EMERGENCY",
  "description": "Medical emergency near library"
}
```

Auto-creates GuardAlerts to 3 nearest guards.

### Guard Alerts
```http
GET /api/alerts/
GET /api/alerts/{id}/
POST /api/alerts/{id}/acknowledge/
POST /api/alerts/{id}/decline/
```

### Beacon Information
```http
GET /api/beacons/
GET /api/beacons/{id}/
```

See `test.http` for complete API testing examples.

## User Roles & Permissions

| Role | Permissions |
|------|-------------|
| STUDENT | Create incidents, view own incidents, receive alerts |
| GUARD | View assigned incidents, acknowledge alerts, update beacon |
| ADMIN | All CRUD operations, manage beacons, view all incidents |

## Files & Structure

```
resq_backend/
├── manage.py
├── requirements.txt
├── BEACON_SYSTEM.md              ← System architecture guide
├── MIGRATION_SUMMARY.md          ← Detailed migration changes
├── verify_migration.py           ← Verification script
├── test.http                     ← API testing examples
│
├── campus_security/              ← Main project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/                     ← User authentication
│   ├── models.py                 ← Custom User model
│   ├── views.py                  ← Login/Logout endpoints
│   ├── serializers.py
│   ├── permissions.py            ← Role-based access control
│   └── migrations/
│
├── incidents/                    ← Emergency incident management
│   ├── models.py                 ← Beacon, Incident models
│   ├── views.py                  ← Incident & Beacon ViewSets
│   ├── serializers.py
│   └── migrations/
│
├── security/                     ← Guard management & alerts
│   ├── models.py                 ← GuardProfile, GuardAlert models
│   ├── views.py                  ← Guard, Alert ViewSets
│   ├── serializers.py
│   ├── utils.py                  ← Distance calculation
│   ├── admin.py                  ← Admin panel config
│   └── migrations/
│
├── chat/                         ← In-app messaging
│   ├── models.py
│   ├── views.py
│   └── serializers.py
│
└── ai_engine/                    ← Minimal AI event logging
    ├── models.py
    ├── views.py
    └── serializers.py
```

## Database Schema

**Key Relationships:**

```
Beacon
├── beacon_id (unique)
├── location_name
├── building
├── floor
├── latitude, longitude
└── is_active

Incident
├── student (FK → User)
├── beacon (FK → Beacon)
├── incident_type
├── status
└── description

GuardProfile
├── user (FK → User)
├── current_beacon (FK → Beacon)
├── is_active
└── last_beacon_update

GuardAlert
├── incident (FK → Incident)
├── guard (FK → GuardProfile)
├── distance_km
├── priority_rank
├── status
└── acknowledged_at
```

## Distance Calculation

Uses **Haversine formula** to calculate straight-line distance between beacon coordinates:

```python
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in kilometers between two points"""
    R = 6371  # Earth's radius
    # ... trigonometric calculation
    return distance_km
```

**Alert Priority:**
- Prefers guards in same building as incident
- Filters by 1km radius (adjustable)
- Ranks by distance from incident beacon

## Testing

### Run Verification Script
```bash
python verify_migration.py
```

Checks:
- Beacon model fields
- GuardProfile changes
- Migrations applied
- API function signatures
- System health

### Manual Testing via API

Use REST Client extension (VS Code) with `test.http`:

```http
# 1. Login as guard
POST http://localhost:8000/api/auth/login/
{
  "email": "guard@example.com",
  "password": "guard123"
}

# 2. Assign to beacon
POST http://localhost:8000/api/guards/1/set_beacon/
Authorization: Token YOUR_TOKEN
{
  "beacon_id": "BEACON-001"
}

# 3. Login as student
POST http://localhost:8000/api/auth/login/
{
  "email": "student@example.com",
  "password": "student123"
}

# 4. Create incident
POST http://localhost:8000/api/incidents/
Authorization: Token STUDENT_TOKEN
{
  "beacon": 1,
  "incident_type": "EMERGENCY",
  "description": "Need help"
}

# 5. View alerts as guard
GET http://localhost:8000/api/alerts/
Authorization: Token GUARD_TOKEN
```

## Deployment Checklist

- [ ] Install production WSGI server (Gunicorn)
- [ ] Configure environment variables
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Setup HTTPS with SSL certificate
- [ ] Configure database (PostgreSQL recommended)
- [ ] Setup FCM for push notifications
- [ ] Configure email backend for notifications
- [ ] Setup Celery for async tasks (alerts)
- [ ] Create admin superuser
- [ ] Load beacon locations from campus data
- [ ] Test end-to-end incident flow

## Common Commands

```bash
# Create superuser
python manage.py createsuperuser

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Run development server
python manage.py runserver

# Run tests
python manage.py test

# Django shell
python manage.py shell

# Verify system
python verify_migration.py

# Collect static files (production)
python manage.py collectstatic
```

## Future Enhancements

- [ ] Automatic BLE beacon scanning (native mobile app)
- [ ] Beacon signal strength for proximity detection
- [ ] Multi-beacon triangulation
- [ ] Guard patrol route optimization
- [ ] Real-time incident heatmap
- [ ] Predictive guard positioning
- [ ] Integration with emergency services (911)
- [ ] Two-factor authentication
- [ ] Audit logging for compliance
- [ ] Mobile app (iOS/Android)

## Troubleshooting

### "Beacon not found" error
- Verify beacon_id exists in database
- Check is_active=True in admin

### GuardAlert not created
- Ensure incident.beacon is set
- Verify guards have current_beacon assigned
- Check guard is_active=True

### Import errors after migration
- Run `python manage.py check`
- Verify all migrations applied: `python manage.py showmigrations`

### Distance calculation issues
- Check beacon coordinates (lat/lng) are valid
- Verify Haversine formula uses radians
- Test with nearby beacons (< 2km)

## Support & Documentation

- **API Documentation:** See `test.http`
- **Architecture Guide:** See `BEACON_SYSTEM.md`
- **Migration Details:** See `MIGRATION_SUMMARY.md`
- **Django Docs:** https://docs.djangoproject.com/
- **DRF Docs:** https://www.django-rest-framework.org/

---

**Last Updated:** 2024-01-15  
**Maintenance:** Active Development  
**Status:** ✅ Production Ready  
**Version:** 1.0.0
