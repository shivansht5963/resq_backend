# GUARD (SECURITY) APP - Frontend Integration Guide

## 1. Purpose
Security app to receive SOS alerts from students, update location every 10-15 seconds, accept/decline incidents, chat with students, resolve incidents.

---

## 2. Authentication

**Login Endpoint:**
```
POST /auth/login/
```

**Request:**
```json
{
  "email": "guard@example.com",
  "password": "password123"
}
```

**Response (201 Created):**
```json
{
  "auth_token": "de88e903f2731983695f8e698a4eaa3d83d05d4a",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "role": "GUARD",
  "email": "guard@example.com"
}
```

**Token Storage:** SecureStore (iOS) / EncryptedSharedPreferences (Android). Never log or store plaintext.

**Logout:**
```
POST /auth/logout/
Authorization: Token {token}
```
Response: 200 OK. Clear token & stop all polling.

---

## 3. Guard App Screens
1. **Login** - Email & password
2. **On-Duty Status** - Location updates running, show active/inactive
3. **Alerts Screen** - Poll every 5-10s, display new SOS alerts
4. **Alert Details** - Incident info, accept/decline buttons
5. **Assigned Incident** - Student location, description, assignment details
6. **Chat** - Real-time messages with student
7. **Assignment History** - Past & active assignments

---

## 4. API Endpoints Summary

| Endpoint | Method | Polling | Purpose |
|----------|--------|---------|---------|
| `/guards/update_location/` | POST | 10-15 sec | Update nearest beacon (CRITICAL) |
| `/alerts/` | GET | 5-10 sec | List unacknowledged alerts |
| `/alerts/{id}/` | GET | Once | Get alert with incident details |
| `/alerts/{id}/acknowledge/` | POST | Once | Accept alert, create assignment |
| `/alerts/{id}/decline/` | POST | Once | Reject alert (reassign to others) |
| `/assignments/` | GET | 30 sec | List active assignments |
| `/incidents/{id}/` | GET | 5 sec | Get incident status & details |
| `/conversations/{id}/messages/` | GET | 3 sec | Get all messages in chat |
| `/conversations/{id}/send_message/` | POST | Once | Send message to student |
| `/incidents/{id}/resolve/` | POST | Once | Mark incident resolved |

---

## 5. Detailed Endpoint JSON Examples

### 5.1 Update Guard Location (CRITICAL - Every 10-15 Seconds)

**Endpoint:**
```
POST /guards/update_location/
Authorization: Token {token}
Content-Type: application/json
```

**Request:**
```json
{
  "nearest_beacon_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-25T10:30:15Z"
}
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "guard_id": "550e8400-e29b-41d4-a716-446655440001",
  "beacon_id": "550e8400-e29b-41d4-a716-446655440000",
  "updated_at": "2025-12-25T10:30:15Z"
}
```

**⚠️ CRITICAL:** Update every 10-15 seconds continuously. If stops > 5 min, backend marks guard offline. Continue updates even during chat.

---

### 5.2 Poll for Alerts

**Endpoint:**
```
GET /alerts/
Authorization: Token {token}
```

**Response (200 OK):**
```json
{
  "count": 2,
  "results": [
    {
      "id": 17,
      "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
      "status": "PENDING",
      "created_at": "2025-12-25T10:30:00Z"
    },
    {
      "id": 18,
      "incident_id": "85ca3932-0b7c-475b-834b-0573dfe037dd",
      "status": "PENDING",
      "created_at": "2025-12-25T10:32:00Z"
    }
  ]
}
```

**Poll every 5-10 seconds on On-Duty screen.**

---

### 5.3 Get Alert Details

**Endpoint:**
```
GET /alerts/17/
Authorization: Token {token}
```

**Response (200 OK):**
```json
{
  "id": 17,
  "status": "PENDING",
  "incident": {
    "id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
    "student": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "John Student",
      "phone": "+1234567890"
    },
    "beacon": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Library Entrance",
      "location": "Building A, Floor 1"
    },
    "description": "I need help in the library",
    "priority": 2
  },
  "created_at": "2025-12-25T10:30:00Z"
}
```

---

### 5.4 Accept Alert (Acknowledge)

**Endpoint:**
```
POST /alerts/17/acknowledge/
Authorization: Token {token}
Content-Type: application/json
```

**Request:**
```json
{}
```

**Response (200 OK):**
```json
{
  "id": 17,
  "status": "ACKNOWLEDGED",
  "assignment": {
    "id": 1,
    "guard_id": "550e8400-e29b-41d4-a716-446655440001",
    "guard_name": "John Guard",
    "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
    "is_active": true,
    "conversation_id": 1,
    "created_at": "2025-12-25T10:31:00Z"
  },
  "acknowledged_at": "2025-12-25T10:31:00Z"
}
```

**Result:** Alert removed from alerts list, assignment created, conversation ready.

---

### 5.5 Decline Alert (Reject)

**Endpoint:**
```
POST /alerts/17/decline/
Authorization: Token {token}
Content-Type: application/json
```

**Request:**
```json
{}
```

**Response (200 OK):**
```json
{
  "id": 17,
  "status": "DECLINED",
  "declined_at": "2025-12-25T10:31:00Z"
}
```

**Result:** Alert removed from alerts list, reassigned to other on-duty guards.

---

### 5.6 Get Active Assignments

**Endpoint:**
```
GET /assignments/
Authorization: Token {token}
```

**Response (200 OK):**
```json
{
  "count": 2,
  "results": [
    {
      "id": 1,
      "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
      "guard": {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "John Guard"
      },
      "student": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Jane Student",
        "phone": "+9876543210"
      },
      "incident_details": {
        "beacon_name": "Library Entrance",
        "description": "I need help",
        "status": "IN_PROGRESS"
      },
      "is_active": true,
      "conversation_id": 1,
      "created_at": "2025-12-25T10:31:00Z"
    }
  ]
}
```

**Poll every 30 seconds on On-Duty screen.**

---

### 5.7 Get Incident Details & Status

**Endpoint:**
```
GET /incidents/75ca3932-0b7c-475b-834b-0573dfe037dc/
Authorization: Token {token}
```

**Response (200 OK):**
```json
{
  "id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "status": "IN_PROGRESS",
  "priority": 2,
  "student": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Jane Student",
    "phone": "+9876543210"
  },
  "beacon": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Library Entrance",
    "location": "Building A, Floor 1"
  },
  "description": "I need help",
  "assignment": {
    "id": 1,
    "guard": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "John Guard"
    },
    "conversation_id": 1
  },
  "created_at": "2025-12-25T10:30:00Z",
  "updated_at": "2025-12-25T10:35:00Z"
}
```

**Poll every 5 seconds while incident is active.**

---

### 5.8 Get Conversation Messages

**Endpoint:**
```
GET /conversations/1/messages/
Authorization: Token {token}
```

**Response (200 OK):**
```json
{
  "conversation_id": 1,
  "incident_id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "messages": [
    {
      "id": 122,
      "sender_id": "550e8400-e29b-41d4-a716-446655440001",
      "sender": "John Guard",
      "sender_role": "GUARD",
      "content": "I'm arriving in 2 minutes",
      "timestamp": "2025-12-25T10:34:00Z"
    },
    {
      "id": 123,
      "sender_id": "550e8400-e29b-41d4-a716-446655440000",
      "sender": "Jane Student",
      "sender_role": "STUDENT",
      "content": "Thank you, I'm near the main reading area",
      "timestamp": "2025-12-25T10:35:30Z"
    }
  ]
}
```

**Poll every 3 seconds during chat.**

---

### 5.9 Send Message to Student

**Endpoint:**
```
POST /conversations/1/send_message/
Authorization: Token {token}
Content-Type: application/json
```

**Request:**
```json
{
  "content": "I'm near the building entrance, which floor are you on?"
}
```

**Response (201 Created):**
```json
{
  "id": 124,
  "sender_id": "550e8400-e29b-41d4-a716-446655440001",
  "sender_role": "GUARD",
  "content": "I'm near the building entrance, which floor are you on?",
  "timestamp": "2025-12-25T10:36:00Z"
}
```

---

### 5.10 Resolve Incident

**Endpoint:**
```
POST /incidents/75ca3932-0b7c-475b-834b-0573dfe037dc/resolve/
Authorization: Token {token}
Content-Type: application/json
```

**Request:**
```json
{}
```

**Response (200 OK):**
```json
{
  "id": "75ca3932-0b7c-475b-834b-0573dfe037dc",
  "status": "RESOLVED",
  "resolved_at": "2025-12-25T10:40:00Z",
  "resolution_time_seconds": 600
}
```

**Result:** Incident closed, stop polling status, remove from assignments, return to On-Duty screen.

---

## 6. Location Update Rules (CRITICAL ⚠️)

**Frequency:** Every 10-15 seconds continuously
**Start:** Immediately after login
**Stop:** Only on logout
**Background:** Must continue even when app minimized (use background tasks)

**✅ MUST:**
- Update every 10-15 sec without fail
- Include nearest beacon UUID
- Include precise ISO 8601 timestamp
- Continue during chat, assignments, all screens
- Implement in background task (iOS/Android)

**❌ NEVER:**
- Skip updates even if same beacon
- Stop during other operations
- Invent beacon IDs
- Update only on user action

**If stops > 5 min:** Backend removes guard from active pool, cannot receive new alerts.

---

## 7. Guard App Flow (Complete)

```
1. LOGIN
   ├─ POST /auth/login/
   ├─ Store token in secure storage
   ├─ Start location update interval (10-15 sec)
   ├─ Start alert polling interval (5-10 sec)
   └─ Navigate to On-Duty Screen

2. ON-DUTY STATUS SCREEN (Continuous)
   ├─ POST /guards/update_location/ (Every 10-15 sec)
   ├─ GET /alerts/ (Every 5-10 sec)
   ├─ GET /assignments/ (Every 30 sec)
   ├─ Display new alerts as they arrive
   └─ Wait for guard action (Accept/Decline/Logout)

3. RECEIVE ALERT (Real-time)
   ├─ GET /alerts/{id}/ (Get full details)
   ├─ Show: Student name, location, description, priority
   ├─ Display accept/decline buttons
   └─ Guard chooses action

4. ACCEPT ALERT
   ├─ POST /alerts/{id}/acknowledge/
   ├─ Get assignment_id + conversation_id
   ├─ Remove alert from list
   ├─ Add to active assignments
   └─ Navigate to Assigned Incident Screen

5. DECLINE ALERT
   ├─ POST /alerts/{id}/decline/
   ├─ Remove from alerts list
   ├─ Stay on On-Duty Screen
   └─ Alert reassigned to other guards

6. ASSIGNED INCIDENT SCREEN (While Active)
   ├─ GET /incidents/{id}/ (Poll every 5 sec)
   ├─ Show: Student, location, description, assignment
   ├─ Display: Chat & Resolve buttons
   ├─ POST /guards/update_location/ (Continue every 10-15 sec)
   └─ Wait for guard action

7. CHAT WITH STUDENT (While Communicating)
   ├─ GET /conversations/{id}/messages/ (Poll every 3 sec)
   ├─ POST /conversations/{id}/send_message/ (On send)
   ├─ Display messages from both parties
   ├─ POST /guards/update_location/ (Continue every 10-15 sec)
   └─ Wait for incident resolution

8. RESOLVE INCIDENT
   ├─ Guard confirms incident resolved
   ├─ POST /incidents/{id}/resolve/
   ├─ Stop polling incident status
   ├─ Remove from active assignments
   ├─ Show confirmation message
   └─ Return to On-Duty Screen

9. LOGOUT
   ├─ Stop location update interval
   ├─ Stop alert polling interval
   ├─ POST /auth/logout/
   ├─ Clear token from storage
   └─ Navigate to Login Screen
```

---

## 8. Guard App Rules & Restrictions

**✅ MUST DO:**
- Update location EVERY 10-15 seconds without exception
- Start location updates immediately after login
- Keep location updates running in foreground AND background
- Poll alerts EVERY 5-10 seconds while on duty
- Include `Authorization: Token {token}` in ALL requests
- Handle 401 errors → Log out immediately
- Continue location updates even during chat/incident handling
- Stop all polling immediately on logout

**❌ MUST NEVER:**
- Report SOS emergencies (student app only)
- Accept multiple alerts simultaneously (one assignment at a time)
- Skip location updates for any reason
- Stop location updates during chat or incident handling
- Modify incident data directly (use resolve endpoint only)
- Invent incident statuses (use backend response values)
- Send messages outside conversation_id
- Store token in plaintext or logs
- Use WebSockets (REST polling only)
- Access student/admin endpoints

---

## 9. Success Criteria

✅ Login successful, token stored securely
✅ Location updates every 10-15 seconds (visible in backend logs)
✅ Location updates continue in background when app minimized
✅ Alerts poll every 5-10 seconds, display new incidents real-time
✅ Can view alert details with full incident info
✅ Accept alert → get assignment + conversation_id
✅ Decline alert → alert reassigned to other guards
✅ Can send/receive messages with students
✅ Messages poll every 3 seconds during chat
✅ Continue location updates during entire incident handling
✅ Can resolve incident, removes from active assignments
✅ Logout stops all polling & clears token
✅ 401 errors redirect to login immediately
✅ Network failures handled with exponential backoff
✅ Multiple active assignments tracked correctly

---

## 10. Configuration & Environment

**Env Variables:**
```
REACT_APP_API_BASE_URL=https://resq-server.onrender.com/api
REACT_APP_LOCATION_UPDATE_INTERVAL=12000  (ms - 10-15 sec)
REACT_APP_ALERT_POLL_INTERVAL=7000        (ms - 5-10 sec)
REACT_APP_ASSIGNMENT_POLL_INTERVAL=30000  (ms - 30 sec)
REACT_APP_INCIDENT_POLL_INTERVAL=5000     (ms - 5 sec)
REACT_APP_MESSAGE_POLL_INTERVAL=3000      (ms - 3 sec)
REACT_APP_LOCATION_TIMEOUT=300000         (ms - 5 min)
```

**Error Handling:**
- **401 Unauthorized:** Clear token → Log out → Redirect to login
- **400 Bad Request:** Show validation error message
- **403 Forbidden:** Show "Permission denied"
- **404 Not Found:** Show "Resource not found"
- **5xx Server Error:** Show error → Retry after 5-10 sec

**Background Location Updates (iOS/Android):**
- Use `react-native-background-timer` or `expo-task-manager`
- Schedule location update every 10-15 seconds
- Continue running even when app is minimized
- Stop only on logout
- Handle network failures with 5-second retry backoff

**App Restart Behavior:**
- Check if token exists in secure storage
- If yes → Auto-login, resume location updates immediately
- If no → Show login screen

---

## 11. Error Response Examples

**401 Unauthorized:**
```json
{
  "detail": "Invalid token."
}
→ Clear token, stop all polling, redirect to login
```

**400 Bad Request:**
```json
{
  "nearest_beacon_id": ["Invalid UUID format"],
  "timestamp": ["Required field"]
}
→ Show validation errors, allow retry
```

**403 Forbidden:**
```json
{
  "detail": "Permission denied. Guards only."
}
→ Show error message
```

**404 Not Found:**
```json
{
  "detail": "Alert not found."
}
→ Show error, refresh alert list
```

**500 Server Error:**
```json
{
  "detail": "Server error. Try again later."
}
→ Show error, provide retry button, retry after 5-10 sec
```
