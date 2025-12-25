# Non-Emergency Incident Report Implementation

## Overview
Added support for students to report non-emergency incidents (Safety Concerns, Suspicious Activity, Infrastructure Issues, etc.) using a new `POST /incidents/report/` endpoint.

## Changes Made

### 1. **Model Changes** (`incidents/models.py`)
- Added `STUDENT_REPORT` signal type to `IncidentSignal.SignalType`:
  ```python
  STUDENT_REPORT = "STUDENT_REPORT", "Student General Report"
  ```
- This allows distinguishing between emergency SOS reports and general incident reports

### 2. **Serializer Changes** (`incidents/serializers.py`)
- Added new `IncidentReportSerializer` with fields:
  - `beacon_id` (optional): Hardware beacon ID for BLE-detected incidents
  - `type` (required): Report type category (e.g., "Safety Concern", "Suspicious Activity", "Infrastructure Issue")
  - `description` (required): Detailed description of the incident
  - `location` (optional): Location description if no beacon available

### 3. **Endpoint Implementation** (`incidents/views.py`)
- New endpoint: `POST /api/incidents/report/`
- Features:
  - Accepts both beacon-based and location-based reports
  - Uses deduplication logic (same as SOS) - combines multiple reports at same location
  - Creates `IncidentSignal` with type `STUDENT_REPORT`
  - Alerts guards when new incident is created
  - Returns incident details with all signals

**Request:**
```json
{
  "beacon_id": "safe:uuid:403:403",  // optional
  "type": "Safety Concern",
  "description": "Detailed description here",
  "location": "Building A, Room 201"  // optional if beacon_id provided
}
```

**Response:**
```json
{
  "status": "incident_created",
  "incident_id": "uuid",
  "signal_id": 123,
  "report_type": "Safety Concern",
  "incident": { ...full incident details... }
}
```

### 4. **Service Layer Updates** (`incidents/services.py`)
- Updated `get_or_create_incident_with_signals()` to handle virtual beacon IDs:
  - Beacon IDs starting with `location:` are treated as virtual beacons
  - Automatically creates virtual beacon placeholder in database
  - Enables grouping of location-based reports
  - Example: `location:dormitory_building_a_ground_floor`

### 5. **Testing** (`test.http`)
Added 3 test cases:
- **2.1d**: Report with beacon ID (Safety Concern)
- **2.1e**: Report without beacon (Location-based, Suspicious Activity)
- **2.1f**: Report with beacon (Infrastructure Issue)

## How It Works

### Scenario 1: Beacon-Based Report
```
Student detects beacon "safe:uuid:403:403"
↓
POST /incidents/report/
{
  "beacon_id": "safe:uuid:403:403",
  "type": "Broken Glass",
  "description": "Glass hazard at entrance"
}
↓
Check if incident exists at this beacon within 5 minutes
├─ YES: Add STUDENT_REPORT signal to existing incident
└─ NO: Create new incident with STUDENT_REPORT signal
↓
Alert guards
↓
Response with incident_id
```

### Scenario 2: Location-Based Report
```
Student reports without beacon
↓
POST /incidents/report/
{
  "type": "Suspicious Activity",
  "description": "Unknown person loitering",
  "location": "Dorm Building A"
}
↓
Create virtual beacon_id: "location:dorm_building_a"
↓
Check if incident exists for this location within 5 minutes
├─ YES: Add STUDENT_REPORT signal to existing incident
└─ NO: Create new incident with STUDENT_REPORT signal
↓
Alert guards
↓
Response with incident_id
```

## Deduplication Logic
- Multiple reports at same beacon/location within **5 minutes** are combined into single incident
- Each report becomes separate `IncidentSignal` with type `STUDENT_REPORT`
- Guards see all signals under one incident
- Supports tracking multiple reports of same issue

## Response Codes
- `201 CREATED`: New incident created
- `200 OK`: Signal added to existing incident
- `400 BAD REQUEST`: Missing required fields or invalid input
- `403 FORBIDDEN`: Non-student user attempted to report

## API Endpoint Summary
```
POST /api/incidents/report/

Required: type, description
Optional: beacon_id, location (at least one of beacon_id or location required)

Response:
- 201/200 OK with incident details
- Signal type: STUDENT_REPORT
- Full deduplication support
- Guard alert on new incident creation
```

## Testing Checklist
- [x] Implementation complete
- [ ] Test 2.1d: Beacon-based safety concern report
- [ ] Test 2.1e: Location-based suspicious activity report
- [ ] Test 2.1f: Infrastructure issue report
- [ ] Verify incident deduplication (multiple reports at same location)
- [ ] Verify guard alert notification
- [ ] Check incident details include all signals
- [ ] Test with missing fields (should fail)
- [ ] Test with both beacon_id and location (should work)
- [ ] Test without beacon_id and location (should fail)

## Notes
- Virtual beacons created automatically for location-based reports
- Reports combine with SOS, AI_VISION, AI_AUDIO, and PANIC_BUTTON signals
- Each report type tracked separately via IncidentSignal.signal_type
- Full audit trail maintained (created_at, source_user, etc.)
- Guards can distinguish report types in incident details
