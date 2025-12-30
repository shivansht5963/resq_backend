# AI Detection Endpoints

## Overview

Two new dedicated AI detection endpoints for **violence** and **scream** detection:

- `POST /api/ai/violence-detected/` - Violence/Fight detection
- `POST /api/ai/scream-detected/` - Scream/Cry detection

Both endpoints:
1. Create an `AIEvent` for logging/analytics
2. Create an `IncidentSignal` if confidence meets threshold
3. Create a new `Incident` OR add signal to existing incident (5-min dedup window)
4. Alert nearest guards if new incident created
5. Support beacon_id, confidence_score, and description

---

## Endpoint 1: Violence Detected

### POST /api/ai/violence-detected/

Detects violence/fights and triggers incident creation if confidence ≥ 75%.

**Request:**
```json
{
  "beacon_id": "safe:uuid:403:403",
  "confidence_score": 0.92,
  "description": "Fight detected between 2 people near library entrance"
}
```

**Fields:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `beacon_id` | string | ✅ | Hardware beacon ID (e.g., "safe:uuid:403:403") |
| `confidence_score` | float | ✅ | 0.0-1.0 (must be ≥ 0.75 to create incident) |
| `description` | string | ✅ | What violence was detected |

**Response (201 - New Incident):**
```json
{
  "status": "incident_created",
  "ai_event_id": 123,
  "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "signal_id": 456,
  "confidence_score": 0.92,
  "beacon_location": "Library 3F Entrance",
  "incident_status": "CREATED",
  "incident_priority": "Critical"
}
```

**Response (200 - Added to Existing Incident):**
```json
{
  "status": "signal_added_to_existing",
  "ai_event_id": 123,
  "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "signal_id": 456,
  "confidence_score": 0.92,
  "beacon_location": "Library 3F Entrance",
  "incident_status": "ASSIGNED",
  "incident_priority": "Critical"
}
```

**Response (200 - Below Threshold):**
```json
{
  "status": "logged_only",
  "ai_event_id": 123,
  "message": "Confidence 0.65 below threshold 0.75"
}
```

**Signal Type:** `VIOLENCE_DETECTED`  
**Incident Priority:** CRITICAL  
**Confidence Threshold:** 0.75 (75%)  
**Guards Alerted:** Yes (if new incident)

---

## Endpoint 2: Scream Detected

### POST /api/ai/scream-detected/

Detects screaming/crying and triggers incident creation if confidence ≥ 80%.

**Request:**
```json
{
  "beacon_id": "safe:uuid:402:402",
  "confidence_score": 0.88,
  "description": "Loud screaming detected in dormitory hallway"
}
```

**Fields:**
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `beacon_id` | string | ✅ | Hardware beacon ID |
| `confidence_score` | float | ✅ | 0.0-1.0 (must be ≥ 0.80 to create incident) |
| `description` | string | ✅ | What scream/cry was detected |

**Response (201 - New Incident):**
```json
{
  "status": "incident_created",
  "ai_event_id": 124,
  "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dd",
  "signal_id": 457,
  "confidence_score": 0.88,
  "beacon_location": "Dormitory 4F Hallway",
  "incident_status": "CREATED",
  "incident_priority": "High"
}
```

**Response (200 - Below Threshold):**
```json
{
  "status": "logged_only",
  "ai_event_id": 124,
  "message": "Confidence 0.72 below threshold 0.80"
}
```

**Signal Type:** `SCREAM_DETECTED`  
**Incident Priority:** HIGH  
**Confidence Threshold:** 0.80 (80%)  
**Guards Alerted:** Yes (if new incident)

---

## Key Behaviors

### 1. Deduplication (5-minute window)
If an incident already exists at the same beacon within the last 5 minutes:
- New signal is added to existing incident (don't create duplicate)
- Response: `"status": "signal_added_to_existing"`
- Guards are NOT re-alerted (only on first incident creation)
- Priority may escalate if new signal is higher priority

### 2. Confidence Thresholds
- **Violence:** 0.75 (75%) - Creates incident if met
- **Scream:** 0.80 (80%) - Creates incident if met
- Below threshold: Event is logged but NO incident created

### 3. Incident Priorities
- **Violence Detection** → CRITICAL (guards respond with high urgency)
- **Scream Detection** → HIGH (guards respond quickly)
- If signal added to existing MEDIUM incident → escalates to CRITICAL/HIGH

### 4. Guard Alerting
- Nearest 3 guards alerted via beacon-proximity search
- Only on NEW incident creation (not on signal merging)
- Guards receive alerts with incident location and type

### 5. Conversation
- Automatic `Conversation` created between guards and student
- Allows real-time messaging during incident response

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "beacon_id is required"
}
```

**Possible errors:**
- `"beacon_id is required"`
- `"confidence_score is required (0.0-1.0)"`
- `"description is required"`
- `"confidence_score must be between 0.0 and 1.0"`
- `"confidence_score must be a valid number"`

### 404 Not Found
```json
{
  "error": "Beacon safe:uuid:999:999 not found or inactive"
}
```

---

## Example Usage

### cURL - Violence Detection
```bash
curl -X POST "http://localhost:8000/api/ai/violence-detected/" \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "safe:uuid:403:403",
    "confidence_score": 0.92,
    "description": "Fight detected near library entrance"
  }'
```

### cURL - Scream Detection
```bash
curl -X POST "http://localhost:8000/api/ai/scream-detected/" \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "safe:uuid:402:402",
    "confidence_score": 0.88,
    "description": "Loud screaming from dormitory hallway"
  }'
```

### Python
```python
import requests

# Violence Detection
response = requests.post(
    'http://localhost:8000/api/ai/violence-detected/',
    json={
        'beacon_id': 'safe:uuid:403:403',
        'confidence_score': 0.92,
        'description': 'Fight detected'
    }
)
print(response.json())

# Scream Detection
response = requests.post(
    'http://localhost:8000/api/ai/scream-detected/',
    json={
        'beacon_id': 'safe:uuid:402:402',
        'confidence_score': 0.88,
        'description': 'Screaming heard'
    }
)
print(response.json())
```

---

## Legacy Endpoint (Deprecated)

### POST /api/ai-detection/

The old endpoint still works for backward compatibility, but supports both old and new types:

```json
{
  "beacon_id": "safe:uuid:403:403",
  "event_type": "VIOLENCE" | "SCREAM" | "VISION" | "AUDIO",
  "confidence_score": 0.92,
  "description": "Optional description",
  "details": {
    "additional_info": "..."
  }
}
```

**Note:** Use the new dedicated endpoints instead. This legacy endpoint maps:
- `VISION` → `violence_detected` endpoint (0.75 threshold)
- `AUDIO` → `scream_detected` endpoint (0.80 threshold)
- `VIOLENCE` → `violence_detected` endpoint
- `SCREAM` → `scream_detected` endpoint

---

## Database Schema

### AIEvent Model
```python
beacon_id          # FK to Beacon
event_type         # VIOLENCE or SCREAM
confidence_score   # 0.0-1.0
details = {
    'description': "...",
    'raw_confidence': 0.92
}
created_at
```

### IncidentSignal Model
```python
incident           # FK to Incident
signal_type        # VIOLENCE_DETECTED or SCREAM_DETECTED
ai_event           # FK to AIEvent (this detection)
details = {
    'ai_confidence': 0.92,
    'ai_type': 'violence' or 'scream'
}
created_at
```

### Incident Model
```python
beacon             # Where detection happened
status             # CREATED → ASSIGNED → IN_PROGRESS → RESOLVED
priority           # CRITICAL (violence) or HIGH (scream)
description        # From AI detection
```

---

## Workflow

```
AI Model Detects Violence/Scream
    ↓
POST /api/ai/violence-detected/ or /api/ai/scream-detected/
    ↓
[STEP 1] Create AIEvent (always, for audit trail)
    ↓
[STEP 2] Check Confidence vs Threshold
    └─→ Below? Return "logged_only" (no incident)
    └─→ Met? Continue...
    ↓
[STEP 3] Check for Existing Incident (5-min window, same beacon)
    └─→ Found? Add signal to existing incident → return "signal_added_to_existing"
    └─→ Not found? Create new incident → return "incident_created"
    ↓
[STEP 4] If NEW incident created:
    ├─→ Create Conversation
    ├─→ Find 3 nearest guards
    ├─→ Create GuardAlerts
    └─→ Notify guards via FCM push
    ↓
Response to AI Server with incident_id + status
```

---

## Testing

See [AI_DETECTION_TEST.http](AI_DETECTION_TEST.http) for complete test examples.

Quick test:
```
POST http://localhost:8000/api/ai/violence-detected/
Content-Type: application/json

{
  "beacon_id": "safe:uuid:403:403",
  "confidence_score": 0.92,
  "description": "Test violence detection"
}
```

Expected: 201 Created with incident_id
