# Complete System Architecture & Data Flow

## 📊 Database Schema (Simplified)

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER ACCOUNTS                            │
├─────────────────────────────────────────────────────────────────┤
│ User                                                             │
│ ├─ id (UUID)                                                    │
│ ├─ email                                                        │
│ ├─ full_name                                                    │
│ ├─ role: STUDENT | GUARD | ADMIN                               │
│ └─ is_active                                                    │
│                                                                 │
│ Device (for push notifications)                                │
│ ├─ id                                                           │
│ ├─ user_id (FK → User)                                          │
│ ├─ token: "ExponentPushToken[...]"                              │
│ ├─ platform: ANDROID | iOS                                     │
│ └─ is_active                                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      LOCATION MANAGEMENT                        │
├─────────────────────────────────────────────────────────────────┤
│ Beacon (physical location)                                      │
│ ├─ id (UUID)                                                    │
│ ├─ beacon_id: "safe:uuid:403:403" (hardware identifier)        │
│ ├─ location_name: "Library 3F"                                  │
│ ├─ building, floor                                              │
│ └─ is_active                                                    │
│                                                                 │
│ GuardProfile                                                    │
│ ├─ user_id (FK → User, GUARD)                                   │
│ ├─ current_beacon_id (FK → Beacon)                              │
│ ├─ is_available: boolean                                        │
│ └─ is_active                                                    │
│                                                                 │
│ BeaconProximity (expanding radius search)                       │
│ ├─ from_beacon_id → to_beacon_id                                │
│ └─ priority (search order)                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    INCIDENT MANAGEMENT                          │
├─────────────────────────────────────────────────────────────────┤
│ Incident                                                        │
│ ├─ id (UUID)                                                    │
│ ├─ beacon_id (FK → Beacon)                                      │
│ ├─ status: CREATED | ASSIGNED | IN_PROGRESS | RESOLVED         │
│ ├─ priority: 1-5 (1=LOW, 5=CRITICAL)                            │
│ ├─ description, location, report_type                           │
│ ├─ first_signal_time, last_signal_time                          │
│ └─ created_at, updated_at                                       │
│                                                                 │
│ IncidentSignal (deduplication)                                  │
│ ├─ id                                                           │
│ ├─ incident_id (FK → Incident)                                  │
│ ├─ signal_type: STUDENT_SOS | AI_VISION | AI_AUDIO | etc       │
│ ├─ source_user_id (FK → User) - who reported                    │
│ └─ created_at                                                   │
│                                                                 │
│ IncidentImage                                                   │
│ ├─ id                                                           │
│ ├─ incident_id (FK → Incident)                                  │
│ └─ image (file path)                                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ALERT MANAGEMENT                             │
├─────────────────────────────────────────────────────────────────┤
│ GuardAlert (who gets notified)                                  │
│ ├─ id                                                           │
│ ├─ incident_id (FK → Incident)                                  │
│ ├─ guard_id (FK → User, GUARD)                                  │
│ ├─ alert_type: ASSIGNMENT | BROADCAST                           │
│ ├─ status: SENT | ACCEPTED | DECLINED | EXPIRED                │
│ ├─ distance_km (from guard to incident)                         │
│ ├─ priority_rank (1=nearest, 2=second, etc)                     │
│ ├─ alert_sent_at                                                │
│ ├─ response_deadline (5 min from creation)                      │
│ └─ updated_at                                                   │
│                                                                 │
│ GuardAssignment (guard officially assigned)                    │
│ ├─ id                                                           │
│ ├─ incident_id (FK → Incident) UNIQUE                           │
│ ├─ guard_id (FK → User, GUARD) UNIQUE                           │
│ ├─ is_active                                                    │
│ └─ created_at, updated_at                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  COMMUNICATION MANAGEMENT                       │
├─────────────────────────────────────────────────────────────────┤
│ Conversation (between student and guard)                        │
│ ├─ id                                                           │
│ ├─ incident_id (FK → Incident)                                  │
│ ├─ student_id (FK → User, STUDENT)                              │
│ ├─ guard_id (FK → User, GUARD)                                  │
│ └─ created_at                                                   │
│                                                                 │
│ Message                                                         │
│ ├─ id                                                           │
│ ├─ conversation_id (FK → Conversation)                          │
│ ├─ sender_id (FK → User)                                        │
│ ├─ content (text)                                               │
│ ├─ read: boolean                                                │
│ └─ created_at                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Data Flow

### Timeline: Student SOS → Guard Assignment → Resolution

```
T+0s    STUDENT REPORTS SOS
        │
        ├─ POST /api/incidents/report_sos/
        │  {beacon_id: "safe:uuid:403:403", description: "..."}
        │
        ├─ Backend:
        │  ├─ Validate beacon (active?)
        │  ├─ Check existing incident (within 5 min dedup window?)
        │  ├─ Create Incident (status=CREATED, priority=5)
        │  ├─ Create IncidentSignal (type=STUDENT_SOS)
        │  └─ Call: alert_guards_for_incident(incident)
        │
        └─ DATABASE WRITES:
           ├─ Incident { id, beacon_id, status=CREATED, priority=5 }
           └─ IncidentSignal { incident_id, signal_type, source_user_id }

T+1s    FIND & ALERT GUARDS
        │
        ├─ Backend (security/services.py):
        │  ├─ Get incident beacon: Library 3F
        │  ├─ Search for guards via beacon proximity:
        │  │  1. Check guards at Library 3F (same beacon)
        │  │  2. Check guards at Library 4F (nearby)
        │  │  3. Check guards at Hallway 4F (further)
        │  │  4. Continue until 3-5 guards found
        │  │
        │  ├─ Skip guards who:
        │  │  - are already assigned to another incident
        │  │  - are inactive
        │  │  - are unavailable
        │  │
        │  └─ For each found guard:
        │     ├─ Create GuardAlert (status=SENT)
        │     ├─ Get guard device tokens
        │     └─ Send push notification
        │
        └─ DATABASE WRITES:
           ├─ GuardAlert #1 { incident_id, guard_id, status=SENT, priority_rank=1 }
           ├─ GuardAlert #2 { incident_id, guard_id, status=SENT, priority_rank=2 }
           └─ GuardAlert #3 { incident_id, guard_id, status=SENT, priority_rank=3 }

T+2s    PUSH NOTIFICATIONS SENT
        │
        ├─ Backend (accounts/push_notifications.py):
        │  ├─ Call: PushNotificationService.notify_guard_alert()
        │  ├─ For each guard:
        │  │  ├─ Get active device tokens
        │  │  ├─ Validate token format (ExponentPushToken[...])
        │  │  ├─ Build PushMessage via exponent_server_sdk
        │  │  ├─ Send to Expo API
        │  │  └─ Log: "Push sent to Guard Sarah Smith (ExponentPushToken[...])"
        │  │
        │  └─ Response from Expo:
        │     └─ {status: "ok", id: "push-ticket-123"}
        │
        └─ GUARD DEVICES:
           ├─ Guard #1 (Sarah): Receives 🚨 "CRITICAL - Library 3F"
           ├─ Guard #2 (John):  Receives 🚨 "CRITICAL - Library 3F"
           └─ Guard #3 (Mike):  Receives 🚨 "CRITICAL - Library 3F"

T+3-5s  GUARDS CHECK APP
        │
        ├─ Each guard opens app
        ├─ Polls: GET /api/alerts/
        │  └─ Response includes 3 new SENT alerts
        │
        └─ GUARD #1 (Sarah) DECIDES TO ACCEPT
           ├─ Taps "Accept" on Library 3F alert #1

T+6s    GUARD ACCEPTS ALERT
        │
        ├─ POST /api/alerts/1/accept/
        │  Authorization: Token {guard1_token}
        │
        ├─ Backend (in transaction):
        │  ├─ Get GuardAlert #1
        │  ├─ Validate: alert_type == ASSIGNMENT (✓)
        │  ├─ Update: GuardAlert #1 status = ACCEPTED
        │  ├─ Create: GuardAssignment {incident_id, guard_id=Sarah}
        │  ├─ Update: Incident status = ASSIGNED
        │  │  (now incident has active assignment)
        │  │
        │  ├─ Auto-decline other alerts:
        │  │  ├─ Update: GuardAlert #2 status = AUTO_DECLINED
        │  │  └─ Update: GuardAlert #3 status = AUTO_DECLINED
        │  │
        │  ├─ Create: Conversation {incident_id, student_id, guard_id=Sarah}
        │  │
        │  └─ Send push notifications:
        │     ├─ To Guard #1 (Sarah): ✅ "Assignment Confirmed"
        │     └─ To Student: 🚨 "Guard Sarah Smith assigned (300m away)"
        │
        └─ DATABASE WRITES:
           ├─ GuardAlert #1 { status = ACCEPTED }
           ├─ GuardAlert #2 { status = AUTO_DECLINED }
           ├─ GuardAlert #3 { status = AUTO_DECLINED }
           ├─ GuardAssignment { incident_id, guard_id=Sarah, is_active=true }
           ├─ Incident { status = ASSIGNED }
           └─ Conversation { incident_id, student_id, guard_id=Sarah }

T+7s    STUDENT APP UPDATES
        │
        ├─ Student polls: GET /api/incidents/{incident_id}/
        │  └─ Response shows:
        │     ├─ status: "ASSIGNED"
        │     ├─ guard_assignment: {guard: "Sarah Smith", distance: 300m}
        │     └─ conversation: {id: 42, created}
        │
        ├─ Student app UI updates:
        │  ├─ Status bar: 🟡 "Guard Sarah Smith assigned (300m away)"
        │  └─ Chat section opens with empty conversation
        │
        └─ Student receives push: 🚨 "Guard Sarah Smith assigned (ETA 2 min)"

T+10-20s GUARD EN ROUTE - LOCATION UPDATES
        │
        ├─ Guard app polls: POST /api/guards/update_location/
        │  {nearest_beacon_id: "safe:uuid:402:402", timestamp: "..."}
        │
        ├─ Backend:
        │  ├─ Update GuardProfile.current_beacon_id
        │  ├─ Calculate new distance (200m, 150m, 100m...)
        │  └─ Log location update
        │
        ├─ Student polls: GET /api/incidents/{incident_id}/
        │  └─ Response updates distance (300m → 200m → 100m...)
        │
        └─ Student app shows: 🚨 "Guard 100m away, ETA 1 min"

T+25s   GUARD SENDS MESSAGE
        │
        ├─ Guard: "I'm here, in the lobby"
        ├─ POST /api/conversations/42/send_message/
        │  {content: "I'm here, in the lobby"}
        │
        ├─ Backend:
        │  ├─ Create Message { conversation_id, sender_id=Sarah, content }
        │  ├─ Send push to Student: 💬 "Sarah: I'm here, in the lobby"
        │  └─ Log: "Message sent from Sarah to Student"
        │
        └─ Student receives push + polls for messages

T+30s   INCIDENT RESOLVED
        │
        ├─ Guard: POST /api/incidents/{incident_id}/resolve/
        │
        ├─ Backend:
        │  ├─ Update Incident { status = RESOLVED }
        │  ├─ Deactivate GuardAssignment { is_active = false }
        │  └─ Send push to both:
        │     ├─ Guard: ✅ "Incident resolved"
        │     └─ Student: ✅ "Incident resolved"
        │
        └─ Both apps show: ✅ "RESOLVED"
```

---

## 🔌 API Endpoints Overview

### By Phase

**Phase 1: Student Reports**
```
POST /api/incidents/report_sos/          ← Creates incident, alerts guards
```

**Phase 2: Guard Gets Alert**
```
GET /api/alerts/                         ← Guard polls for alerts
GET /api/alerts/{id}/                    ← Guard sees alert details
```

**Phase 3: Guard Responds**
```
POST /api/alerts/{id}/accept/            ← Accept & create assignment
POST /api/alerts/{id}/decline/           ← Decline & try next guard
```

**Phase 4: En Route**
```
POST /api/guards/update_location/        ← Guard updates beacon location
GET /api/incidents/{id}/                 ← Student/Guard tracks progress
```

**Phase 5: Communication**
```
GET /api/conversations/{id}/             ← Get conversation
GET /api/conversations/{id}/messages/    ← Get all messages
POST /api/conversations/{id}/send_message/ ← Send message
```

**Phase 6: Resolution**
```
POST /api/incidents/{id}/resolve/        ← Mark incident resolved
```

---

## 🚀 Real-World Deployment Considerations

### Database Indexes
```sql
-- For fast incident lookups
CREATE INDEX idx_incident_status ON incidents_incident(status);
CREATE INDEX idx_incident_beacon ON incidents_incident(beacon_id);
CREATE INDEX idx_incident_created ON incidents_incident(created_at DESC);

-- For fast alert lookups
CREATE INDEX idx_guardalert_incident ON security_guardalert(incident_id);
CREATE INDEX idx_guardalert_guard ON security_guardalert(guard_id);
CREATE INDEX idx_guardalert_status ON security_guardalert(status);

-- For fast assignment lookups
CREATE INDEX idx_guardassignment_incident ON security_guardassignment(incident_id);
CREATE INDEX idx_guardassignment_active ON security_guardassignment(is_active);
```

### Performance Optimization
```python
# Use select_related for foreign keys
Incident.objects.select_related('beacon')
GuardAlert.objects.select_related('guard', 'incident')

# Use prefetch_related for reverse relations
Incident.objects.prefetch_related('guard_alerts', 'guard_assignments')
```

### Monitoring
```
Key metrics to monitor:
- Average response time (student SOS → guard accept)
- Alerts created per incident
- Alert decline rate (should be low)
- Push notification success rate (should be >95%)
- Average distance of assigned guard
- Number of active assignments
```

---

## 📝 Key Business Rules

1. **One assignment per incident**
   - Only ONE active GuardAssignment per Incident
   - Prevents multiple guards responding to same incident

2. **Incident deduplication**
   - Signals within 5 min at same beacon → same incident
   - Prevents duplicate alerts

3. **Guard availability**
   - Guard can't accept new alert if already assigned
   - Prevents overloading guards

4. **Alert escalation**
   - ASSIGNMENT alerts → requires response
   - 5-minute response deadline
   - Auto-escalate if no response (try next guard)

5. **Beacon proximity search**
   - Expanding radius: start at incident beacon
   - Then nearby beacons (by priority order)
   - Continue until max_guards found

---

## ✅ System Readiness Checklist

- [x] Database schema correct
- [x] Models have all relationships
- [x] Serializers return full guard_alerts
- [x] Alert creation logic implemented
- [x] Push notification service integrated (exponent_server_sdk)
- [x] Student polling endpoint returns tracking info
- [x] Guard accept/decline endpoints work
- [x] Assignment creation on accept
- [x] Conversation auto-creation
- [x] Message notifications sent
- [x] Logging throughout

**✅ System is ready for production use.**
