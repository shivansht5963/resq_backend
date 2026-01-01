# Alert & Push Notification Flow - API Documentation

## Complete Flow: From Incident to Guard Alert to Push Notification

### 1️⃣ INCIDENT CREATION TRIGGERS ALERTS

When a new incident is created (student SOS, AI detection, panic button):

```
┌─────────────────────────────────────────┐
│ POST /api/incidents/report_sos/         │
│ POST /api/violence-detected/            │
│ POST /api/scream-detected/              │
│ POST /api/panic/                        │
└─────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│ 1. Create Incident (or find existing)   │
│ 2. Create IncidentSignal                │
│ 3. Create GuardAlerts (if no existing   │
│    assignment)                          │
│ 4. Send GUARD_ALERT Push Notifications  │
└─────────────────────────────────────────┘
```

---

## STEP 1: Student Reports SOS Emergency

### Request
```http
POST https://resq-server.onrender.com/api/incidents/report_sos/
Content-Type: application/json
Authorization: Token 0ae475f9cf39e1134b4003d17a2b1b9f47b1e386

{
  "beacon_id": "safe:uuid:403:403",
  "description": "I need help in the library main hall"
}
```

### Response (201 Created)
```json
{
  "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
  "beacon": {
    "id": "beacon-uuid-003",
    "beacon_id": "safe:uuid:403:403",
    "location_name": "Library 3F - Main Hall",
    "building": "Main Library",
    "floor": 3
  },
  "reported_by": {
    "id": "student-uuid-001",
    "full_name": "John Doe",
    "role": "STUDENT"
  },
  "status": "CREATED",
  "priority": 5,
  "description": "I need help in the library main hall",
  "location": "Library 3F - Main Hall",
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:00:00Z"
}
```

---

## STEP 2: Backend Automatically Finds Nearest Guards & Creates Alerts

**Behind the scenes:**

1. **Find Incident Beacon**: `safe:uuid:403:403` → Library 3F
2. **Search for Guards**: Use beacon proximity
   - Check guards at Library 3F (same beacon)
   - Check guards at nearby beacons (Library 4F, Hallway 4F, etc.)
   - Continue expanding radius until 3-5 guards found
3. **Skip Guards Who:**
   - Are already assigned to another incident
   - Are inactive
   - Are unavailable
4. **Create GuardAlerts** with type `ASSIGNMENT` (requires response)
5. **Send Push Notifications** to all alerted guards

---

## STEP 3: Guard Receives Push Notification

### Push Notification Sent
**Method**: Expo Push API via `exponent_server_sdk`

```python
# Backend code (automatic)
PushNotificationService.notify_guard_alert(
    expo_tokens=["ExponentPushToken[guard1...]", "ExponentPushToken[guard2...]"],
    incident_id="a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    alert_id=1,
    priority="CRITICAL",
    location="Library 3F - Main Hall"
)
```

### Push Notification Received on Guard App
```json
{
  "title": "🚨 Incoming Alert",
  "body": "CRITICAL - Library 3F - Main Hall",
  "data": {
    "type": "GUARD_ALERT",
    "incident_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "alert_id": "1",
    "priority": "CRITICAL",
    "location": "Library 3F - Main Hall"
  }
}
```

---

## STEP 4: Guard Polls for Alerts

### Request
```http
GET https://resq-server.onrender.com/api/alerts/
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a
```

### Response (200 OK)
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "incident": {
        "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "beacon_id": "safe:uuid:403:403",
        "location": "Library 3F - Main Hall",
        "priority": 5,
        "status": "CREATED"
      },
      "guard": "de88e903f2731983695f8e698a4eaa3d83d05d4a",
      "alert_type": "ASSIGNMENT",
      "status": "SENT",
      "created_at": "2025-01-01T12:00:15Z",
      "response_deadline": "2025-01-01T12:05:15Z"
    },
    {
      "id": 2,
      "incident": {
        "id": "b2c3d4e5-f6a7-48b9-c0d1-e2f3a4b5c6d7",
        "beacon_id": "safe:uuid:402:402",
        "location": "Hallway 4F",
        "priority": 4,
        "status": "CREATED"
      },
      "guard": "de88e903f2731983695f8e698a4eaa3d83d05d4a",
      "alert_type": "ASSIGNMENT",
      "status": "SENT",
      "created_at": "2025-01-01T11:55:00Z",
      "response_deadline": "2025-01-01T12:00:00Z"
    }
  ]
}
```

---

## STEP 5: Guard Accepts Alert (Takes Assignment)

### Request
```http
POST https://resq-server.onrender.com/api/alerts/1/accept/
Content-Type: application/json
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a

{}
```

### Response (200 OK)
```json
{
  "id": 1,
  "incident": {
    "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "beacon_id": "safe:uuid:403:403",
    "location": "Library 3F - Main Hall",
    "priority": 5,
    "status": "ASSIGNED",
    "conversation_id": 42
  },
  "guard": "de88e903f2731983695f8e698a4eaa3d83d05d4a",
  "alert_type": "ASSIGNMENT",
  "status": "ACCEPTED",
  "created_at": "2025-01-01T12:00:15Z",
  "accepted_at": "2025-01-01T12:01:30Z",
  "assignment": {
    "id": 10,
    "incident": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "guard_id": "guard-user-uuid",
    "is_active": true,
    "created_at": "2025-01-01T12:01:30Z"
  }
}
```

### Backend Actions (Automatic)
1. ✅ Mark alert as `ACCEPTED`
2. ✅ Create `GuardAssignment` (incident + guard)
3. ✅ Update incident status to `ASSIGNED`
4. ✅ Decline other pending alerts for same incident
5. ✅ Send push notification: "✅ Assignment Confirmed"
6. ✅ Create `Conversation` between student and guard

---

## STEP 6: Guard Declines Alert (Not Accepting)

### Request
```http
POST https://resq-server.onrender.com/api/alerts/1/decline/
Content-Type: application/json
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a

{}
```

### Response (200 OK)
```json
{
  "id": 1,
  "incident": {
    "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "beacon_id": "safe:uuid:403:403",
    "location": "Library 3F - Main Hall",
    "priority": 5,
    "status": "CREATED"
  },
  "guard": "de88e903f2731983695f8e698a4eaa3d83d05d4a",
  "alert_type": "ASSIGNMENT",
  "status": "DECLINED",
  "created_at": "2025-01-01T12:00:15Z",
  "declined_at": "2025-01-01T12:01:45Z",
  "decline_reason": null
}
```

### Backend Actions (Automatic)
1. ✅ Mark alert as `DECLINED`
2. ✅ Find next available guard via beacon proximity expansion
3. ✅ Create new alert for next guard
4. ✅ Send push notification to next guard
5. ✅ Incident still status `CREATED` (waiting for someone to accept)

---

## STEP 7: Guard Updates Location (Periodic)

**Should run every 10-15 seconds**

### Request
```http
POST https://resq-server.onrender.com/api/guards/update_location/
Content-Type: application/json
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a

{
  "nearest_beacon_id": "safe:uuid:403:403",
  "timestamp": "2025-01-01T12:01:45Z"
}
```

### Response (200 OK)
```json
{
  "id": "guard-profile-uuid",
  "user": "de88e903f2731983695f8e698a4eaa3d83d05d4a",
  "current_beacon": {
    "id": "beacon-uuid-003",
    "beacon_id": "safe:uuid:403:403",
    "location_name": "Library 3F - Main Hall"
  },
  "updated_at": "2025-01-01T12:01:45Z"
}
```

---

## STEP 8: Send/Receive Messages (Chat)

### Get Conversation
```http
GET https://resq-server.onrender.com/api/conversations/42/
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a
```

### Response (200 OK)
```json
{
  "id": 42,
  "incident": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
  "student": {
    "id": "student-uuid-001",
    "full_name": "John Doe"
  },
  "guard": {
    "id": "guard-user-uuid",
    "full_name": "Guard Sarah Smith"
  },
  "created_at": "2025-01-01T12:01:30Z",
  "updated_at": "2025-01-01T12:05:00Z",
  "message_count": 3
}
```

### Guard Sends Message to Student
```http
POST https://resq-server.onrender.com/api/conversations/42/send_message/
Content-Type: application/json
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a

{
  "content": "I'm arriving in 2 minutes. I'm near the main entrance."
}
```

### Response (201 Created)
```json
{
  "id": 101,
  "conversation": 42,
  "sender": {
    "id": "guard-user-uuid",
    "full_name": "Guard Sarah Smith",
    "role": "GUARD"
  },
  "content": "I'm arriving in 2 minutes. I'm near the main entrance.",
  "created_at": "2025-01-01T12:02:00Z",
  "read": false
}
```

### Student Receives Push: "💬 New Message"
```json
{
  "title": "💬 New Message",
  "body": "Guard Sarah Smith: I'm arriving in 2 minutes...",
  "data": {
    "type": "NEW_CHAT_MESSAGE",
    "incident_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "conversation_id": "42",
    "sender": "Guard Sarah Smith"
  }
}
```

---

## Alert & Push Notification Types

| Alert Type | Priority | Alert Type | Push Title | Requires Response | When |
|-----------|----------|-----------|------------|------------------|------|
| STUDENT_SOS | 5 | ASSIGNMENT | 🚨 Incoming Alert | Yes | Student reports SOS |
| VIOLENCE (AI) | 5 | ASSIGNMENT | 🚨 Incoming Alert | Yes | AI detects violence (≥75% confidence) |
| SCREAMING (AI) | 4 | ASSIGNMENT | 🚨 Incoming Alert | Yes | AI detects scream (≥80% confidence) |
| PANIC_BUTTON | 5 | ASSIGNMENT | 🚨 Incoming Alert | Yes | ESP32 panic button pressed |
| INCIDENT_ESCALATED | ↑ | BROADCAST | ⚠️ Incident Escalated | No | Priority increased |
| ASSIGNMENT_CONFIRMED | — | — | ✅ Assignment Confirmed | — | Guard accepts alert |
| NEW_CHAT_MESSAGE | — | — | 💬 New Message | — | New message in conversation |

---

## Error Responses

### Invalid Token Format
```http
POST https://resq-server.onrender.com/api/alerts/1/accept/
Authorization: Token invalid-token
```

**Response (401 Unauthorized)**
```json
{
  "detail": "Invalid token."
}
```

### Alert Not Found
```http
POST https://resq-server.onrender.com/api/alerts/999/accept/
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a
```

**Response (404 Not Found)**
```json
{
  "detail": "Not found."
}
```

### Guard Can't Accept BROADCAST Alert
```http
POST https://resq-server.onrender.com/api/alerts/5/accept/
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a
```

**Response (400 Bad Request)**
```json
{
  "error": "Only ASSIGNMENT alerts can be accepted"
}
```

### Invalid Beacon ID
```http
POST https://resq-server.onrender.com/api/incidents/report_sos/
Authorization: Token 0ae475f9cf39e1134b4003d17a2b1b9f47b1e386

{
  "beacon_id": "invalid-beacon-id",
  "description": "Help needed"
}
```

**Response (400 Bad Request)**
```json
{
  "beacon_id": ["Invalid or inactive beacon: invalid-beacon-id"]
}
```

---

## Real-World Scenario: Complete Flow

### Timeline
```
T+0s:   Student presses SOS at Library 3F
        ├─ Incident created (ID: abc123)
        ├─ 3 nearest guards alerted
        └─ Push sent to guards

T+3s:   Guard #1 receives push notification
        └─ Guard opens app and sees alert

T+5s:   Guard #1 accepts alert
        ├─ Assignment created
        ├─ Push: "✅ Assignment Confirmed"
        ├─ Other alerts auto-declined
        └─ Incident status: ASSIGNED

T+10s:  Guard #1 sends location update
        └─ Location: Library 4F (approaching)

T+15s:  Guard #1 sends message to student
        ├─ "I'm on my way, ETA 2 minutes"
        └─ Student receives push: "💬 New Message"

T+60s:  Guard #1 arrives and resolves incident
        └─ Incident status: RESOLVED
```

---

## Database Operations Summary

### GuardAlert Fields
```
- id: Integer (PK)
- incident: ForeignKey → Incident
- guard: ForeignKey → User (GUARD role)
- alert_type: ASSIGNMENT | BROADCAST
- status: SENT | ACCEPTED | DECLINED | AUTO_DECLINED | EXPIRED
- response_deadline: DateTime (5 min from creation)
- created_at: DateTime
- accepted_at: DateTime (nullable)
- declined_at: DateTime (nullable)
- is_read: Boolean (default False)
```

### GuardAssignment Fields
```
- id: Integer (PK)
- incident: ForeignKey → Incident
- guard: ForeignKey → User (GUARD role)
- is_active: Boolean (default True)
- created_at: DateTime
- updated_at: DateTime
```

### Key Constraints
- **Only one active assignment per incident**
- **Alerts only created if no active assignment exists**
- **Response deadline: 5 minutes from alert creation**
- **Auto-decline if guard doesn't respond within deadline**

---

## Testing Checklist

✅ Student SOS creates incident and alerts guards
✅ Guards receive push notifications (🚨 Incoming Alert)
✅ Guard can accept alert
✅ Accept creates assignment and marks incident ASSIGNED
✅ Guard can decline alert
✅ Decline alerts next guard in proximity radius
✅ Guard receives "✅ Assignment Confirmed" push
✅ Guard can send messages
✅ Student receives "💬 New Message" push
✅ Guard can poll for alerts repeatedly
✅ Multiple signals on same incident dedup correctly
✅ AI detection (violence/scream) triggers alerts
✅ Panic button triggers CRITICAL alerts
✅ Broadcast alerts for escalations

---

## Push Notification SDK

**Using**: `exponent_server_sdk>=0.3.0`

All push notifications are sent via Expo Push API with automatic:
- Token validation (must start with "ExponentPushToken")
- Error handling (DeviceNotRegisteredError, PushServerError)
- Batch processing (multiple notifications in one request)
- Response validation

See `accounts/push_notifications.py` for implementation.

---

## Production Deployment Notes

✅ All endpoints require authentication (Token)
✅ Role-based access control enforced
✅ Beacon proximity DB queries optimized with indexes
✅ Push notifications logged for debugging
✅ Incident deduplication with 5-minute window
✅ Alert response deadline auto-escalation
✅ Conversation history persisted
✅ Guard location updates tracked
✅ All timestamps in UTC (Z format)

**Ready for production use.**
