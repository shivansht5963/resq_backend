# Student Polling API - Integration Guide

## 🎯 Real-World Use Case

**Scenario:** Student presses SOS → App polls backend every 2 seconds → Shows "Searching..." → Guard accepts → App instantly shows guard details (name, email, chat button) → Student can contact guard immediately.

---

## 📡 API Request

```http
GET /api/incidents/550e8400-e29b-41d4-a716-446655440000/status_poll/ HTTP/1.1
Host: localhost:8000
Authorization: Token 0ae475f9cf39e1134b4003d17a2b1b9f47b1e386
Content-Type: application/json
```

**Poll Interval:** 2 seconds (adjust based on UX needs)

---

## 📥 Response - Status 200 OK

**Case 1: Still Searching (WAITING_FOR_GUARD)**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CREATED",
  "priority": 4,
  "guard_status": {
    "status": "WAITING_FOR_GUARD",
    "message": "Searching for available guard... (2 being contacted)",
    "pending_alerts": 2
  },
  "guard_assignment": null,
  "pending_alerts": [
    {
      "id": 1,
      "guard": {
        "id": "user-001",
        "full_name": "John Security Guard"
      },
      "priority_rank": 1,
      "response_deadline": "2025-12-30T10:00:45Z"
    },
    {
      "id": 2,
      "guard": {
        "id": "user-002",
        "full_name": "Sarah Guard"
      },
      "priority_rank": 2,
      "response_deadline": "2025-12-30T10:00:50Z"
    }
  ]
}
```

**Case 2: Guard Assigned (GUARD_ASSIGNED)** ✅
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CREATED",
  "priority": 4,
  "guard_status": {
    "status": "GUARD_ASSIGNED",
    "message": "Guard assigned and on the way",
    "pending_alerts": 0
  },
  "guard_assignment": {
    "id": "assign-001",
    "guard": {
      "id": "user-001",
      "full_name": "John Security Guard",
      "email": "john.guard@campus.edu"
    },
    "assigned_at": "2025-12-30T10:00:15Z",
    "is_active": true
  },
  "pending_alerts": []
}
```

**Case 3: No Guard Available (NO_ASSIGNMENT)**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CREATED",
  "priority": 4,
  "guard_status": {
    "status": "NO_ASSIGNMENT",
    "message": "No guards available in your area",
    "pending_alerts": 0
  },
  "guard_assignment": null,
  "pending_alerts": []
}
```

---

## 🔄 Status Flow & UI Actions

| Status | Show | Action |
|--------|------|--------|
| `WAITING_FOR_GUARD` | Spinner + "Searching..." | Keep polling |
| `GUARD_ASSIGNED` | Guard name + email + chat button | Open chat, stop polling (optional) |
| `NO_ASSIGNMENT` | ⚠️ "No guard available" | Retry or contact admin |

---

## 💻 Basic Implementation

```javascript
// Start polling when SOS sent
const startPolling = (incidentId, token) => {
  const interval = setInterval(async () => {
    const res = await fetch(
      `http://localhost:8000/api/incidents/${incidentId}/status_poll/`,
      { headers: { 'Authorization': `Token ${token}` } }
    );
    const data = await res.json();
    
    // Guard assigned - show instantly
    if (data.guard_assignment) {
      displayGuardCard(data.guard_assignment.guard);
      clearInterval(interval); // stop polling
    }
    
    // Still waiting
    else if (data.guard_status.status === 'WAITING_FOR_GUARD') {
      updateStatus(`Contacting guards... (${data.guard_status.pending_alerts} pending)`);
    }
    
    // No guards available
    else {
      showError('No guards available. Contact admin.');
    }
  }, 2000);
};

// Guard card display
const displayGuardCard = (guard) => {
  console.log(`✅ Guard assigned: ${guard.full_name}`);
  console.log(`📧 Email: ${guard.email}`);
  console.log(`💬 Open chat now`);
};
```

---

## ⚙️ Backend Guarantees

✅ **Instant display**: Guard details sent immediately when accepted  
✅ **Auto-escalation**: 45s timeout → next guard contacted  
✅ **Priority-based**: Critical (5 guards) → High (3) → Medium (2)  
✅ **Permission check**: Only incident reporter or admin can poll  

---

## 🚀 Real-World Flow

1. Student taps SOS
2. App creates incident, gets incident ID
3. App starts polling `/status_poll/` every 2 seconds
4. Backend searches guards via beacon proximity
5. Guard receives alert, taps "Accept"
6. Next poll returns `guard_assignment` with full details
7. App displays guard card with name + email + chat button
8. Student contacts guard or waits for arrival
