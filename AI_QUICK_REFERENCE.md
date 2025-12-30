# 🎯 AI Detection - Quick Reference Card

## Two Endpoints, Three Seconds Each

### Violence Detection
```bash
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -H "Content-Type: application/json" \
  -d '{"beacon_id":"safe:uuid:403:403","confidence_score":0.92,"description":"Fight"}'
```
**Threshold:** 0.75 | **Priority:** CRITICAL | **Alerts:** 3 guards

### Scream Detection
```bash
curl -X POST http://localhost:8000/api/ai/scream-detected/ \
  -H "Content-Type: application/json" \
  -d '{"beacon_id":"safe:uuid:402:402","confidence_score":0.88,"description":"Scream"}'
```
**Threshold:** 0.80 | **Priority:** HIGH | **Alerts:** 3 guards

---

## Response Codes Cheat Sheet

| Code | Status | Meaning |
|------|--------|---------|
| **201** | incident_created | ✅ New incident, guards alerted |
| **200** | signal_added_to_existing | ⚠️ Merged with existing incident |
| **200** | logged_only | ℹ️ Confidence too low, logged only |
| **400** | Error | ❌ Invalid input (check beacon_id, confidence) |
| **404** | Error | ❌ Beacon not found (get valid from `/api/beacons/`) |

---

## Request Format

```json
{
  "beacon_id": "safe:uuid:403:403",      // Required - from /api/beacons/
  "confidence_score": 0.92,               // Required - 0.0 to 1.0
  "description": "Fight detected"         // Required - what was detected
}
```

---

## Response Example (201)

```json
{
  "status": "incident_created",
  "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "ai_event_id": 123,
  "signal_id": 456,
  "confidence_score": 0.92,
  "beacon_location": "Library 3F Entrance",
  "incident_priority": "Critical"
}
```

---

## Valid Beacon Examples

```
safe:uuid:403:403    (Library 3F)
safe:uuid:402:402    (Hallway 4F)
safe:uuid:401:401    (Library 4F)
test:uuid:2:2        (Test area)
```
Get full list: `GET /api/beacons/`

---

## Confidence Guidelines

### Violence (Threshold: 0.75)
| Confidence | Action |
|------------|--------|
| < 0.75 | Logged only, no incident |
| 0.75+ | **CRITICAL incident created** |

### Scream (Threshold: 0.80)
| Confidence | Action |
|------------|--------|
| < 0.80 | Logged only, no incident |
| 0.80+ | **HIGH incident created** |

---

## Python Integration

```python
import requests

def report_violence(beacon_id, confidence, description):
    return requests.post(
        'http://localhost:8000/api/ai/violence-detected/',
        json={
            'beacon_id': beacon_id,
            'confidence_score': confidence,
            'description': description
        }
    )

def report_scream(beacon_id, confidence, description):
    return requests.post(
        'http://localhost:8000/api/ai/scream-detected/',
        json={
            'beacon_id': beacon_id,
            'confidence_score': confidence,
            'description': description
        }
    )

# Usage
r = report_violence('safe:uuid:403:403', 0.92, 'Fight near library')
if r.status_code == 201:
    incident_id = r.json()['incident_id']
    print(f"Incident created: {incident_id}")
```

---

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `"beacon_id is required"` | Include beacon_id in request |
| `"Beacon ... not found"` | Use valid beacon from `/api/beacons/` |
| `"confidence_score must be 0-1"` | Use 0.92 not 92 (decimals) |
| `"description is required"` | Include description field |
| `"confidence must be between 0 and 1"` | Check value is between 0.0 and 1.0 |

---

## Success Response Codes

```
201 = New incident created (most common for real incidents)
200 = Signal merged with existing (same beacon, within 5 min)
200 = Logged only (below confidence threshold)
```

---

## Key Facts

✅ **No authentication required** (endpoints are public)  
✅ **Deduplication: 5-minute window** (same beacon = merge)  
✅ **Confidence thresholds:** Violence 0.75, Scream 0.80  
✅ **Guard alerting:** Max 3 guards, beacon-proximity based  
✅ **Incident priority:** CRITICAL (violence), HIGH (scream)  
✅ **Auto-conversation:** Guard + student messaging starts  

---

## Test Locally

```bash
# Get valid beacons
curl http://localhost:8000/api/beacons/

# Test violence detection
curl -X POST http://localhost:8000/api/ai/violence-detected/ \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "safe:uuid:403:403",
    "confidence_score": 0.92,
    "description": "Test"
  }'

# Check incident created
curl http://localhost:8000/api/incidents/ \
  -H "Authorization: Token <token>"
```

---

## Links

📖 [Full API Docs](AI_DETECTION_ENDPOINTS.md)  
🚀 [Integration Guide](AI_MODEL_INTEGRATION_GUIDE.md)  
📋 [System Overview](AI_DETECTION_SYSTEM_REFACTORED.md)  
✅ [Implementation Status](IMPLEMENTATION_COMPLETE.md)

---

## What Happens When You Call

```
POST /api/ai/violence-detected/
    ↓
✅ Validate input
    ↓
✅ Create AIEvent (logged)
    ↓
✅ Check 0.92 >= 0.75? YES
    ↓
✅ Check existing incident
    ↓
✅ Create Incident (CRITICAL)
    ↓
✅ Alert 3 guards
    ↓
✅ Return incident_id
    ↓
🔔 Guards get push notification
    ↓
📱 Guard sees incident, accepts alert
    ↓
💬 Conversation starts with student
    ↓
🏃 Guard responds to incident
```

---

## Status: Production Ready ✅

- Endpoints: ✅ Working
- Tests: ✅ Passing  
- Docs: ✅ Complete
- Integration: ✅ Ready
