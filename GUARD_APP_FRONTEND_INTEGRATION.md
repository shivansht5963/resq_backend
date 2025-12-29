# Guard App Frontend Integration Guide

## Configuration
```
REACT_APP_API_URL=https://resq-server.onrender.com/api
REACT_APP_API_TIMEOUT=30000
REACT_APP_DEBUG_MODE=false
```

---

## 1. Authentication

### Login
**`POST https://resq-server.onrender.com/api/accounts/login/`**
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
    "email": "user@example.com"
  }
}
```

### Logout
**`POST https://resq-server.onrender.com/api/accounts/logout/`** | Header: `Authorization: Token <token>`

---

## 2. Incidents

### Report Incident
**`POST https://resq-server.onrender.com/api/incidents/incidents/report/`** | Header: `Authorization: Token <token>`
```json
{
  "type": "theft",
  "description": "Suspicious activity near gate",
  "location": "Gate A",
  "beacon_id": "beacon_001"
}
```
**Response (201):**
```json
{
  "id": 5,
  "type": "theft",
  "status": "reported",
  "location": "Gate A",
  "images": ["https://storage.googleapis.com/..."]
}
```

### Get Incidents
**`GET https://resq-server.onrender.com/api/incidents/incidents/`** | Header: `Authorization: Token <token>`
**Response (200):**
```json
{
  "count": 15,
  "results": [
    {"id": 5, "type": "theft", "status": "active", "location": "Gate A"},
    {"id": 4, "type": "trespassing", "status": "reported", "location": "Boundary"}
  ]
}
```

### Get Incident Detail
**`GET https://resq-server.onrender.com/api/incidents/incidents/{id}/`** | Header: `Authorization: Token <token>`

### SOS Report
**`POST https://resq-server.onrender.com/api/incidents/incidents/report_sos/`** | Header: `Authorization: Token <token>`
```json
{
  "beacon_id": "beacon_001",
  "location": "Emergency Location"
}
```

---

## 3. Security Alerts

### Create Alert
**`POSGuard Profile & Alerts

### Get Guard Profile
**`GET https://resq-server.onrender.com/api/security/guards/`** | Header: `Authorization: Token <token>`
**Response (200):**
```json
{
  "id": 1,
  "user": {"username": "guard_user", "email": "user@example.com"},
  "status": "active",
  "area_assigned": "Main Gate"
}
```

### Get Alerts
**`GET https://resq-server.onrender.com/api/security/alerts/`** | Header: `Authorization: Token <token>`
**Response (200):**
```json
{
  "count": 8,
  "results": [
    {"id": 12, "alert_type": "suspicious_activity", "status": "active", "priority": "high"},
    {"id": 11, "alert_type": "system_alert", "status": "resolved", "priority": "low"}
  ]
}
```

### Update Alert
**`PATCH https://resq-server.onrender.com/api/security/alerts/{id}/`** | Header: `Authorization: Token <token>`
```json
{
  "status": "resolved
---

## 4. Beacons

### Get Beacons
**`GET https://resq-server.onrender.com/api/incidents/beacons/`** | Header: `Authorization: Token <token>`
**Response (200):**
```json
{
  "count": 5,
  "results": [
    {"id": 1, "beacon_id": "beacon_001", "location": "Gate A", "status": "active"},
    {"id": 2, "beacon_id": "beacon_002", "location": "Boundary", "status": "active"}
  ]
}
```

### Panic Button
**`POST https://resq-server.onrender.com/api/incidents/panic/`** | Header: `Authorization: Token <token>`
```json
{
  "beacon_id": "beacon_001",
  "location": "Gate A"
}
```
**Response (201):**
```json
{
  "status": "success",
  "message": "Panic alert sent to guards"
}
```

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
Base URL: `https://resq-server.onrender.com/api`
- All requests use `Content-Type: application/json`
- Authorization header: `Authorization: Token <your_token>`
- Image uploads use `multipart/form-data`
- Pagination: Default 20 items per page