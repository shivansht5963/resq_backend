# Guard Alert & Assignment System Design

## Current Implementation

### 1. **GUARD ALERT FLOW** 
When a student reports an emergency, the system:

#### Step 1: Create Incident with Signal
- **API**: `POST /api/incidents/report_sos/` or `POST /api/incidents/report/`
- **Creates**: New `Incident` (status=CREATED) + `IncidentSignal`
- **Dedup Window**: 5 minutes - if incident exists at same beacon within 5 min, add signal to existing incident instead

#### Step 2: Alert Nearest Guards
- **Function**: `alert_guards_for_incident()` (incidents/services.py)
- **Method**: Beacon-proximity based search (not GPS)
  - Searches incident beacon for nearby guards
  - Expands to nearby beacons (priority order) if not enough guards found
  - Sends to max 3 nearest available guards
- **Creates**: `GuardAlert` objects (status=SENT) ranked by proximity
- **Ranking**: Guard closest to incident beacon gets priority_rank=1

---

### 2. **GUARD ALERT MODEL**
```
GuardAlert
├── incident (FK)
├── guard (FK) 
├── assignment (1-to-1) ← Created when acknowledged
├── status: [SENT, ACKNOWLEDGED, DECLINED, EXPIRED]
├── distance_km (beacon-based, always 0.0 currently)
├── priority_rank (1=nearest, 2=next, etc)
├── alert_sent_at
└── updated_at
```

---

### 3. **GUARD ALERT APIs**

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `GET /api/alerts/` | GET | List alerts sent to current guard (SENT status first) | Guard |
| `GET /api/alerts/{id}/` | GET | Get alert details + incident info | Guard |
| `POST /api/alerts/{id}/acknowledge/` | POST | Guard accepts alert, creates assignment | Guard |
| `POST /api/alerts/{id}/decline/` | POST | Guard rejects, tries next guard | Guard |

**Example Response (GET /api/alerts/):**
```json
{
  "id": 17,
  "incident": {
    "id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
    "beacon": {
      "location_name": "Library 3F",
      "building": "Central Library"
    },
    "status": "CREATED",
    "priority": 3
  },
  "status": "SENT",
  "priority_rank": 1,
  "assignment": null
}
```

---

### 4. **GUARD ASSIGNMENT FLOW**

#### Acknowledge Alert
- **API**: `POST /api/alerts/{alertId}/acknowledge/`
- **Action**: Guard says "I'm responding"
- **Steps**:
  1. Update alert: status = ACKNOWLEDGED
  2. Create/Update `GuardAssignment` (guard → incident)
  3. Update Incident: status = CREATED → ASSIGNED
  4. Mark other alerts as EXPIRED (this guard is now assigned)
  5. Create `Conversation` between student & guard for messaging

#### Decline Alert
- **API**: `POST /api/alerts/{alertId}/decline/`
- **Action**: Guard says "I'm busy"
- **Steps**:
  1. Update alert: status = DECLINED
  2. **Continue beacon-proximity search** for next available guard
  3. Create new GuardAlert for next guard (doesn't restart)
  4. If no more guards: log warning, incident stays in CREATED state

---

### 5. **GUARD ASSIGNMENT MODEL**
```
GuardAssignment
├── incident (FK)
├── guard (FK)
├── assigned_at
├── is_active: True/False
└── updated_at

Constraint: Only ONE active assignment per incident
```

**Assignment APIs:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/assignments/` | GET | Guards see only their assignments |
| `POST /api/assignments/{id}/deactivate/` | POST | Guard or admin deactivates |

---

### 6. **INCIDENT STATUS UPDATES**

| Status | When | What Happens |
|--------|------|--------------|
| **CREATED** | Student reports incident | Alerts are sent to guards (3 max) |
| **ASSIGNED** | Guard acknowledges alert | Assignment created, conversation starts |
| **IN_PROGRESS** | (Not auto-set currently) | Can be updated by admin via PATCH |
| **RESOLVED** | `POST /api/incidents/{id}/resolve/` | Guard or student marks complete, assignments deactivated |

---

### 7. **LOCATION UPDATE** (Guard Tracking)
- **API**: `POST /api/guards/update_location/`
- **Purpose**: Guard sends current beacon position (every 10-15s)
- **Updates**: `GuardProfile.current_beacon` + `last_beacon_update`
- **Used by**: Beacon-proximity search to find "nearest" guards

---

## What SHOULD Be There (Improvements)

### ❌ **Missing Features**

1. **ACCEPT_RESPONSE** status for GuardAlert
   - Currently: SENT → ACKNOWLEDGED (immediate)
   - Better: SENT → ACCEPT_RESPONSE (waiting for response) → ACKNOWLEDGED
   - Reason: Differentiate "I saw it" from "I'm on the way"

2. **ETA/Distance Tracking**
   - GuardAlert.distance_km is always 0.0
   - Should calculate real beacon distance or walking distance
   - Should track ETA for student visibility

3. **Incident Status: IN_PROGRESS Auto-Trigger**
   - Currently only set manually via PATCH
   - Should auto-set when guard sends first message to student
   - Better UX for tracking response time

4. **Guard Unavailability Reasons**
   - When guard declines, no reason captured
   - Should log: "Busy", "Too far", "Manual decline", etc
   - Helps with analytics and re-alerting

5. **Multi-Assignment Support**
   - Currently: 1 guard per incident
   - Some incidents need 2-3 guards (brawls, multiple victims)
   - Current code enforces single assignment, needs redesign

6. **Alert Timeout/Auto-Escalation**
   - Alert sent but guard never responds (no ACK/DECLINE)
   - Should auto-expire after 30-60s and try next guard
   - Current: Guards can ignore alerts indefinitely

7. **Response Time Metrics**
   - Don't track: alert_sent → acknowledge time
   - Should calculate for analytics & SLA monitoring
   - Add: acknowledged_at, first_message_at timestamps

8. **Incident Priority-Based Alert Limits**
   - CRITICAL incidents: alert 5+ guards
   - HIGH: alert 3
   - MEDIUM: alert 1-2
   - Currently hardcoded to max 3

9. **Guard Capability/Skills**
   - All guards treated equally
   - Should assign based on: first aid certified, incident type, etc

10. **Conversation Auto-Start**
    - Currently created on assignment
    - Should auto-send "Guard is on the way" system message

---

## Database Indexes Performance

**Good:**
- ✅ GuardAlert: `(incident, status)` with priority_rank
- ✅ GuardAssignment: `(incident, is_active)` 
- ✅ Incident: `(beacon, status, -created_at)`

**Should Add:**
- Alert lookup by guard + status: `GuardAlert(guard, status)`
- Assignment active lookup: `GuardAssignment(is_active, assigned_at)`

---

## Summary Table

| Component | Current | Status |
|-----------|---------|--------|
| Guard Alert Creation | ✅ Working | Beacon-proximity working |
| Guard Alert List | ✅ Working | Shows SENT alerts first |
| Acknowledge Alert | ✅ Working | Creates assignment |
| Decline Alert | ✅ Working | Continues search |
| Incident Resolution | ✅ Working | Simple status update |
| Location Updates | ✅ Working | Beacon tracking |
| Multi-Guard Assignment | ❌ Missing | Only 1 guard/incident |
| Alert Timeout | ❌ Missing | No auto-escalation |
| Response Metrics | ❌ Missing | No timing data |
| Guard Skills | ❌ Missing | All guards equal |

