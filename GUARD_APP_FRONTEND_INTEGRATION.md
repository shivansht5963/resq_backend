# Guard App Frontend Integration Guide

## Configuration
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_TIMEOUT=30000
REACT_APP_DEBUG_MODE=false
```

---

## 1. Authentication

### Login
**`POST /api/accounts/login/`**
```json
{
  "username": "guard_user",
  "password": "secure_password"
}
```
**Response (200):**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "guard_user",
    "email": "user@example.com",
    "role": "guard"
  }
}
```

### Register
**`POST /api/accounts/register/`**
```json
{
  "username": "new_guard",
  "email": "guard@example.com",
  "password": "password123",
  "role": "guard"
}
```

### Logout
**`POST /api/accounts/logout/`** | Header: `Authorization: Bearer <token>`

---

## 2. Incidents

### Report Incident
**`POST /api/incidents/report/`** | Header: `Authorization: Bearer <token>`
```json
{
  "incident_type": "theft",
  "location": {"latitude": 12.9716, "longitude": 77.5946},
  "description": "Suspicious activity near gate",
  "severity": "high",
  "reporters": [1],
  "media": "file_upload"
}
```
**Response (201):**
```json
{
  "id": 5,
  "incident_type": "theft",
  "status": "reported",
  "created_at": "2025-12-29T10:30:00Z",
  "location": {"latitude": 12.9716, "longitude": 77.5946}
}
```

### Get Incidents
**`GET /api/incidents/?status=active&limit=10`** | Header: `Authorization: Bearer <token>`
**Response (200):**
```json
{
  "count": 15,
  "next": "http://localhost:8000/api/incidents/?page=2",
  "results": [
    {"id": 5, "incident_type": "theft", "status": "active", "severity": "high"},
    {"id": 4, "incident_type": "trespassing", "status": "investigating", "severity": "medium"}
  ]
}
```

### Get Incident Detail
**`GET /api/incidents/{id}/`** | Header: `Authorization: Bearer <token>`

### Update Incident
**`PATCH /api/incidents/{id}/`** | Header: `Authorization: Bearer <token>`
```json
{
  "status": "investigating",
  "assigned_to": 2
}
```

---

## 3. Security Alerts

### Create Alert
**`POST /api/security/alerts/`** | Header: `Authorization: Bearer <token>`
```json
{
  "alert_type": "suspicious_activity",
  "location": {"latitude": 12.9716, "longitude": 77.5946},
  "priority": "high",
  "description": "Unknown person near boundary"
}
```
**Response (201):**
```json
{
  "id": 12,
  "alert_type": "suspicious_activity",
  "status": "active",
  "priority": "high",
  "created_at": "2025-12-29T10:35:00Z"
}
```

### Get Alerts
**`GET /api/security/alerts/?priority=high`** | Header: `Authorization: Bearer <token>`

### Resolve Alert
**`PATCH /api/security/alerts/{id}/`** | Header: `Authorization: Bearer <token>`
```json
{
  "status": "resolved",
  "resolution_notes": "False alarm - maintenance crew"
}
```

---

## 4. Chat & Communication

### Get Conversations
**`GET /api/chat/conversations/`** | Header: `Authorization: Bearer <token>`

### Send Message
**`POST /api/chat/messages/`** | Header: `Authorization: Bearer <token>`
```json
{
  "conversation": 3,
  "content": "Backup needed at North Gate",
  "message_type": "text"
}
```

### Get Messages
**`GET /api/chat/conversations/{id}/messages/`** | Header: `Authorization: Bearer <token>`

---

## 5. AI Engine & Beacon

### Report Beacon Event
**`POST /api/ai_engine/events/`** | Header: `Authorization: Bearer <token>`
```json
{
  "event_type": "proximity_alert",
  "beacon_id": "beacon_001",
  "location": {"latitude": 12.9716, "longitude": 77.5946},
  "intensity": 0.85,
  "timestamp": "2025-12-29T10:40:00Z"
}
```

### Get AI Events
**`GET /api/ai_engine/events/?event_type=anomaly&limit=20`** | Header: `Authorization: Bearer <token>`

---

## Error Responses

| Code | Error | Meaning |
|------|-------|---------|
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Backend error |

---

## Implementation Notes
- All requests use `Content-Type: application/json`
- Token expires in 24 hours; refresh before expiry
- Pagination: Default 20 items per page
- Image uploads use `multipart/form-data`
- Timestamps in ISO 8601 format
