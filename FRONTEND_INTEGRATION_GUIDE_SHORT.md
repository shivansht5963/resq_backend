# FRONTEND INTEGRATION GUIDE (COMPACT)
**Campus Security System | Django REST Backend | React Native (Expo)**  
**Status:** ✅ Backend 100% Complete | Ready for Frontend Development

---

## 1. AUTHENTICATION

### Login
```
POST /api/auth/login/
{
  "email": "user@example.com",
  "password": "password123"
}

Response (200):
{
  "auth_token": "abc123...",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "STUDENT|GUARD|ADMIN"
}
```

### Token & User Storage (CRITICAL)
After login, **store both values securely**:

```javascript
// Secure storage (AsyncStorage on Android, SecureStore on iOS)
await SecureStorage.setItem('auth_token', response.auth_token);     // Required for ALL requests
await SecureStorage.setItem('user_id', response.user_id);           // For reference
await SecureStorage.setItem('user_role', response.role);            // For UI branching (STUDENT vs GUARD)

// Every API request must include token:
Authorization: Token abc123...
```

### Logout
```
POST /api/auth/logout/
Response (200): {"detail": "Logged out successfully."}

Then: Delete token + user_id + user_role from secure storage
```

### Token Expiration
- If 401 returned on ANY endpoint → Token invalid
- Clear all stored data
- Redirect to login screen
- User must login again

---

## 2. STUDENT APP FLOW

### Report SOS
```
POST /api/incidents/report-sos/
{
  "beacon_id": "uuid",
  "description": "I need help"
}

Response (201 - New incident):
{
  "status": "incident_created",
  "incident_id": "uuid",
  "incident": { ...full incident data }
}
```

### Poll Incident Status (5-10 sec)
```
GET /api/incidents/{incident_id}/

Returns:
{
  "id": "uuid",
  "status": "CREATED|ASSIGNED|IN_PROGRESS|RESOLVED",
  "beacon": { "location_name", "building", "floor", "latitude", "longitude" },
  "guard_assignments": [{ "guard": { "full_name", "email" }, "assigned_at" }],
  "conversation": { "id", "messages": [...] },
  "signals": [...]
}
```

### Chat
```
GET /api/conversations/{conversation_id}/messages/
POST /api/conversations/{conversation_id}/send_message/
  {"content": "message text"}
```

**Stop polling when:** `incident.status === "RESOLVED"`

---

## 3. GUARD APP FLOW

### Login (Same as Student)
```
POST /api/auth/login/
```

### Update Location (Every 10-15 sec - CRITICAL)
```
POST /api/guards/update_location/
{
  "nearest_beacon_id": "uuid",
  "timestamp": "2025-12-25T10:30:00Z"  // optional
}

Response:
{
  "status": "location_updated",
  "guard": {
    "current_beacon": { "location_name", "building", "floor", "latitude", "longitude" },
    "last_beacon_update": "...",
    "is_active": true,
    "is_available": true
  }
}
```
✅ **This is how backend finds guards for incidents. Don't skip it.**

### Poll Alerts (5-10 sec)
```
GET /api/alerts/

Returns list of:
{
  "id": 5,
  "status": "PENDING|ACKNOWLEDGED|DECLINED|EXPIRED",
  "incident": {
    "id": "uuid",
    "status": "CREATED|ASSIGNED",
    "beacon": { "location_name", "building", "floor" },
    "description": "...",
    "priority": 1-4,
    "signals": [{ "signal_type": "STUDENT_SOS", "source_user": { "full_name" } }]
  },
  "created_at": "..."
}
```

**⚠️ GuardAlert states:** Only PENDING, ACKNOWLEDGED, DECLINED, EXPIRED. Assignment is determined by `incident.status=ASSIGNED` + `GuardAssignment` record (created when guard acknowledges). Frontend must check **incident**, not alert, for assignment.

### Accept Alert
```
POST /api/alerts/{alert_id}/acknowledge/

Backend does:
  1. Creates GuardAssignment
  2. Changes incident.status: CREATED → ASSIGNED
  3. Creates Conversation
  4. Expires other pending alerts

Response:
{
  "status": "ACKNOWLEDGED",
  "assigned_at": "...",
  "incident": { "status": "ASSIGNED", "conversation": { "id": 1 } }
}
```

### Decline Alert
```
POST /api/alerts/{alert_id}/decline/

Backend searches for next guard. If found, creates new alert.

Response:
{
  "status": "DECLINED",
  "incident": { "status": "CREATED" }  // still waiting
}
```

### Chat (Same as Student)
```
GET /api/conversations/{conversation_id}/messages/
POST /api/conversations/{conversation_id}/send_message/
```

---

## 4. COMPLETE ENDPOINT TABLE

| Endpoint | Method | Auth | Purpose | Polling |
|----------|--------|------|---------|---------|
| `/api/auth/login/` | POST | ❌ | Login | — |
| `/api/auth/logout/` | POST | ✅ | Logout | — |
| `/api/incidents/` | GET | ✅ | List incidents | — |
| `/api/incidents/report-sos/` | POST | ✅ | Report emergency | — |
| `/api/incidents/{id}/` | GET | ✅ | Get full incident + chat | 5-10s |
| `/api/incidents/{id}/resolve/` | POST | ✅ | Mark resolved | — |
| `/api/beacons/` | GET | ✅ | List beacon locations | — |
| `/api/guards/` | GET | ✅ | List guards | — |
| `/api/guards/update_location/` | POST | ✅ | Update beacon | **10-15s** |
| `/api/alerts/` | GET | ✅ | Get pending alerts (states: PENDING, ACKNOWLEDGED, DECLINED, EXPIRED) | 5-10s |
| `/api/alerts/{id}/acknowledge/` | POST | ✅ | Accept alert → creates GuardAssignment | — |
| `/api/alerts/{id}/decline/` | POST | ✅ | Reject alert | — |
| `/api/assignments/` | GET | ✅ | List assignments | — |
| `/api/conversations/` | GET | ✅ | List conversations | — |
| `/api/conversations/{id}/messages/` | GET | ✅ | Get messages | 3-5s |
| `/api/conversations/{id}/send_message/` | POST | ✅ | Send message | — |
| `/api/panic/` | POST | ❌ | ESP32 panic button | — |

---

## 5. JSON SCHEMAS

### Beacon
```json
{
  "id": "uuid",
  "beacon_id": "BEACON-LIB-001",
  "uuid": "FDA50693-...",
  "major": 10001,
  "minor": 54321,
  "location_name": "Library Entrance",
  "building": "Building A",
  "floor": 1,
  "latitude": 40.1234,
  "longitude": -74.5678,
  "is_active": true
}
```

### User
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "STUDENT|GUARD|ADMIN",
  "is_active": true,
  "created_at": "2025-12-25T08:00:00Z"
}
```

### Incident
```json
{
  "id": "uuid",
  "status": "CREATED|ASSIGNED|IN_PROGRESS|RESOLVED",
  "priority": 1-4,
  "beacon": { ...beacon object },
  "description": "...",
  "first_signal_time": "...",
  "last_signal_time": "...",
  "created_at": "...",
  "guard_assignments": [
    {
      "id": 10,
      "guard": { "id", "full_name", "email" },
      "assigned_at": "...",
      "is_active": true
    }
  ],
  "conversation": {
    "id": 1,
    "created_at": "...",
    "messages": [
      {
        "id": 1,
        "sender": { "id", "full_name", "email" },
        "message_text": "I'm on my way",
        "created_at": "..."
      }
    ]
  },
  "signals": [
    {
      "id": 1,
      "signal_type": "STUDENT_SOS|AI_VISION|PANIC_BUTTON",
      "source_user": { "id", "full_name" },
      "created_at": "..."
    }
  ]
}
```

### GuardProfile
```json
{
  "user": { ...user object },
  "is_active": true,
  "is_available": true,
  "current_beacon": { ...beacon object },
  "last_beacon_update": "...",
  "last_active_at": "..."
}
```

---

## 6. POLLING STRATEGY

| Operation | Interval | When to Poll |
|-----------|----------|--------------|
| Guard location update | 10-15 sec | Always while app active |
| Poll for alerts | 5-10 sec | While waiting for alert |
| Check messages | 3-5 sec | While in chat screen |
| Check incident status | 5-10 sec | While incident active |

**Stop polling:**
- Location: Guard logs out
- Alerts: Guard has assignment AND incident status ≠ RESOLVED
- Messages & Status: incident.status === RESOLVED

**Retry Rules:**
- Network timeout → Retry after 3s
- 5xx error → Exponential backoff (3s → 6s → 12s, max 60s)
- 401/403/404/400 → Stop, don't retry

---

## 7. FRONTEND RULES (NON-NEGOTIABLE)

### ✅ FRONTEND CAN DO
- Detect nearest beacon via BLE scanning
- Store token in secure storage
- Display incident status/location/guard info
- Format timestamps and location names
- Validate email/password format
- Cache data locally for offline access

### ❌ FRONTEND MUST NOT DO

| Rule | Why |
|------|-----|
| Create multiple SOS for same incident | Backend deduplicates. Send every SOS, backend merges. |
| Decide if guard is available | Only backend knows. GuardProfile.is_available is truth. |
| Decide if incident is RESOLVED | Only guard/admin can resolve. Frontend reads status only. |
| Skip location updates | Guards MUST send beacon every 10-15s. This enables guard search. |
| Modify beacon proximity data | Backend admin handles this. Frontend is read-only. |
| Create GuardAssignment manually | Only backend auto-creates via acknowledge. Don't invent. |
| Auto-retry 401/403 errors | These mean auth/permission failed. Show login/error screen. |
| Poll after incident RESOLVED | Stop polling. Waste of bandwidth. |
| Show "next guard" before backend assigns | Wait for GuardAlert. Don't invent fallback. |

**Backend ALWAYS controls:** Guard search algorithm, incident deduplication, alert expiration, status transitions, availability checks, conversation creation.

---

## 8. ERROR HANDLING

| Status | Meaning | Action |
|--------|---------|--------|
| 200/201 | Success | Show response data |
| 400 | Bad request | Show validation error, don't retry |
| 401 | Token invalid | Clear token, go to login |
| 403 | No permission | Show "Access denied" |
| 404 | Not found | Show "Resource not found" |
| 5xx | Server error | Show retry option |

### Common Errors
- **"Invalid email or password"** → Wrong credentials, retry login
- **"User account is inactive"** → Admin disabled account
- **"Only students can report SOS"** → Wrong user role
- **"Beacon not found"** → Invalid beacon ID, user move location
- **"Token invalid"** (401) → Token expired, redirect to login

---

## 9. REQUEST/RESPONSE EXAMPLES

### SOS Report Request
```json
POST /api/incidents/report-sos/
Authorization: Token abc123...

{
  "beacon_id": "550e8400-e29b-41d4-a716-446655440000",
  "description": "I need help in the library"
}
```

### Location Update Request
```json
POST /api/guards/update_location/
Authorization: Token abc123...

{
  "nearest_beacon_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-25T10:30:15Z"
}
```

### Send Message Request
```json
POST /api/conversations/1/send_message/
Authorization: Token abc123...

{
  "content": "I'm in the main reading area"
}
```

### Alert Response
```json
GET /api/alerts/

[
  {
    "id": 5,
    "status": "PENDING",
    "incident": {
      "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "status": "CREATED",
      "priority": 3,
      "beacon": {
        "location_name": "Library Entrance",
        "building": "Building A",
        "floor": 1
      },
      "description": "I need help",
      "signals": [{
        "signal_type": "STUDENT_SOS",
        "source_user": { "full_name": "John Doe" }
      }]
    },
    "created_at": "2025-12-25T10:30:05Z"
  }
]
```

---

## 10. QUICK REFERENCE: STUDENT VS GUARD

| Action | Student | Guard |
|--------|---------|-------|
| Login | ✅ | ✅ |
| Update location | ❌ | ✅ (10-15s) |
| Report SOS | ✅ | ❌ |
| Poll alerts | ❌ | ✅ (5-10s) |
| Accept/decline alert | ❌ | ✅ |
| Send/receive chat | ✅ | ✅ |
| View incident status | ✅ | ✅ |
| Resolve incident | ❌ | ✅ |

---

## 11. INCIDENT STATUS FLOW

```
CREATED
  ↓ (Guard accepts alert via acknowledge)
ASSIGNED
  ↓ (Guard arrives and starts response)
IN_PROGRESS
  ↓ (Guard completes response)
RESOLVED (polling stops)
```

Student can see this status change via polling.
Guard creates this status change via API actions.

---

## 12. IMPLEMENTATION CHECKLIST

- [ ] Login screen (email + password)
- [ ] Secure token storage
- [ ] Token attached to ALL requests
- [ ] Logout functionality (delete token)
- [ ] BLE beacon detection (for students & guards)
- [ ] **Guard: Location update every 10-15s** (non-negotiable)
- [ ] **Guard: Alert polling every 5-10s**
- [ ] Student: SOS report screen
- [ ] Student: Incident status polling (5-10s)
- [ ] Chat screen (fetch messages 3-5s, send messages)
- [ ] Error handling (401 → login, others → show message)
- [ ] Stop polling when incident.status = RESOLVED
- [ ] Accept/decline alert buttons (guards)

---

## SUPPORT

Backend is production-ready. All endpoints tested.

If frontend encounters issues:
- Check token is being sent
- Check beacon ID is valid UUID
- Check user role (student/guard/admin)
- Read response JSON error messages

Trust backend. It tells you what's wrong.

---

**Backend Version:** COMPLETE & TESTED ✅  
**Date:** December 25, 2025  
**Size:** ~550 lines | Full details preserved
