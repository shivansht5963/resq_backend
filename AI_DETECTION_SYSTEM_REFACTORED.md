# AI Detection System Refactored - Summary

## ✅ What Was Done

### 1. **New Signal Types Added to IncidentSignal Model**
```python
VIOLENCE_DETECTED = "VIOLENCE_DETECTED", "Violence Detected"
SCREAM_DETECTED = "SCREAM_DETECTED", "Scream Detected"
```
- Kept legacy `AI_VISION` and `AI_AUDIO` for backward compatibility
- New types map to specific high-priority incident triggers

### 2. **New Event Types Added to AIEvent Model**
```python
VIOLENCE = "VIOLENCE", "Violence Detected"
SCREAM = "SCREAM", "Scream Detected"
```
- Kept legacy `VISION` and `AUDIO` types

### 3. **Two New Dedicated API Endpoints**

#### `/api/ai/violence-detected/` (POST)
- **Purpose:** Detect fights, physical violence
- **Priority:** CRITICAL
- **Confidence Threshold:** 0.75 (75%)
- **Request:**
  ```json
  {
    "beacon_id": "safe:uuid:403:403",
    "confidence_score": 0.92,
    "description": "Fight detected near library entrance"
  }
  ```
- **Creates:** Incident with CRITICAL priority + Alerts 3 nearest guards

#### `/api/ai/scream-detected/` (POST)
- **Purpose:** Detect screaming, crying
- **Priority:** HIGH
- **Confidence Threshold:** 0.80 (80%)
- **Request:**
  ```json
  {
    "beacon_id": "safe:uuid:402:402",
    "confidence_score": 0.88,
    "description": "Loud screaming from dormitory"
  }
  ```
- **Creates:** Incident with HIGH priority + Alerts 3 nearest guards

### 4. **Updated Priority Escalation Logic**
```python
Priority Map:
├─ PANIC_BUTTON → CRITICAL
├─ VIOLENCE_DETECTED → CRITICAL (new)
├─ SCREAM_DETECTED → HIGH (new)
├─ AI_AUDIO (legacy) → HIGH
├─ AI_VISION (legacy) → MEDIUM
└─ STUDENT_SOS → MEDIUM
```

### 5. **Kept Legacy Endpoint for Backward Compatibility**
`/api/ai-detection/` still works with:
- New types: `VIOLENCE`, `SCREAM`
- Old types: `VISION` (maps to VIOLENCE), `AUDIO` (maps to SCREAM)
- Auto-maps to appropriate thresholds

---

## 📊 API Endpoint Comparison

| Feature | Violence Endpoint | Scream Endpoint | Legacy Endpoint |
|---------|-------------------|-----------------|-----------------|
| URL | `/api/ai/violence-detected/` | `/api/ai/scream-detected/` | `/api/ai-detection/` |
| Priority | CRITICAL | HIGH | Depends on type |
| Threshold | 0.75 | 0.80 | 0.75 / 0.80 |
| Beacon ID | ✅ Required | ✅ Required | ✅ Required |
| Confidence | ✅ Required | ✅ Required | ✅ Required |
| Description | ✅ Required | ✅ Required | ⭕ Optional |
| Guards Alerted | ✅ Yes (3 max) | ✅ Yes (3 max) | ✅ Yes (3 max) |
| Dedup Window | 5 minutes | 5 minutes | 5 minutes |

---

## 🔄 Flow Diagram

```
AI Model Detects Violence/Scream
    ↓
POST /api/ai/{violence|scream}-detected/
    ↓
┌─────────────────────────────────────────────────────┐
│ 1. Validate Input                                    │
│    ├─ beacon_id (required)                          │
│    ├─ confidence_score (required, 0.0-1.0)          │
│    └─ description (required)                        │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ 2. Create AIEvent (always, for audit trail)         │
│    ├─ event_type: VIOLENCE or SCREAM               │
│    ├─ confidence_score: (0.92)                      │
│    └─ details: {description, raw_confidence}       │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ 3. Check Confidence vs Threshold                    │
│    ├─ VIOLENCE: 0.75 required                       │
│    └─ SCREAM: 0.80 required                         │
└─────────────────────────────────────────────────────┘
    ↓
 ┌─ Below? ─→ Return "logged_only" (200 OK)
 │
 └─ Met? ──→ Continue
    ↓
┌─────────────────────────────────────────────────────┐
│ 4. Check Existing Incident (5-min, same beacon)    │
│    ├─ Found? → Add signal to existing              │
│    │           Return "signal_added_to_existing"   │
│    └─ Not found? → Create new incident             │
│                    Return "incident_created"       │
└─────────────────────────────────────────────────────┘
    ↓ (if NEW incident)
┌─────────────────────────────────────────────────────┐
│ 5. Alert Guards                                      │
│    ├─ Find 3 nearest guards (beacon-proximity)     │
│    ├─ Create GuardAlerts (SENT status)             │
│    └─ Send FCM push notifications                  │
└─────────────────────────────────────────────────────┘
    ↓
Response to AI Server with incident_id + status
```

---

## 📝 Response Examples

### Success (New Incident Created - 201)
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

### Success (Signal Added to Existing - 200)
```json
{
  "status": "signal_added_to_existing",
  "ai_event_id": 124,
  "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "signal_id": 457,
  "confidence_score": 0.88,
  "beacon_location": "Library 3F Entrance",
  "incident_status": "ASSIGNED",
  "incident_priority": "Critical"
}
```

### Below Threshold (200)
```json
{
  "status": "logged_only",
  "ai_event_id": 125,
  "message": "Confidence 0.65 below threshold 0.75"
}
```

### Error (400)
```json
{
  "error": "confidence_score must be between 0.0 and 1.0"
}
```

### Error (404)
```json
{
  "error": "Beacon safe:uuid:999:999 not found or inactive"
}
```

---

## 🔐 Security & Design Notes

### 1. **AllowAny Permission**
- Both endpoints don't require authentication
- Why? AI models call from external server (can't do auth)
- Security: Validate beacon_id exists + confidence range

### 2. **Mandatory Description Field**
- Unlike legacy `/api/ai-detection/`, description is **required**
- Provides context to guards for emergency response
- Helps with incident analysis/audit

### 3. **Confidence Thresholds**
- **Violence: 0.75** - Lower threshold (more sensitive)
  - False positives less harmful than misses
  - Guards will investigate anyway
- **Scream: 0.80** - Higher threshold (more specific)
  - Screams can be false (laughter, excitement)
  - Need higher confidence to reduce false alerts

### 4. **Priority Levels**
- **VIOLENCE → CRITICAL** - Highest urgency
- **SCREAM → HIGH** - Still high but slightly less urgent
- System may escalate MEDIUM→HIGH/CRITICAL if signal added

### 5. **Deduplication**
- 5-minute window prevents alert spam
- Multiple violence/scream signals at same location → 1 incident
- Guards not re-alerted on new signals (already responding)

---

## 🧪 Testing

### Quick Test (cURL)
```bash
# Violence Detection
curl -X POST "http://localhost:8000/api/ai/violence-detected/" \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "safe:uuid:403:403",
    "confidence_score": 0.92,
    "description": "Test violence detection"
  }'

# Scream Detection
curl -X POST "http://localhost:8000/api/ai/scream-detected/" \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "safe:uuid:402:402",
    "confidence_score": 0.88,
    "description": "Test scream detection"
  }'
```

### REST Client (test.http)
See test requests added:
- `0.5a` - Violence Detection (high confidence)
- `0.5b` - Scream Detection (high confidence)
- `0.5c` - Violence Detection (below threshold)
- `0.5d` - Scream Detection (below threshold)
- `0.5e` - Legacy endpoint test

---

## 📋 Files Modified

### Models
- `incidents/models.py` - Added `VIOLENCE_DETECTED`, `SCREAM_DETECTED` to `IncidentSignal.SignalType`
- `ai_engine/models.py` - Added `VIOLENCE`, `SCREAM` to `AIEvent.EventType`

### Views
- `ai_engine/views.py` - Added 2 new endpoints + helper function

### URLs
- `ai_engine/urls.py` - Registered new endpoints

### Services
- `incidents/services.py` - Updated priority escalation for new signal types

### Testing
- `test.http` - Added 5 AI detection test cases

### Documentation
- `AI_DETECTION_ENDPOINTS.md` - Complete API documentation
- `AI_DETECTION_SYSTEM_REFACTORED.md` - This summary

---

## 🚀 Next Steps

### If You Want to Enhance Further:

1. **Add Alert Timeout** (30-60s)
   - Auto-escalate if guard doesn't respond to alert
   - Try next guard automatically

2. **Response Time Metrics**
   - Track: alert_sent → acknowledge duration
   - Good for SLA monitoring and analytics

3. **Guard Skills Matching**
   - Assign violence incidents to trained guards first
   - Assign scream incidents to mental health first aid trained

4. **Multi-Guard Support**
   - CRITICAL incidents (violence) need 2+ guards
   - Current: 1 guard per incident

5. **Incident Status Auto-Progression**
   - Auto-set `IN_PROGRESS` when guard sends first message
   - Better real-time tracking

6. **Web Dashboard Integration**
   - Show live violence/scream detections
   - Real-time incident tracking
   - Guard response times

---

## 💾 Database Migrations

**No migrations needed** - Only added new choice values to existing CharField fields. Django doesn't require migration for adding new choices.

If deploying to production:
```bash
python manage.py makemigrations  # Check - should be empty
python manage.py migrate         # Run - should be no-op
```

---

## 📚 Related Documentation

- [Guard Alert System Design](GUARD_ALERT_SYSTEM_DESIGN.md)
- [AI Detection Endpoints](AI_DETECTION_ENDPOINTS.md)
- [API Test File](test.http) - Lines 45-80 (new AI tests)
