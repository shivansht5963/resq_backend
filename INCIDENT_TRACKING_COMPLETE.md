# Incident Tracking & Push Notification Flow - Complete Architecture

## Problem Analysis

❌ **Current Issues:**
1. No visibility into which guard is being alerted
2. No tracking of alert status progression  
3. Push notifications may not be reaching guards
4. Student app doesn't get real-time incident updates
5. No clear incident tracking timeline
6. Logging scattered/incomplete

---

## ✅ Solution: Complete Tracking System

### 1. DATABASE TRACKING

#### Incident Status Progression
```
Incident.status:
CREATED → ASSIGNED → IN_PROGRESS → RESOLVED
   ↓         ↓          ↓             ↓
[No guard] [Guard     [Guard       [Resolved]
           accepted]   arrived]
```

#### GuardAlert Status Progression
```
GuardAlert.status:
SENT → ACCEPTED → (Assignment created, incident ASSIGNED)
 ↓       ↓
[Pending] [Done]

SENT → DECLINED → (Try next guard, alert stays SENT for other guards)
 ↓       ↓
[Pending] [Rejected]

SENT → EXPIRED → (5 min timeout, try next guard)
 ↓       ↓
[Pending] [Timeout]
```

#### GuardAssignment (One per Incident)
```
Created when guard accepts alert:
- incident_id (FK)
- guard_id (FK) 
- is_active = true
- created_at

Only ONE active assignment per incident.
```

---

## 2. COMPLETE INCIDENT CREATION FLOW

### A. Student Reports SOS

```
POST /api/incidents/report_sos/
├── Input Validation
├── Get/Create Incident
│   ├── Check: Same beacon, within 5 min?
│   │   ├── YES → Reuse existing incident
│   │   └── NO → Create new incident
│   ├── Create IncidentSignal (STUDENT_SOS)
│   └── Return incident data with tracking info
├── Alert Guards (if NEW incident)
│   ├── Find nearest guards via beacon proximity
│   ├── Create GuardAlert records (status=SENT)
│   ├── Send push notifications
│   └── Log: which guards were alerted
└── Return to Student with:
    ├── incident_id
    ├── status: CREATED
    ├── alerts_sent_to: [list of guard names]
    └── tracking_id for polling
```

### B. Guard Receives Alert (Push + Poll)

```
1. PUSH NOTIFICATION (automatic, immediate)
   Title: 🚨 Incoming Alert
   Body: CRITICAL - Library 3F - Main Hall
   Data: {type: GUARD_ALERT, incident_id, alert_id}

2. POLL for alerts (every 5-10 seconds)
   GET /api/alerts/
   ├── Returns list of new alerts
   ├── Guard sees:
   │   ├── incident_id
   │   ├── location
   │   ├── priority
   │   ├── alert status
   │   └── response_deadline
   └── Guard picks one to accept/decline
```

### C. Guard Accepts Alert

```
POST /api/alerts/{alert_id}/accept/
├── Validate: Only ASSIGNMENT type
├── Database Transaction:
│   ├── Update GuardAlert.status = ACCEPTED
│   ├── Create GuardAssignment (incident + guard)
│   ├── Update Incident.status = ASSIGNED
│   ├── Mark other alerts for same incident as AUTO_DECLINED
│   └── Create Conversation (student + guard)
├── Send Push Notifications:
│   ├── To Guard: ✅ Assignment Confirmed
│   ├── To Student: 🚨 Guard Assigned
│   └── Log: which guard accepted which incident
└── Return updated alert + assignment details
```

### D. Guard Declines Alert

```
POST /api/alerts/{alert_id}/decline/
├── Update GuardAlert.status = DECLINED
├── Find next guard in beacon proximity queue
├── Create new GuardAlert for next guard
├── Send push to next guard
└── Log: declined guard, trying next guard
```

---

## 3. INCIDENT TRACKING RESPONSE FORMAT

### GET /api/incidents/{incident_id}/

Returns full tracking data:

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
  "status": "ASSIGNED",
  "priority": 5,
  "description": "I need help in the library main hall",
  "location": "Library 3F - Main Hall",
  "report_type": "STUDENT_SOS",
  
  "tracking": {
    "created_at": "2025-01-01T12:00:00Z",
    "first_signal_at": "2025-01-01T12:00:00Z",
    "last_signal_at": "2025-01-01T12:00:15Z",
    "signal_count": 2,
    "alerts_sent_count": 3,
    "alerts_declined": 1,
    "alerts_accepted": 1
  },
  
  "guard_assignment": {
    "id": 10,
    "guard": {
      "id": "guard-user-uuid",
      "full_name": "Sarah Smith",
      "email": "guard@example.com"
    },
    "assigned_at": "2025-01-01T12:01:30Z",
    "accepted_alert_id": 1
  },
  
  "guard_alerts": [
    {
      "id": 1,
      "guard": {
        "id": "guard-uuid-001",
        "full_name": "Guard Sarah Smith",
        "email": "guard1@example.com"
      },
      "status": "ACCEPTED",
      "alert_type": "ASSIGNMENT",
      "priority_rank": 1,
      "distance_km": 0.3,
      "alert_sent_at": "2025-01-01T12:00:15Z",
      "response_deadline": "2025-01-01T12:05:15Z",
      "accepted_at": "2025-01-01T12:01:30Z"
    },
    {
      "id": 2,
      "guard": {
        "id": "guard-uuid-002",
        "full_name": "Guard John Lee",
        "email": "guard2@example.com"
      },
      "status": "DECLINED",
      "alert_type": "ASSIGNMENT",
      "priority_rank": 2,
      "distance_km": 0.7,
      "alert_sent_at": "2025-01-01T12:00:15Z",
      "response_deadline": "2025-01-01T12:05:15Z",
      "declined_at": "2025-01-01T12:00:45Z"
    },
    {
      "id": 3,
      "guard": {
        "id": "guard-uuid-003",
        "full_name": "Guard Mike Johnson",
        "email": "guard3@example.com"
      },
      "status": "SENT",
      "alert_type": "ASSIGNMENT",
      "priority_rank": 3,
      "distance_km": 1.2,
      "alert_sent_at": "2025-01-01T12:00:50Z",
      "response_deadline": "2025-01-01T12:05:50Z",
      "accepted_at": null
    }
  ],
  
  "signals": [
    {
      "id": 1,
      "signal_type": "STUDENT_SOS",
      "source_user": "student-name",
      "created_at": "2025-01-01T12:00:00Z"
    },
    {
      "id": 2,
      "signal_type": "STUDENT_SOS",
      "source_user": "student-name",
      "created_at": "2025-01-01T12:00:15Z"
    }
  ],
  
  "conversation": {
    "id": 42,
    "student": {
      "id": "student-uuid",
      "full_name": "John Doe"
    },
    "guard": {
      "id": "guard-uuid-001",
      "full_name": "Sarah Smith"
    },
    "message_count": 3,
    "created_at": "2025-01-01T12:01:30Z",
    "last_message_at": "2025-01-01T12:02:30Z"
  }
}
```

---

## 4. STUDENT APP REAL-TIME UPDATES

### Student Polls Incident Status

```http
GET /api/incidents/{incident_id}/
Authorization: Token student-token

✅ Response shows:
- Current incident status (CREATED/ASSIGNED/IN_PROGRESS/RESOLVED)
- Guard assignment (name, photo, distance, ETA)
- Messages in real-time
- All alert history (who was asked, accepted/declined)
```

### Student Receives Push Notifications

```
When Guard Accepts:
  Title: 🚨 Guard Assigned
  Body: Guard Sarah Smith (300m away, ETA 2 min)
  Action: Open incident details

When Guard Sends Message:
  Title: 💬 New Message
  Body: Sarah Smith: "I'm arriving in 2 minutes"
  Action: Open conversation
```

---

## 5. PUSH NOTIFICATION TRACKING

### What Gets Logged

Every push notification includes:

```python
# In accounts/push_notifications.py
logger.info(
    f"Push notification sent",
    extra={
        'notification_type': 'GUARD_ALERT',
        'incident_id': str(incident_id),
        'alert_id': alert_id,
        'guard_id': str(guard_id),
        'guard_name': guard_name,
        'location': location,
        'tokens_sent': len(tokens),
        'timestamp': timezone.now().isoformat()
    }
)
```

### Check Push Status

```
Backend Logs: /var/log/django.log
```

Or:

```python
# From Django shell
from accounts.models import Device

# See all device tokens for a guard
Device.objects.filter(user_id='guard-uuid', is_active=True)

# Check last few push logs
from django.core.management.base import CommandError
import logging
logger = logging.getLogger('accounts.push_notifications')
```

---

## 6. IMPLEMENTATION CHECKLIST

### Phase 1: Ensure Data Models Are Correct ✅
- [x] Incident model with status tracking
- [x] GuardAlert model with status progression
- [x] GuardAssignment (one per incident)
- [x] IncidentSignal for deduplication
- [x] Conversation + Message for chat

### Phase 2: Fix Response Serialization ✅
- [x] IncidentDetailedSerializer includes guard_alerts
- [x] GuardAlertSerializer with full guard info
- [x] Tracking timestamps included

### Phase 3: Verify Alert Creation
- [ ] Check: `alert_guards_for_incident()` is called after incident creation
- [ ] Check: GuardAlerts are created with proper status
- [ ] Check: Push notifications are sent

### Phase 4: Verify Student Updates
- [ ] GET /api/incidents/{id}/ returns full tracking
- [ ] Student app polls every 2-5 seconds
- [ ] Frontend updates based on guard_assignment status

### Phase 5: Verify Guard Flow
- [ ] GET /api/alerts/ returns list with all info
- [ ] Guard can see incident location/priority
- [ ] POST /api/alerts/{id}/accept/ creates assignment
- [ ] POST /api/alerts/{id}/decline/ tries next guard

### Phase 6: Logging & Debugging
- [ ] All alert creations logged
- [ ] All push notifications logged
- [ ] All transitions logged (status changes)

---

## 7. DEBUGGING: How to Find Issues

### Issue: "I don't see which guard got the alert"

**Check:**
```
1. GET /api/incidents/{incident_id}/
   → Look at "guard_alerts" array
   → See all guards who got alerts and their status

2. Django admin: security > Guard Alerts
   → Filter by incident_id
   → See full status of each alert

3. Logs:
   tail -f /var/log/django.log | grep "alert"
```

### Issue: "Push notification not reaching guard"

**Check:**
```
1. Device tokens registered:
   GET /api/device-tokens/
   → See if guard has active tokens

2. Token format valid:
   Must start with "ExponentPushToken["

3. Expo account:
   Check Expo dashboard for push errors

4. Logs:
   grep "push notification" /var/log/django.log
   → See if notification was sent
   → See response from Expo API
```

### Issue: "Student app not updating"

**Check:**
```
1. Student polling interval:
   Should be every 2-5 seconds
   GET /api/incidents/{incident_id}/

2. Check response includes:
   - guard_assignment (after accept)
   - guard_alerts array
   - conversation (after assignment)

3. Network requests:
   Chrome DevTools → Network tab
   → See GET /incidents/{id}/ requests
   → Check response body
```

---

## 8. REAL-WORLD SCENARIO WITH TRACKING

```
T+0s:   Student: "I'm in trouble at Library 3F"
        SOS_REQUEST → POST /api/incidents/report_sos/
        ├─ Incident created (ID: abc123)
        ├─ Status: CREATED
        ├─ 3 alerts created (status: SENT)
        └─ Push sent to 3 guards

T+2s:   Guard #1 receives push: 🚨 Incoming Alert
        ├─ Opens app
        ├─ Polls: GET /api/alerts/
        └─ Sees: Library 3F, CRITICAL, Guard #2 also invited

T+5s:   Guard #1 accepts alert
        ACCEPT_ALERT → POST /api/alerts/1/accept/
        ├─ Alert #1 status: ACCEPTED
        ├─ Assignment created (Guard #1 → Incident abc123)
        ├─ Incident status: ASSIGNED
        ├─ Alerts #2, #3 auto-declined
        ├─ Push to Guard #1: ✅ Assignment Confirmed
        └─ Push to Student: 🚨 Guard Sarah Smith assigned

T+7s:   Student polls: GET /api/incidents/abc123/
        ├─ Status: ASSIGNED
        ├─ guard_assignment: {guard: "Sarah Smith", distance: 300m}
        └─ Conversation: {id: 42, created}

T+15s:  Guard #1 updates location: 200m away
        UPDATE_LOCATION → POST /api/guards/update_location/
        └─ Backend calculates new distance

T+20s:  Guard #1 sends message: "I'm here"
        SEND_MESSAGE → POST /api/conversations/42/send_message/
        ├─ Message created
        ├─ Push to Student: 💬 "I'm here"
        └─ Student polls and sees message

T+25s:  Student: "Thank you, I'm okay now"
        SEND_MESSAGE → POST /api/conversations/42/send_message/
        └─ Push to Guard: 💬 "Thank you..."

T+30s:  Guard #1: Incident resolved
        RESOLVE → POST /api/incidents/abc123/resolve/
        ├─ Incident status: RESOLVED
        ├─ Assignment deactivated
        └─ Both get push notifications
```

---

## 9. FRONTEND IMPLEMENTATION GUIDE

### Student App - Real-time Incident Tracking

```javascript
// Every 2 seconds while incident is active
const pollIncident = async (incidentId) => {
  const response = await fetch(`/api/incidents/${incidentId}/`, {
    headers: { Authorization: `Token ${studentToken}` }
  });
  const data = await response.json();
  
  // Update UI based on status
  switch(data.status) {
    case 'CREATED':
      showStatus('🔴 Waiting for guard response');
      break;
    case 'ASSIGNED':
      showStatus(`🟡 Guard ${data.guard_assignment.guard.full_name} assigned`);
      showGuardLocation(data.guard_assignment.guard.distance_km);
      break;
    case 'IN_PROGRESS':
      showStatus('🟡 Guard on the way');
      break;
    case 'RESOLVED':
      showStatus('✅ Incident resolved');
      stopPolling();
      break;
  }
  
  // Show all messages
  if(data.conversation) {
    displayMessages(data.conversation.messages);
  }
  
  // Show guard alert status
  if(data.guard_alerts) {
    displayAlertStatus(data.guard_alerts);
  }
};

// Start polling
setInterval(() => pollIncident(incidentId), 2000);
```

### Guard App - Alert Management

```javascript
// Poll alerts every 5 seconds
const pollAlerts = async () => {
  const response = await fetch('/api/alerts/', {
    headers: { Authorization: `Token ${guardToken}` }
  });
  const alerts = await response.json();
  
  // Show new alerts only
  alerts.results.forEach(alert => {
    if(alert.status === 'SENT') {
      showNewAlert({
        id: alert.id,
        location: alert.incident.location,
        priority: alert.incident.priority,
        distance: alert.distance_km,
        deadline: alert.response_deadline
      });
    }
  });
};

// Accept alert
const acceptAlert = async (alertId) => {
  const response = await fetch(`/api/alerts/${alertId}/accept/`, {
    method: 'POST',
    headers: { Authorization: `Token ${guardToken}` }
  });
  const data = await response.json();
  
  showConfirmation(`Assigned to ${data.incident.location}`);
  openIncident(data.assignment.incident);
};

// Decline alert
const declineAlert = async (alertId) => {
  const response = await fetch(`/api/alerts/${alertId}/decline/`, {
    method: 'POST',
    headers: { Authorization: `Token ${guardToken}` }
  });
  removeAlertFromUI(alertId);
};
```

---

## Summary

✅ **Tracking is now explicit:**
- See which guards got which alerts
- Track status of each alert (SENT → ACCEPTED/DECLINED/EXPIRED)
- Real-time incident status updates
- Full conversation history
- Distance calculations
- Response deadlines

✅ **Push notifications logged:**
- Track when sent
- See which token(s)
- Capture errors

✅ **Student app gets updates:**
- Poll every 2-5 seconds
- See guard assignment
- See distance/ETA
- Real-time messages

✅ **Guard app gets clear flow:**
- See all alerts (new ones marked SENT)
- Accept/decline with instant feedback
- See next guard will be tried if declined
