# STUDENT MOBILE APP - Frontend Integration Guide

## 1. Purpose
Emergency response application for students. Report SOS incidents, track assignment progress, communicate with security guards in real-time.

---

## 2. Authentication

### Login Endpoint
```
POST https://resq-server.onrender.com/api/auth/login/
Content-Type: application/json

{
  "email": "student@example.com",
  "password": "password123"
}
```

### Login Response (201 Created)
```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "student@example.com",
    "full_name": "John Student",
    "role": "STUDENT"
  }
}
```

### Token Storage Rules
- **Store in secure storage** (AsyncStorage or SecureStore)
- **Extract token value** from login response: `response.token`
- **Include in every request** as `Authorization: Token {token}`
- **Token is permanent** (no expiration unless manually logged out)
- **DO NOT store in plaintext** in state or console logs

### Logout
```
POST https://resq-server.onrender.com/api/auth/logout/
Authorization: Token {auth_token}
Content-Type: application/json
```
- **Response:** 200 OK
- **Action:** Clear token from storage, navigate to login screen

---

## 3. Student App Screens
1. **Login Screen** - Email & password input
2. **Auto Beacon Detection** - BLE scanning for nearest beacon (primary)
3. **Manual Beacon Selection** - Fallback list if BLE fails (secondary)
4. **SOS Report Screen** - Confirm location & add description
5. **Incident Status Screen** - Real-time incident tracking (poll every 5 sec)
6. **Chat Screen** - Message exchange with assigned guard
7. **Incident History** - List of past incidents

---

## 4. Student API Endpoints

| Endpoint | Method | Purpose | Request | Response | Polling |
|----------|--------|---------|---------|----------|---------|
| `/beacons/` | GET | List campus locations | None | `{beacon_list}` | On app load |
| `/incidents/report_sos/` | POST | Create emergency incident | `{beacon_id, description}` | `{incident_id, status}` | Once |
| `/incidents/` | GET | List student's incidents | None | `{incident_list}` | Every 30 sec |
| `/incidents/{id}/` | GET | Get incident details & guard info | None | `{incident, assignment, conversation_id}` | Every 5 sec (active) |
| `/conversations/{id}/messages/` | GET | Get conversation messages with guard | None | `{messages}` | Every 3 sec (active) |
| `/conversations/{id}/send_message/` | POST | Send message to guard | `{content}` | `{message_id, timestamp}` | Once |

### Detailed Endpoint JSON Examples

#### 1. Get Beacons
**Request:** None
```json
GET /beacons/
Authorization: Token {token}
```

**Response (200 OK):**
```json
{
  "count": 3,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Library Entrance",
      "location": "Building A, Floor 1"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Science Center",
      "location": "Building B, Floor 2"
    }
  ]
}
```

#### 2. Report SOS
**Request:**
```json
POST /incidents/report_sos/
Authorization: Token {token}
Content-Type: application/json

{
  "beacon_id": "550e8400-e29b-41d4-a716-446655440000",
  "description": "I need help in the library"
}
```

**Response (201 Created):**
```json
{
  "id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "student_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CREATED",
  "beacon_id": "550e8400-e29b-41d4-a716-446655440000",
  "description": "I need help in the library",
  "created_at": "2025-12-25T10:30:00Z",
  "assignment": null
}
```

**Note:** Status is `CREATED` when incident first reported. Backend will update to `ASSIGNED` when guard accepts, then `IN_PROGRESS` when guard arrives, then `RESOLVED` when guard resolves.

#### 3. Get Incident Details
**Request:** None
```json
GET /incidents/75ca3932-0b7c-475b-834b-0573dfe037dc/
Authorization: Token {token}
```

**Response (200 OK):**
```json
{
  "id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "status": "IN_PROGRESS",
  "student": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "John Student"
  },
  "beacon": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Library Entrance"
  },
  "assignment": {
    "id": 1,
    "guard": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Guard Name",
      "phone": "+1234567890"
    },
    "conversation_id": 1
  },
  "created_at": "2025-12-25T10:30:00Z",
  "updated_at": "2025-12-25T10:35:00Z"
}
```

**Status Progression (Backend Controlled):**
- `CREATED` → Incident reported, waiting for guards
- `ASSIGNED` → Guard accepted the alert
- `IN_PROGRESS` → Guard is on the way or with student
- `RESOLVED` → Guard completed the incident (student cannot change this)

#### 4. Send Message to Guard
**Request:**
```json
POST /conversations/1/send_message/
Authorization: Token {token}
Content-Type: application/json

{
  "content": "I'm near the main reading area on floor 1"
}
```

**Response (201 Created):**
```json
{
  "id": 123,
  "sender_id": "550e8400-e29b-41d4-a716-446655440000",
  "sender_role": "STUDENT",
  "content": "I'm near the main reading area on floor 1",
  "timestamp": "2025-12-25T10:35:30Z"
}
```

#### 5. Get Conversation Messages
**Request:** None
```json
GET /conversations/1/messages/
Authorization: Token {token}
```

**Response (200 OK):**
```json
{
  "conversation_id": 1,
  "messages": [
    {
      "id": 122,
      "sender": "Guard Name",
      "sender_role": "GUARD",
      "content": "I'm arriving in 2 minutes",
      "timestamp": "2025-12-25T10:34:00Z"
    },
    {
      "id": 123,
      "sender": "John Student",
      "sender_role": "STUDENT",
      "content": "I'm near the main reading area",
      "timestamp": "2025-12-25T10:35:30Z"
    }
  ]
}
```

#### 6. Monitor Incident Resolution (Student Read-Only)

**⚠️ CRITICAL:** Student CANNOT resolve incidents. Only assigned guard or admin can resolve.

**Incident resolution happens ONLY when:**
- Assigned guard calls `POST /incidents/{id}/resolve/`
- OR admin manually resolves

**Student must:**
- Poll incident status every 5 seconds
- When `status === "RESOLVED"`, show "Incident Resolved" message
- DO NOT provide a "Resolve" button in UI
- Allow user to return to home or incident history

**Example resolved incident response:**
```json
{
  "id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "status": "RESOLVED",
  "resolved_at": "2025-12-25T10:40:00Z",
  "assignment": {...}
}
```

---

## 5. Student App Flow (Step-by-Step)

```
1. LAUNCH APP
   ↓
2. LOGIN
   ├─ POST /auth/login/
   ├─ Extract token from response.token
   ├─ Store token in secure storage
   ├─ On success → Go to Auto Beacon Detection
   └─ On error (401) → Show error message
   ↓
3. AUTO DETECT BEACON (Primary Method)
   ├─ Start BLE scanning
   ├─ Detect nearest beacon
   ├─ If found: Use detected beacon UUID
   └─ If not found in 10s: Go to Manual Selection
   ↓
3b. MANUAL BEACON SELECTION (Fallback)
   ├─ GET /beacons/ (show list)
   ├─ User manually selects beacon
   └─ Continue to SOS Screen
   ↓
4. REPORT SOS
   ├─ User enters description (optional)
   ├─ POST /incidents/report_sos/ with beacon_id
   ├─ Get incident_id from response
   ├─ Incident status: CREATED
   └─ Go to Incident Status Screen
   ↓
5. POLL INCIDENT STATUS (Every 5 seconds)
   ├─ GET /incidents/{incident_id}/
   ├─ If status CREATED: Show "Waiting for guard..."
   ├─ If status ASSIGNED: Show assigned guard info
   ├─ If status IN_PROGRESS: Show "Guard arriving..."
   └─ If status RESOLVED: Show "Incident Resolved"
   ↓
6. CHAT WITH GUARD (When assigned, poll every 3 sec)
   ├─ GET /conversations/{conversation_id}/messages/
   ├─ POST /conversations/{conversation_id}/send_message/
   ├─ Display real-time messages with guard
   └─ Continue polling incident status
   ↓
7. INCIDENT RESOLVED (Guard resolves, NOT student)
   ├─ Guard calls POST /incidents/{id}/resolve/
   ├─ Student polls and sees status RESOLVED
   ├─ Show "Incident Resolved" message
   └─ Go back to home or incident history
```

---

## 6. Student App Rules

### ✅ DO
- Store token securely in SecureStore (never plaintext)
- Extract token from `response.token` after login
- Include `Authorization: Token {token}` in ALL protected requests
- Auto-detect nearest beacon via BLE first
- Use manual beacon selection only if BLE fails
- Poll incident status every 5 seconds (while active)
- Poll messages every 3 seconds during chat
- Display status as-is from backend (CREATED, ASSIGNED, IN_PROGRESS, RESOLVED)
- Show "Waiting for guard..." while status is CREATED or ASSIGNED
- Handle 401 errors → Log out and go to login screen
- Handle 403 errors → Show "Access denied"
- Handle 5xx errors → Show "Server error, try again"
- Cache beacon list (update on app launch)

### ❌ DO NOT
- **ATTEMPT TO RESOLVE INCIDENTS** (Guard-only action)
- Accept alert assignments (Guard-only action)
- Update guard location (Guard-only action)
- Use status values other than: CREATED, ASSIGNED, IN_PROGRESS, RESOLVED
- Call POST `/incidents/{id}/resolve/` (not allowed for students)
- Access `/guards/` or `/admin/` endpoints
- Create assignments manually
- Send messages outside of conversation_id
- Store token in plaintext, logs, or localStorage
- Use WebSockets (polling only)
- Invent or guess incident status values

---

## 7. Success Criteria

✅ **Student App is successful when:**
1. User can login with valid credentials
2. Token extracted from `response.token` and stored securely
3. App attempts auto-detection of nearest beacon via BLE
4. If BLE fails, shows manual beacon selection list
5. User can report SOS incident and receive incident_id
6. Incident status starts as `CREATED`
7. App polls incident status every 5 seconds
8. Status updates: CREATED → ASSIGNED → IN_PROGRESS → RESOLVED
9. Once guard assigned (status ASSIGNED), chat becomes available
10. User can send/receive messages with assigned guard
11. **User CANNOT resolve incident** (no resolve button in UI)
12. When guard resolves, status becomes RESOLVED
13. Student sees "Incident Resolved" without taking action
14. Logout clears token from storage
15. 401 errors redirect to login
16. App handles all HTTP error codes gracefully

---

## Environment Variables (.env)
```
REACT_APP_API_BASE_URL=https://resq-server.onrender.com/api
REACT_APP_POLL_INCIDENT_INTERVAL=5000  (ms)
REACT_APP_POLL_MESSAGE_INTERVAL=3000   (ms)
REACT_APP_BEACON_CACHE_TIME=3600000    (ms - 1 hour)
```

---

## Error Response Examples

**400 Bad Request:**
```json
{
  "beacon_id": ["Invalid UUID format"]
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid token."
}
```

**403 Forbidden:**
```json
{
  "detail": "Permission denied."
}
```

**404 Not Found:**
```json
{
  "detail": "Incident not found."
}
```

**500 Server Error:**
```json
{
  "detail": "Server error. Try again later."
}
```
