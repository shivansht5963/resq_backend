# FRONTEND INTEGRATION GUIDE
## Campus Security & Emergency Response System
**Backend Version:** COMPLETE & PRODUCTION-READY  
**Target:** React Native (Expo) | Android-First | REST APIs Only  
**Last Updated:** December 25, 2025

---

## TABLE OF CONTENTS
1. [Authentication Contract](#1-authentication-contract)
2. [Student App Flow](#2-student-app-flow)
3. [Guard App Flow](#3-guard-app-flow)
4. [Admin Dashboard (Optional)](#4-admin-dashboardoptional)
5. [Complete API Endpoint Summary](#5-complete-api-endpoint-summary)
6. [Polling Strategy](#6-polling-strategy)
7. [Frontend Rules (Non-Negotiable)](#7-frontend-rules-non-negotiable)
8. [Error Handling Guide](#8-error-handling-guide)
9. [Request/Response JSON Format Reference](#9-requestresponse-json-format-reference)

---

## 1. AUTHENTICATION CONTRACT

### 1.1 Login Endpoint

**Endpoint:** `POST /api/auth/login/`

**Request Format:**
```json
{
  "email": "student@example.com",
  "password": "password123"
}
```

**Success Response (200 OK):**
```json
{
  "auth_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "STUDENT"
}
```

**Error Response (400 Bad Request):**
```json
{
  "non_field_errors": ["Invalid email or password."]
}
```

**Error Response (401 Inactive Account):**
```json
{
  "non_field_errors": ["User account is inactive."]
}
```

### 1.2 Token Storage & Attachment

**Storage Recommendation:**
- Use secure storage (AsyncStorage with encryption or SecureStore in React Native)
- Key name: `auth_token`
- Also store `user_id` and `role` for offline reference

**How to Attach Token to Requests:**
```
Authorization: Token a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**Example Header:**
```
GET /api/incidents/
Authorization: Token a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
Content-Type: application/json
```

### 1.3 Logout

**Endpoint:** `POST /api/auth/logout/`

**Headers Required:**
```
Authorization: Token <token_key>
```

**Success Response (200 OK):**
```json
{
  "detail": "Logged out successfully."
}
```

**Action:** 
- Delete token from secure storage
- Clear all cached data
- Navigate to login screen

### 1.4 Token Expiration & Error Handling

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| **401 Unauthorized** | Token invalid/expired | Clear token, redirect to login |
| **403 Forbidden** | User lacks permission | Show error, don't retry |
| **400 Bad Request** | Invalid request payload | Fix request, show user error |
| **500 Server Error** | Backend crash | Show retry option |

**Global Interceptor Rule:**
- If ANY endpoint returns 401, immediately show login screen
- Don't retry 401 errors

---

## 2. STUDENT APP FLOW

### 2.1 Student User Profile
Students can:
- Report SOS emergencies
- View their incident
- Chat with assigned guard
- Track incident status

### 2.2 Step-by-Step: Report SOS Emergency

**Requirement:** Student must be near a beacon (app detects beacon via iBeacon/Eddystone)

**Flow:**
```
1. Student detects nearest beacon (via BLE scanning)
2. Student taps "Report Emergency" button
3. Send SOS to backend with beacon ID
4. Backend creates/merges Incident
5. Backend automatically alerts nearby guards
6. Student sees incident created
7. Student polls for:
   - Incident status (Is a guard assigned?)
   - Chat messages (Can I contact the guard?)
```

### 2.3 Report SOS API

**Endpoint:** `POST /api/incidents/report-sos/`

**Headers:**
```
Authorization: Token <token_key>
Content-Type: application/json
```

**Request Format:**
```json
{
  "beacon_id": "550e8400-e29b-41d4-a716-446655440000",
  "description": "I need help in the library"
}
```

**Success Response (201 Created - New Incident):**
```json
{
  "status": "incident_created",
  "incident_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "signal_id": 1,
  "incident": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "CREATED",
    "priority": 2,
    "beacon": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "location_name": "Library Entrance",
      "building": "Building A",
      "floor": 1,
      "latitude": 40.123,
      "longitude": -74.456
    },
    "description": "I need help in the library",
    "first_signal_time": "2025-12-25T10:30:00Z",
    "last_signal_time": "2025-12-25T10:30:00Z",
    "created_at": "2025-12-25T10:30:00Z",
    "guard_assignments": [],
    "conversation": null,
    "signals": [
      {
        "id": 1,
        "signal_type": "STUDENT_SOS",
        "source_user": {
          "id": "user-uuid",
          "full_name": "John Doe",
          "email": "john@example.com"
        },
        "created_at": "2025-12-25T10:30:00Z"
      }
    ]
  }
}
```

**Success Response (200 OK - Signal Added to Existing Incident):**
```json
{
  "status": "signal_added_to_existing",
  "incident_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "signal_id": 2,
  "incident": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "CREATED",
    "priority": 2,
    "...": "..."
  }
}
```

**Error Response (403 Forbidden - Not a Student):**
```json
{
  "error": "Only students can report SOS"
}
```

**Error Response (400 Bad Request - Invalid Beacon):**
```json
{
  "error": "Beacon not found"
}
```

### 2.4 Backend Guarantees After SOS

✅ **Guaranteed:**
1. Incident created with `status = "CREATED"`
2. IncidentSignal created linking to student
3. Guards automatically alerted (via GuardAlert)
4. Incident visible to student in `/api/incidents/` list
5. Conversation created automatically for chat

❌ **NOT guaranteed (yet):**
- Guard will accept (depends on guard availability)
- Guard will arrive immediately

### 2.5 Student Polling: Check Incident Status

**Endpoint:** `GET /api/incidents/{incident_id}/`

**Headers:**
```
Authorization: Token <token_key>
```

**Response (200 OK):**
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "CREATED",  // Can be: CREATED → ASSIGNED → IN_PROGRESS → RESOLVED
  "priority": 2,
  "beacon": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "location_name": "Library Entrance",
    "building": "Building A",
    "floor": 1
  },
  "description": "I need help in the library",
  "first_signal_time": "2025-12-25T10:30:00Z",
  "last_signal_time": "2025-12-25T10:30:00Z",
  "created_at": "2025-12-25T10:30:00Z",
  "guard_assignments": [
    {
      "id": 5,
      "guard": {
        "id": "guard-uuid",
        "full_name": "Officer Mike",
        "email": "mike@example.com"
      },
      "assigned_at": "2025-12-25T10:31:00Z",
      "is_active": true
    }
  ],
  "conversation": {
    "id": 1,
    "created_at": "2025-12-25T10:31:00Z",
    "messages": [
      {
        "id": 1,
        "sender": {
          "id": "guard-uuid",
          "full_name": "Officer Mike",
          "email": "mike@example.com"
        },
        "message_text": "I'm on my way",
        "created_at": "2025-12-25T10:31:30Z"
      }
    ]
  },
  "signals": [
    {
      "id": 1,
      "signal_type": "STUDENT_SOS",
      "source_user": {
        "id": "user-uuid",
        "full_name": "John Doe",
        "email": "john@example.com"
      },
      "created_at": "2025-12-25T10:30:00Z"
    }
  ]
}
```

### 2.6 Student Polling: Check Chat Messages

**Endpoint:** `GET /api/conversations/{conversation_id}/messages/`

**Headers:**
```
Authorization: Token <token_key>
```

**Response (200 OK):**
```json
{
  "conversation_id": 1,
  "incident_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "message_count": 3,
  "messages": [
    {
      "id": 1,
      "sender": {
        "id": "guard-uuid",
        "full_name": "Officer Mike",
        "email": "mike@example.com"
      },
      "message_text": "I'm on my way",
      "created_at": "2025-12-25T10:31:30Z"
    },
    {
      "id": 2,
      "sender": {
        "id": "student-uuid",
        "full_name": "John Doe",
        "email": "john@example.com"
      },
      "message_text": "Thank you!",
      "created_at": "2025-12-25T10:31:45Z"
    }
  ]
}
```

### 2.7 Student Send Chat Message

**Endpoint:** `POST /api/conversations/{conversation_id}/send_message/`

**Headers:**
```
Authorization: Token <token_key>
Content-Type: application/json
```

**Request:**
```json
{
  "content": "I'm in the main reading area"
}
```

**Response (201 Created):**
```json
{
  "id": 3,
  "sender": {
    "id": "student-uuid",
    "full_name": "John Doe",
    "email": "john@example.com"
  },
  "message_text": "I'm in the main reading area",
  "created_at": "2025-12-25T10:32:00Z"
}
```

### 2.8 When Is Incident Considered "Closed"?

An incident is **RESOLVED** when:
1. Guard or admin marks it as `RESOLVED`
2. Status changes from `IN_PROGRESS` → `RESOLVED`
3. All active assignments are deactivated
4. Student can no longer send messages (conversation closed)

**Frontend Action:**
- If incident status = `RESOLVED`, show "Incident Closed" screen
- Allow student to rate guard or provide feedback (optional)
- Disable message sending

### 2.9 Student Polling Frequencies

| Event | Endpoint | Interval | When to Poll |
|-------|----------|----------|--------------|
| **Check Status** | `GET /api/incidents/{id}/` | 5-10 sec | While status ≠ RESOLVED |
| **Check Messages** | `GET /api/conversations/{id}/messages/` | 3-5 sec | While in chat screen |
| **Stop Polling** | — | — | Status = RESOLVED |

---

## 3. GUARD APP FLOW

### 3.1 Guard User Profile
Guards can:
- Login with email/password
- Update location (beacon scanning)
- Receive alerts for new incidents
- Accept/decline alerts
- Chat with student
- Mark incident as in progress / resolved

### 3.2 Step-by-Step: Guard Login & Initialization

**Flow:**
```
1. Guard logs in with email/password
2. Backend validates credentials, returns auth_token
3. Frontend stores token in secure storage
4. Frontend detects guard has GuardProfile (backend-verified)
5. Start periodic location updates (every 10-15 seconds)
6. Start polling for alerts
7. Show guard home screen
```

### 3.3 Guard Login

**Endpoint:** `POST /api/auth/login/`

**Request:**
```json
{
  "email": "guard@example.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "auth_token": "abcd1234efgh5678ijkl9012mnop3456",
  "user_id": "guard-uuid-here",
  "role": "GUARD"
}
```

### 3.4 Step-by-Step: Guard Location Updates (Critical)

**Requirement:** Guard app must run BLE beacon scanning in background

**Flow:**
```
1. Start app → Start BLE beacon scanning
2. Every 10-15 seconds, detect nearest beacon UUID:major:minor
3. Send beacon ID to update_location endpoint
4. Backend stores in GuardProfile.current_beacon
5. Backend uses this for guard search when incident occurs
6. Continue scanning until guard logs out
```

### 3.5 Guard Update Location API

**Endpoint:** `POST /api/guards/update_location/`

**Headers:**
```
Authorization: Token <token_key>
Content-Type: application/json
```

**Request Format:**
```json
{
  "nearest_beacon_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-25T10:30:15Z"
}
```
*(timestamp is optional - backend uses server time if omitted)*

**Response (200 OK):**
```json
{
  "status": "location_updated",
  "guard": {
    "user": {
      "id": "guard-uuid",
      "full_name": "Officer Mike",
      "email": "mike@example.com",
      "role": "GUARD"
    },
    "is_active": true,
    "is_available": true,
    "current_beacon": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "location_name": "Library Entrance",
      "building": "Building A",
      "floor": 1,
      "latitude": 40.123,
      "longitude": -74.456
    },
    "last_beacon_update": "2025-12-25T10:30:15Z",
    "last_active_at": "2025-12-25T10:30:15Z"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "nearest_beacon_id": ["Invalid UUID format"]
}
```

**Idempotency:** This endpoint is **safe to call repeatedly**. Same beacon_id sent multiple times = no problem.

### 3.6 Step-by-Step: Guard Receives Alert

**Backend Automatically Sends Alert When:**
1. Student/ESP32 reports SOS at Beacon X
2. Backend searches for guards near Beacon X
3. If guard found, GuardAlert is created with status="PENDING"

**Guard Polling Mechanism:**

**Endpoint:** `GET /api/alerts/?ordering=-created_at`

**Headers:**
```
Authorization: Token <token_key>
```

**Response (200 OK - List of alerts):**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 5,
      "status": "PENDING",
      "incident": {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "status": "CREATED",
        "priority": 3,
        "beacon": {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "location_name": "Library Entrance",
          "building": "Building A",
          "floor": 1,
          "latitude": 40.123,
          "longitude": -74.456
        },
        "description": "I need help",
        "first_signal_time": "2025-12-25T10:30:00Z",
        "guard_assignments": [],
        "signals": [
          {
            "id": 1,
            "signal_type": "STUDENT_SOS",
            "source_user": {
              "full_name": "John Doe"
            }
          }
        ]
      },
      "created_at": "2025-12-25T10:30:05Z",
      "acknowledged_at": null,
      "assigned_at": null
    }
  ]
}
```

**Alert Status Values:**
- `PENDING` → Guard hasn't seen the alert yet
- `ACKNOWLEDGED` → Guard tapped "Accept"
- `DECLINED` → Guard tapped "Decline"
- `ASSIGNED` → Guard accepted, assignment created
- `EXPIRED` → Another guard accepted, this alert is old

### 3.7 Guard Acknowledge Alert (Accept)

**Endpoint:** `POST /api/alerts/{alert_id}/acknowledge/`

**Headers:**
```
Authorization: Token <token_key>
```

**What Backend Does:**
1. Creates GuardAssignment (incident → this guard)
2. Changes incident status: `CREATED` → `ASSIGNED`
3. Expires other pending alerts for this incident
4. Creates Conversation for chat
5. Returns updated alert

**Response (200 OK):**
```json
{
  "id": 5,
  "status": "ACKNOWLEDGED",
  "incident": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "ASSIGNED",
    "guard_assignments": [
      {
        "id": 10,
        "guard": {
          "id": "guard-uuid",
          "full_name": "Officer Mike",
          "email": "mike@example.com"
        },
        "assigned_at": "2025-12-25T10:30:30Z",
        "is_active": true
      }
    ],
    "conversation": {
      "id": 1,
      "created_at": "2025-12-25T10:30:30Z",
      "messages": []
    }
  },
  "acknowledged_at": "2025-12-25T10:30:30Z",
  "assigned_at": "2025-12-25T10:30:30Z"
}
```

**Frontend Action After Acknowledge:**
1. Show "You accepted the alert!" message
2. Get `conversation_id` from response
3. Enable chat screen
4. Show incident details + student info
5. Start polling: incident status + chat messages

### 3.8 Guard Decline Alert (Reject)

**Endpoint:** `POST /api/alerts/{alert_id}/decline/`

**Headers:**
```
Authorization: Token <token_key>
```

**What Backend Does:**
1. Marks alert as `DECLINED`
2. Searches for next available guard (expanding-radius)
3. If found: creates new GuardAlert for next guard
4. If not found: logs "No more guards available"
5. Incident remains `CREATED` (waiting for acceptance)

**Response (200 OK):**
```json
{
  "id": 5,
  "status": "DECLINED",
  "incident": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "CREATED",
    "guard_assignments": []
  },
  "declined_at": "2025-12-25T10:30:35Z"
}
```

**Frontend Action After Decline:**
1. Remove alert from list
2. Show "Alert declined" notification
3. Continue polling for next alert

### 3.9 Guard Chat with Student

**Send Message Endpoint:** `POST /api/conversations/{conversation_id}/send_message/`

**Headers:**
```
Authorization: Token <token_key>
Content-Type: application/json
```

**Request:**
```json
{
  "content": "I'm arriving in 2 minutes"
}
```

**Response (201 Created):**
```json
{
  "id": 4,
  "sender": {
    "id": "guard-uuid",
    "full_name": "Officer Mike",
    "email": "mike@example.com"
  },
  "message_text": "I'm arriving in 2 minutes",
  "created_at": "2025-12-25T10:31:00Z"
}
```

**Poll Messages:** `GET /api/conversations/{conversation_id}/messages/` (see Student section for format)

### 3.10 Guard Polling Frequencies

| Event | Endpoint | Interval | When to Poll |
|-------|----------|----------|--------------|
| **Update Location** | `POST /api/guards/update_location/` | 10-15 sec | While app is active (background safe) |
| **Check Alerts** | `GET /api/alerts/` | 5-10 sec | While waiting for alert |
| **Check Messages** | `GET /api/conversations/{id}/messages/` | 3-5 sec | While in chat screen |
| **Check Assignment Status** | `GET /api/incidents/{id}/` | 10 sec | While in progress |

### 3.11 When Guard Stops Polling

**Stop polling for alerts when:**
- Guard has an active assignment (`is_active=true`)

**Continue polling (incident status + chat) while:**
- Assignment is active
- Incident status ≠ `RESOLVED`

**Stop all polling when:**
- Guard logs out
- Incident status = `RESOLVED`

---

## 4. ADMIN DASHBOARD (OPTIONAL)

### 4.1 Admin Capabilities

Admins can:
- View all incidents, guards, assignments, alerts
- Create/update beacon locations
- View and manage beacon proximity relationships
- View all conversations and messages
- Manually assign/reassign guards
- Resolve incidents
- View analytics (if available)

### 4.2 Admin-Only Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/beacons/` | GET | List all beacons |
| `GET /api/incidents/` | GET | List all incidents (no filtering) |
| `GET /api/guards/` | GET | List all guards with profiles |
| `GET /api/assignments/` | GET | List all assignments |
| `GET /api/alerts/` | GET | List all alerts |
| `GET /api/conversations/` | GET | List all conversations |
| `POST /api/incidents/{id}/resolve/` | POST | Mark incident as RESOLVED |
| `POST /api/assignments/` | POST | Create assignment manually |
| `PATCH /api/assignments/{id}/` | PATCH | Update assignment |

### 4.3 What Admin Should NOT Do

❌ **Never modify via frontend UI:**
- Delete incidents directly (mark as RESOLVED instead)
- Modify beacon proximity relationships via raw API calls (use admin panel)
- Create fake alerts
- Modify GuardProfile active/available flags without verification
- Delete GuardAlerts (just let them expire)

✅ **Let backend handle:**
- Guard search algorithm
- Alert expiration
- Incident deduplication
- Status transitions

---

## 5. COMPLETE API ENDPOINT SUMMARY

### 5.1 Authentication Endpoints

| Endpoint | Method | Auth | Purpose | Response |
|----------|--------|------|---------|----------|
| `/api/auth/login/` | POST | No | Login with email/password | `{auth_token, user_id, role}` |
| `/api/auth/logout/` | POST | Yes | Logout & invalidate token | `{detail: "Logged out successfully"}` |

---

### 5.2 Incident Endpoints

| Endpoint | Method | Auth | Who | Purpose | Response |
|----------|--------|------|-----|---------|----------|
| `/api/incidents/` | GET | Yes | All | List incidents (filtered by role) | Incident list |
| `/api/incidents/` | POST | Yes | Admin | Create incident (manual) | Incident detail |
| `/api/incidents/{id}/` | GET | Yes | All | Get incident full details | Incident detail + signals + chat |
| `/api/incidents/{id}/` | PATCH | Yes | Admin | Update incident (status/priority) | Incident detail |
| `/api/incidents/{id}/resolve/` | POST | Yes | All | Mark as RESOLVED | Incident detail (status=RESOLVED) |
| `/api/incidents/{id}/signals/` | GET | Yes | All | Get all signals for incident | Signal list |
| `/api/incidents/report-sos/` | POST | Yes | Student | Report emergency | Incident detail + `status` (created/merged) |

---

### 5.3 Guard Endpoints

| Endpoint | Method | Auth | Who | Purpose | Response |
|----------|--------|------|-----|---------|----------|
| `/api/guards/` | GET | Yes | All | List all guards | Guard list |
| `/api/guards/{id}/` | GET | Yes | All | Get guard details | Guard detail |
| `/api/guards/update_location/` | POST | Yes | Guard | Update current beacon | `{status, guard}` |
| `/api/guards/{id}/set_beacon/` | POST | Yes | Guard | Set beacon (deprecated) | Guard detail |

---

### 5.4 Alert Endpoints

| Endpoint | Method | Auth | Who | Purpose | Response |
|----------|--------|------|-----|---------|----------|
| `/api/alerts/` | GET | Yes | Guard/Admin | List alerts | Alert list |
| `/api/alerts/{id}/` | GET | Yes | Guard/Admin | Get alert details | Alert detail |
| `/api/alerts/{id}/acknowledge/` | POST | Yes | Guard | Accept alert + create assignment | Alert detail (status=ACKNOWLEDGED) |
| `/api/alerts/{id}/decline/` | POST | Yes | Guard | Reject alert + search next guard | Alert detail (status=DECLINED) |

---

### 5.5 Assignment Endpoints

| Endpoint | Method | Auth | Who | Purpose | Response |
|----------|--------|------|-----|---------|----------|
| `/api/assignments/` | GET | Yes | Guard/Admin | List assignments | Assignment list |
| `/api/assignments/{id}/` | GET | Yes | Guard/Admin | Get assignment details | Assignment detail |
| `/api/assignments/{id}/deactivate/` | POST | Yes | Guard/Admin | Deactivate assignment | Assignment detail (is_active=false) |
| `/api/assignments/` | POST | Yes | Admin | Create assignment manually | Assignment detail |
| `/api/assignments/{id}/` | PATCH | Yes | Admin | Update assignment | Assignment detail |

---

### 5.6 Chat Endpoints

| Endpoint | Method | Auth | Who | Purpose | Response |
|----------|--------|------|-----|---------|----------|
| `/api/conversations/` | GET | Yes | All | List conversations | Conversation list |
| `/api/conversations/{id}/` | GET | Yes | All | Get conversation + messages | Conversation detail |
| `/api/conversations/{id}/messages/` | GET | Yes | All | Get all messages | `{conversation_id, incident_id, message_count, messages}` |
| `/api/conversations/{id}/send_message/` | POST | Yes | All | Send message | Message detail |
| `/api/messages/` | GET | Yes | All | List all messages | Message list |
| `/api/messages/{id}/` | GET | Yes | All | Get message details | Message detail |

---

### 5.7 Beacon Endpoints

| Endpoint | Method | Auth | Who | Purpose | Response |
|----------|--------|------|-----|---------|----------|
| `/api/beacons/` | GET | Yes | All | List all beacons | Beacon list |
| `/api/beacons/{id}/` | GET | Yes | All | Get beacon details | Beacon detail |

---

### 5.8 Panic Button Endpoint

| Endpoint | Method | Auth | Who | Purpose | Response |
|----------|--------|------|-----|---------|----------|
| `/api/panic/` | POST | No | ESP32 | Trigger emergency from device | `{status, incident_id, alerts_sent, location}` |

---

## 6. POLLING STRATEGY

### 6.1 Recommended Polling Intervals

| Operation | Interval | Reason | When Active |
|-----------|----------|--------|-------------|
| **Location Update (Guard)** | 10-15 sec | Beacon detection, precision | Always (guard logged in) |
| **Alert Check (Guard)** | 5-10 sec | Time-sensitive | Waiting for alert |
| **Chat Messages** | 3-5 sec | Immediate feedback | In chat screen |
| **Incident Status** | 5-10 sec | Track assignment | While incident active |

### 6.2 Backoff Rules

**When to Retry:**
- Network timeout (no response) → Retry after 3 seconds
- 5xx error → Exponential backoff (3s → 6s → 12s, max 60s)
- 429 Rate Limited → Backoff 60+ seconds

**When to NOT Retry:**
- 401 Unauthorized → Stop, show login screen
- 403 Forbidden → Stop, show permission error
- 404 Not Found → Stop, resource doesn't exist
- 400 Bad Request → Stop, fix request payload

### 6.3 What NOT to Poll Aggressively

❌ **Avoid polling more frequently than listed intervals:**
- Location updates < 10 sec wastes battery
- Alert checks < 5 sec adds no value (backend generates on-demand)
- Chat < 3 sec is overkill (user can't type faster)

✅ **Better Approach (if available):**
- Use FCM push notifications instead of polling
- Backend sends `{"alert_id": 5}` → Frontend fetches alert details
- This saves battery and is more responsive

### 6.4 Polling Stop Conditions

**Stop polling for alerts when:**
```
Guard has active assignment AND incident.status != RESOLVED
```

**Stop polling for location when:**
```
Guard logs out OR app is backgrounded
```

**Stop polling for chat when:**
```
incident.status == RESOLVED
```

---

## 7. FRONTEND RULES (NON-NEGOTIABLE)

### ✅ What Frontend CAN Do

- Display incident status, location, guard info
- Manage local UI state (which screen, form values, etc.)
- Cache incident/guard data in localStorage (for offline)
- Detect nearest beacon via BLE scanning
- Format timestamps and location names for display
- Validate email/password format before sending
- Show loading/error states to user

### ❌ What Frontend MUST NOT Do

| Rule | Reason |
|------|--------|
| **Never create multiple SOS reports for same incident** | Deduplication is backend's job. If student hits button twice, backend merges. Don't invent merging logic. |
| **Never decide if guard is available** | Only backend knows. GuardProfile.is_available is source of truth. |
| **Never decide if incident should be RESOLVED** | Only guard/admin can resolve. Frontend shows status, doesn't change it. |
| **Never skip location updates** | Guards must send beacon every 10-15 sec. This is how backend finds guards for incidents. |
| **Never modify beacon proximity data** | Backend admin panel handles this. Frontend is read-only. |
| **Never show "next guard" UI before backend assigns** | Wait for GuardAlert. Don't invent local fallback logic. |
| **Never auto-retry 401/403 errors** | These indicate auth/permission issues. Show login/error screen. |
| **Never poll incident status after status=RESOLVED** | Waste of bandwidth. Stop polling. |
| **Never manually create GuardAssignment** | Only backend auto-creates via acknowledge. Admin can create manually via API, but not frontend user. |

### ❌ What Backend ALWAYS Controls

| What | Why | Frontend Should |
|------|-----|-----------------|
| **Guard search algorithm** | Complex beacon proximity logic | Trust backend, display results only |
| **Incident deduplication** | Time-window + beacon matching | Send every SOS, backend merges |
| **Alert expiration** | Timestamp-based + status rules | Just poll alerts, don't expire locally |
| **Status transitions** | Strict state machine (CREATED→ASSIGNED→...) | Display status, never change locally |
| **Guard availability** | Real-time beacon + assignment data | Read only, never assume available |
| **Conversation creation** | Auto-created when assignment happens | Don't create manually, just use it |

---

## 8. ERROR HANDLING GUIDE

### 8.1 Standard Error Response Format

All endpoints follow this error format:

```json
{
  "error": "User-friendly error message"
}
```

Or:

```json
{
  "field_name": ["Error description"],
  "another_field": ["Multiple errors possible"]
}
```

Or:

```json
{
  "detail": "Error detail"
}
```

### 8.2 HTTP Status Codes & Handling

| Status | Meaning | Frontend Action |
|--------|---------|-----------------|
| **200 OK** | Request successful | Show response data |
| **201 Created** | Resource created | Show success, display new resource |
| **400 Bad Request** | Invalid payload | Show validation error to user, don't retry |
| **401 Unauthorized** | Token invalid/expired | Clear token, redirect to login |
| **403 Forbidden** | User lacks permission | Show permission denied error |
| **404 Not Found** | Resource doesn't exist | Show "not found" error |
| **500 Server Error** | Backend crashed | Show "server error" with retry option |
| **503 Service Unavailable** | Backend maintenance | Show offline message |

### 8.3 Common Errors & Recovery

**Error: "Invalid email or password"**
- User typed wrong credentials
- Action: Show login form error, let user retry

**Error: "User account is inactive"**
- Admin deactivated account
- Action: Show message "Account disabled. Contact admin."

**Error: "Only students can report SOS"**
- Guard tried to report SOS (should use different flow)
- Action: Prevent guard from seeing SOS button

**Error: "Beacon not found"**
- Beacon ID is invalid or doesn't exist
- Action: Show "Invalid location. Try again." Tell user to move to different area

**Error: "User does not have a guard profile"**
- User is student, not guard
- Action: This shouldn't happen. Show "Account type mismatch"

**Error: "Token invalid"** (401)
- Token expired or deleted
- Action: Delete token, redirect to login

---

## 9. REQUEST/RESPONSE JSON FORMAT REFERENCE

### 9.1 User Object

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "STUDENT",
  "is_active": true,
  "created_at": "2025-12-25T08:00:00Z",
  "updated_at": "2025-12-25T10:00:00Z"
}
```

### 9.2 Beacon Object

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "beacon_id": "BEACON-LIBRARY-001",
  "uuid": "FDA50693-A4E2-4FB1-AFCF-C6EB07647825",
  "major": 10001,
  "minor": 54321,
  "location_name": "Library Entrance",
  "building": "Building A",
  "floor": 1,
  "latitude": 40.1234,
  "longitude": -74.5678,
  "is_active": true,
  "created_at": "2025-12-25T08:00:00Z"
}
```

### 9.3 Incident Object (List View)

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "ASSIGNED",
  "priority": 2,
  "beacon": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "location_name": "Library Entrance",
    "building": "Building A",
    "floor": 1
  },
  "description": "I need help",
  "first_signal_time": "2025-12-25T10:30:00Z",
  "created_at": "2025-12-25T10:30:00Z"
}
```

### 9.4 Incident Object (Detail View - Full)

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "ASSIGNED",
  "priority": 2,
  "beacon": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "beacon_id": "BEACON-LIB-001",
    "uuid": "FDA50693-A4E2-4FB1-AFCF-C6EB07647825",
    "major": 10001,
    "minor": 54321,
    "location_name": "Library Entrance",
    "building": "Building A",
    "floor": 1,
    "latitude": 40.1234,
    "longitude": -74.5678,
    "is_active": true
  },
  "description": "I need help in the library",
  "first_signal_time": "2025-12-25T10:30:00Z",
  "last_signal_time": "2025-12-25T10:30:00Z",
  "created_at": "2025-12-25T10:30:00Z",
  "updated_at": "2025-12-25T10:30:00Z",
  "guard_assignments": [
    {
      "id": 10,
      "guard": {
        "id": "guard-uuid",
        "full_name": "Officer Mike",
        "email": "mike@example.com"
      },
      "assigned_at": "2025-12-25T10:30:30Z",
      "is_active": true
    }
  ],
  "conversation": {
    "id": 1,
    "created_at": "2025-12-25T10:30:30Z",
    "updated_at": "2025-12-25T10:32:00Z",
    "messages": [
      {
        "id": 1,
        "sender": {
          "id": "guard-uuid",
          "full_name": "Officer Mike",
          "email": "mike@example.com"
        },
        "message_text": "I'm on my way",
        "created_at": "2025-12-25T10:31:30Z"
      }
    ]
  },
  "signals": [
    {
      "id": 1,
      "signal_type": "STUDENT_SOS",
      "source_user": {
        "id": "student-uuid",
        "full_name": "John Doe",
        "email": "john@example.com"
      },
      "source_device": null,
      "ai_event": null,
      "created_at": "2025-12-25T10:30:00Z"
    }
  ]
}
```

### 9.5 GuardProfile Object

```json
{
  "user": {
    "id": "guard-uuid",
    "email": "mike@example.com",
    "full_name": "Officer Mike",
    "role": "GUARD",
    "is_active": true
  },
  "is_active": true,
  "is_available": true,
  "current_beacon": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "location_name": "Library Entrance",
    "building": "Building A",
    "floor": 1,
    "latitude": 40.1234,
    "longitude": -74.5678
  },
  "last_beacon_update": "2025-12-25T10:30:15Z",
  "last_active_at": "2025-12-25T10:30:15Z",
  "created_at": "2025-12-25T08:00:00Z",
  "updated_at": "2025-12-25T10:30:15Z"
}
```

### 9.6 GuardAlert Object

```json
{
  "id": 5,
  "status": "PENDING",
  "incident": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "CREATED",
    "priority": 3,
    "beacon": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "location_name": "Library Entrance",
      "building": "Building A",
      "floor": 1,
      "latitude": 40.1234,
      "longitude": -74.5678
    },
    "description": "I need help",
    "first_signal_time": "2025-12-25T10:30:00Z",
    "guard_assignments": [],
    "signals": [
      {
        "id": 1,
        "signal_type": "STUDENT_SOS",
        "source_user": {
          "full_name": "John Doe"
        }
      }
    ]
  },
  "created_at": "2025-12-25T10:30:05Z",
  "acknowledged_at": null,
  "assigned_at": null
}
```

### 9.7 Message Object

```json
{
  "id": 1,
  "sender": {
    "id": "user-uuid",
    "full_name": "Officer Mike",
    "email": "mike@example.com"
  },
  "message_text": "I'm on my way",
  "created_at": "2025-12-25T10:31:30Z"
}
```

### 9.8 GuardAssignment Object

```json
{
  "id": 10,
  "guard": {
    "id": "guard-uuid",
    "full_name": "Officer Mike",
    "email": "mike@example.com"
  },
  "assigned_at": "2025-12-25T10:30:30Z",
  "is_active": true
}
```

### 9.9 Conversation Object

```json
{
  "id": 1,
  "created_at": "2025-12-25T10:30:30Z",
  "updated_at": "2025-12-25T10:32:00Z",
  "messages": [
    {
      "id": 1,
      "sender": {
        "id": "guard-uuid",
        "full_name": "Officer Mike",
        "email": "mike@example.com"
      },
      "message_text": "I'm on my way",
      "created_at": "2025-12-25T10:31:30Z"
    }
  ]
}
```

---

## QUICK START CHECKLIST FOR FRONTEND TEAM

### Phase 1: Authentication
- [ ] Implement login screen (email + password)
- [ ] Store auth_token in secure storage
- [ ] Attach token to all requests (Authorization header)
- [ ] Implement logout (delete token, clear UI)
- [ ] Handle 401 errors (redirect to login)

### Phase 2: Student App
- [ ] BLE beacon scanning (detect nearest beacon)
- [ ] Report SOS screen
- [ ] Poll incident status (5-10 sec interval)
- [ ] Display guard assignment when status = ASSIGNED
- [ ] Chat screen (fetch + send messages)
- [ ] Stop polling when incident.status = RESOLVED

### Phase 3: Guard App
- [ ] **Background location updates** (post beacon every 10-15 sec)
- [ ] Poll alerts (5-10 sec interval)
- [ ] Alert detail screen (show incident info + student)
- [ ] Acknowledge button (POST /alerts/{id}/acknowledge/)
- [ ] Decline button (POST /alerts/{id}/decline/)
- [ ] Chat screen (send + receive messages)
- [ ] Assignment status screen

### Phase 4: Polish
- [ ] Error messages (all 4xx/5xx cases)
- [ ] Loading states (while polling)
- [ ] Offline handling (cache critical data)
- [ ] Push notifications (optional, use FCM)
- [ ] Beacon reliability (retry if no beacon found)

---

## SUPPORT & QUESTIONS

**Backend is PRODUCTION-READY.** All endpoints tested and working.

If frontend encounters:
- **404 on valid incident ID** → Check user role filtering
- **Alert not received** → Check guard location updates are working
- **Chat not appearing** → Check conversation is tied to incident
- **Incident not created** → Check beacon ID is valid UUID

The backend will tell you what's wrong via response JSON. Trust error messages.

---

**Generated:** December 25, 2025  
**Status:** Ready for Frontend Development  
**Backend:** ✅ 100% Complete
