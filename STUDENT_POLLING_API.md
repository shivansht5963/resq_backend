# Student Incident Status Polling API

## 🎯 Overview

After a student creates an incident (via SOS or report), they can **poll the incident status** to see:
- **Guard Assignment Status** (Waiting / Assigned / No Guards Available)
- **Pending Alerts** (which guards are being contacted)
- **Guard Details** (when a guard accepts)

---

## 📡 API Endpoint

### Get Incident Status (Poll)

```http
GET /api/incidents/{incident_id}/status_poll/
Authorization: Token <student_token>
```

**Method:** GET  
**Permission:** Authenticated (Student who reported incident or Admin)  
**Rate Limit:** Can poll frequently (e.g., every 1-2 seconds for real-time updates)  

---

## 📤 Request Example

```bash
# Using cURL
curl -X GET "http://localhost:8000/api/incidents/550e8400-e29b-41d4-a716-446655440000/status_poll/" \
  -H "Authorization: Token 0ae475f9cf39e1134b4003d17a2b1b9f47b1e386" \
  -H "Content-Type: application/json"
```

```javascript
// Using JavaScript/Fetch
fetch(`http://localhost:8000/api/incidents/${incidentId}/status_poll/`, {
  method: 'GET',
  headers: {
    'Authorization': `Token ${studentToken}`,
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => {
  console.log('Incident Status:', data);
  // Use data.guard_status.status to update UI
});
```

```python
# Using Python/Requests
import requests

response = requests.get(
    f"http://localhost:8000/api/incidents/{incident_id}/status_poll/",
    headers={'Authorization': f'Token {student_token}'}
)
data = response.json()
print(f"Guard Status: {data['guard_status']['status']}")
```

---

## 📥 Response Format

### Success Response (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CREATED",
  "priority": 4,
  "description": "Medical emergency on campus",
  "report_type": "Safety Concern",
  "location": "Library Ground Floor",
  "signal_count": 1,
  
  "guard_status": {
    "status": "WAITING_FOR_GUARD",
    "message": "Searching for available guard... (2 being contacted)",
    "pending_alerts": 2
  },
  
  "guard_assignment": null,
  
  "alert_status_summary": {
    "total_alerts": 3,
    "sent": 2,
    "accepted": 0,
    "declined": 1,
    "expired": 0
  },
  
  "pending_alerts": [
    {
      "id": 1,
      "guard": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "full_name": "John Security Guard"
      },
      "priority_rank": 1,
      "alert_type": "ASSIGNMENT",
      "requires_response": true,
      "alert_sent_at": "2025-12-30T10:00:00Z",
      "response_deadline": "2025-12-30T10:00:45Z"
    },
    {
      "id": 2,
      "guard": {
        "id": "223e4567-e89b-12d3-a456-426614174111",
        "full_name": "Sarah Guard"
      },
      "priority_rank": 2,
      "alert_type": "ASSIGNMENT",
      "requires_response": true,
      "alert_sent_at": "2025-12-30T10:00:00Z",
      "response_deadline": "2025-12-30T10:00:45Z"
    }
  ],
  
  "first_signal_time": "2025-12-30T10:00:00Z",
  "last_signal_time": "2025-12-30T10:00:10Z",
  "created_at": "2025-12-30T10:00:00Z",
  "updated_at": "2025-12-30T10:00:15Z"
}
```

### Error Response (403 Forbidden)

```json
{
  "error": "You do not have permission to poll this incident"
}
```

### Error Response (404 Not Found)

```json
{
  "detail": "Not found."
}
```

---

## 🔄 Guard Status States

The `guard_status.status` field has 3 possible values:

### 1. **WAITING_FOR_GUARD**
```json
{
  "status": "WAITING_FOR_GUARD",
  "message": "Searching for available guard... (2 being contacted)",
  "pending_alerts": 2
}
```

**Meaning:** Guards are being alerted, waiting for one to accept.

**What to show:**
- Loading spinner with "Searching for guard..."
- Counter showing "2 guards being contacted"
- Maybe countdown timer to response deadline

**Transitions to:**
- `GUARD_ASSIGNED` (when a guard accepts)
- `NO_ASSIGNMENT` (if all guards decline/timeout)

---

### 2. **GUARD_ASSIGNED**
```json
{
  "status": "GUARD_ASSIGNED",
  "message": "Guard has been assigned to your incident",
  "assigned_at": "2025-12-30T10:00:15Z"
}
```

**Meaning:** A guard has accepted and is heading to location.

**What to show:**
- ✅ Success message "Guard Assigned!"
- Guard name and details (from `guard_assignment`)
- Time assigned
- Maybe map with guard location
- Chat with guard option

**Example guard_assignment:**
```json
{
  "guard_assignment": {
    "id": 99,
    "guard": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "full_name": "John Security Guard",
      "email": "john@campus.edu"
    },
    "assigned_at": "2025-12-30T10:00:15Z",
    "status": "ACTIVE"
  }
}
```

---

### 3. **NO_ASSIGNMENT**
```json
{
  "status": "NO_ASSIGNMENT",
  "message": "No guard available at this time. Admin has been notified.",
  "pending_alerts": 0
}
```

**Meaning:** All guards have declined or timeout expired. Admin notified.

**What to show:**
- ⚠️ Warning message
- "No guard available, but admin has been notified"
- Still show incident details
- Option to wait or contact admin manually

---

## 📊 Alert Status Summary

The `alert_status_summary` shows the distribution of alert states:

```json
{
  "alert_status_summary": {
    "total_alerts": 5,
    "sent": 2,       // Waiting for response
    "accepted": 1,   // Guard accepted (assignment created)
    "declined": 1,   // Guard rejected
    "expired": 1     // Timeout (no response in 45s)
  }
}
```

**Logic:**
- `sent`: Still waiting for guard response
- `accepted`: One guard will be in `guard_assignment` (other alerts expired)
- `declined`: Guard said "no thanks"
- `expired`: Guard didn't respond in 45 seconds

---

## 📱 Frontend Implementation Examples

### React Example

```javascript
import { useState, useEffect } from 'react';

export function IncidentStatusPoller({ incidentId, studentToken }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Poll every 2 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `/api/incidents/${incidentId}/status_poll/`,
          {
            headers: {
              'Authorization': `Token ${studentToken}`,
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch status');
        }

        const data = await response.json();
        setStatus(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [incidentId, studentToken]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!status) return <div>No status available</div>;

  return (
    <div className="incident-status">
      <h2>Incident Status</h2>
      
      {/* Guard Status Section */}
      <GuardStatusDisplay guardStatus={status.guard_status} />
      
      {/* Guard Assignment (if assigned) */}
      {status.guard_assignment && (
        <GuardAssignmentCard assignment={status.guard_assignment} />
      )}
      
      {/* Pending Alerts (if waiting) */}
      {status.pending_alerts.length > 0 && (
        <PendingAlertsDisplay alerts={status.pending_alerts} />
      )}
      
      {/* Alert Summary */}
      <AlertSummary summary={status.alert_status_summary} />
    </div>
  );
}

// Sub-component: Display guard status
function GuardStatusDisplay({ guardStatus }) {
  const { status, message, pending_alerts } = guardStatus;

  if (status === 'GUARD_ASSIGNED') {
    return (
      <div className="success">
        <h3>✅ Guard Assigned</h3>
        <p>{message}</p>
      </div>
    );
  }

  if (status === 'WAITING_FOR_GUARD') {
    return (
      <div className="waiting">
        <h3>⏳ Searching for Guard</h3>
        <p>{message}</p>
        <div className="loader">Contacting {pending_alerts} guards...</div>
      </div>
    );
  }

  return (
    <div className="warning">
      <h3>⚠️ No Guard Available</h3>
      <p>{message}</p>
      <p>Campus Admin has been notified and will assist shortly.</p>
    </div>
  );
}

// Sub-component: Display assigned guard
function GuardAssignmentCard({ assignment }) {
  const guard = assignment.guard;
  
  return (
    <div className="guard-card">
      <h3>Your Guard</h3>
      <p><strong>{guard.full_name}</strong></p>
      <p>Email: {guard.email}</p>
      <p>Assigned: {new Date(assignment.assigned_at).toLocaleTimeString()}</p>
      <button>Chat with Guard</button>
    </div>
  );
}

// Sub-component: Show pending alerts
function PendingAlertsDisplay({ alerts }) {
  return (
    <div className="pending-alerts">
      <h3>Guards Being Contacted</h3>
      <ul>
        {alerts.map(alert => (
          <li key={alert.id}>
            <span>{alert.priority_rank}. {alert.guard.full_name}</span>
            <span className="time">
              Expires: {new Date(alert.response_deadline).toLocaleTimeString()}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Sub-component: Alert summary stats
function AlertSummary({ summary }) {
  return (
    <div className="alert-summary">
      <h3>Alert Status</h3>
      <p>Total Alerts: {summary.total_alerts}</p>
      <p>Waiting: {summary.sent}</p>
      <p>Accepted: {summary.accepted}</p>
      <p>Declined: {summary.declined}</p>
      <p>Expired: {summary.expired}</p>
    </div>
  );
}
```

### Vue.js Example

```vue
<template>
  <div class="incident-status">
    <h2>Incident Status</h2>
    
    <!-- Loading -->
    <div v-if="loading" class="loading">Loading...</div>
    
    <!-- Error -->
    <div v-if="error" class="error">{{ error }}</div>
    
    <!-- Status Content -->
    <div v-if="status" class="content">
      <!-- Guard Status -->
      <div :class="`guard-status ${status.guard_status.status}`">
        <h3 v-if="status.guard_status.status === 'GUARD_ASSIGNED'">
          ✅ Guard Assigned
        </h3>
        <h3 v-else-if="status.guard_status.status === 'WAITING_FOR_GUARD'">
          ⏳ Searching for Guard
        </h3>
        <h3 v-else>⚠️ No Guard Available</h3>
        
        <p>{{ status.guard_status.message }}</p>
      </div>
      
      <!-- Guard Card (if assigned) -->
      <div v-if="status.guard_assignment" class="guard-card">
        <h4>{{ status.guard_assignment.guard.full_name }}</h4>
        <p>{{ status.guard_assignment.guard.email }}</p>
        <p>Assigned: {{ formatTime(status.guard_assignment.assigned_at) }}</p>
      </div>
      
      <!-- Pending Alerts (if waiting) -->
      <div v-if="status.pending_alerts.length > 0" class="pending">
        <h4>Guards Being Contacted</h4>
        <ul>
          <li v-for="alert in status.pending_alerts" :key="alert.id">
            {{ alert.priority_rank }}. {{ alert.guard.full_name }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';

export default {
  props: {
    incidentId: String,
    studentToken: String
  },
  setup(props) {
    const status = ref(null);
    const loading = ref(true);
    const error = ref(null);
    let intervalId = null;

    const fetchStatus = async () => {
      try {
        const response = await fetch(
          `/api/incidents/${props.incidentId}/status_poll/`,
          {
            headers: {
              'Authorization': `Token ${props.studentToken}`,
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) throw new Error('Failed to fetch');

        status.value = await response.json();
        loading.value = false;
      } catch (err) {
        error.value = err.message;
        loading.value = false;
      }
    };

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString();
    };

    onMounted(() => {
      fetchStatus(); // Fetch immediately
      intervalId = setInterval(fetchStatus, 2000); // Then every 2s
    });

    onUnmounted(() => {
      if (intervalId) clearInterval(intervalId);
    });

    return { status, loading, error, formatTime };
  }
};
</script>
```

---

## ⏲️ Polling Strategy

### Recommended Polling Intervals

```
Initial Phase (0-10s):    Poll every 1 second
Active Phase (10-60s):    Poll every 2 seconds
Waiting Phase (60s+):     Poll every 5 seconds
After Assignment:         Poll every 10 seconds (or stop)
```

**JavaScript:**
```javascript
function getPollingInterval(elapsedSeconds) {
  if (elapsedSeconds < 10) return 1000;      // 1 second
  if (elapsedSeconds < 60) return 2000;      // 2 seconds
  if (elapsedSeconds < 120) return 5000;     // 5 seconds
  return 10000;                              // 10 seconds
}
```

---

## 🎯 Real-World Scenario (Timeline)

### Timeline: Student Reports SOS

```
T=0s   Student clicks "SOS" → Incident created
       guard_status: WAITING_FOR_GUARD
       pending_alerts: 3 guards

T=1s   Poll... still waiting
       guard_status: WAITING_FOR_GUARD
       pending_alerts: 3 guards

T=5s   Poll... still waiting
       guard_status: WAITING_FOR_GUARD
       pending_alerts: 2 guards (1 timed out)

T=8s   Poll... Guard #1 accepted!
       guard_status: GUARD_ASSIGNED
       guard_assignment: { guard: "John", assigned_at: "..." }
       pending_alerts: [] (cleared)

T=15s  Student can see guard details
       Chat with guard opens
       Can track guard location (optional)

T=30s  Guard arrives at location
       Incident status updates to IN_PROGRESS
```

---

## 🛡️ Error Handling

```javascript
async function pollIncidentStatus(incidentId, token) {
  try {
    const response = await fetch(`/api/incidents/${incidentId}/status_poll/`, {
      headers: { 'Authorization': `Token ${token}` }
    });

    // 403: Permission denied
    if (response.status === 403) {
      console.error('Not authorized to poll this incident');
      return null;
    }

    // 404: Incident not found
    if (response.status === 404) {
      console.error('Incident not found');
      return null;
    }

    // 200: Success
    if (response.ok) {
      return await response.json();
    }

    // Other errors
    throw new Error(`HTTP ${response.status}`);
  } catch (error) {
    console.error('Polling error:', error);
    return null;
  }
}
```

---

## 📋 Complete Frontend Checklist

- [ ] Create polling component
- [ ] Set up interval (start with 2 seconds)
- [ ] Handle WAITING_FOR_GUARD state
- [ ] Handle GUARD_ASSIGNED state
- [ ] Handle NO_ASSIGNMENT state
- [ ] Display guard details when assigned
- [ ] Show pending alerts list
- [ ] Display alert summary
- [ ] Handle errors (403, 404, network)
- [ ] Stop polling after assignment (optional)
- [ ] Add timeout (stop after 5 minutes if no assignment)
- [ ] Test with multiple refreshes

---

## 🧪 Quick Test with curl

```bash
# Replace these with actual values
INCIDENT_ID="550e8400-e29b-41d4-a716-446655440000"
STUDENT_TOKEN="0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"

# Test 1: Poll incident status
curl -X GET "http://localhost:8000/api/incidents/${INCIDENT_ID}/status_poll/" \
  -H "Authorization: Token ${STUDENT_TOKEN}" \
  -H "Content-Type: application/json" | python -m json.tool

# Expected output: Full status object with guard_status, pending_alerts, etc.
```

---

## 📞 Support

**Questions?**

- Check guard_status.status for the current state
- Use pending_alerts to show which guards are being contacted
- Use guard_assignment to show assigned guard details
- Poll every 2 seconds for good balance between real-time and server load

**Hackathon Ready:** ✅
