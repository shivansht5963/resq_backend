# Guard Assignment Flow Documentation

## Overview
This document explains how guards are assigned to incidents, how they are notified, and how the system handles acceptances and rejections.

---

## 1. INCIDENT CREATED → GUARD ALERT SENT

### 1.1 When Incident is Created
An incident is created when:
- Student presses SOS button (STUDENT_SOS signal)
- Panic button is activated (PANIC_BUTTON signal)
- AI detects violence (VIOLENCE_DETECTED signal)
- AI detects screaming (SCREAM_DETECTED signal)
- Admin manually creates incident

### 1.2 How Guards Are Selected (Beacon-Proximity Search)

**Goal:** Find 3 available guards nearest to incident location using beacon proximity expansion.

**Process:**
```
Step 1: Get Incident Beacon Location
   └─ Where did incident occur?

Step 2: Expanding-Radius Search
   ├─ Level 1: Search guards at INCIDENT BEACON
   │          (Find available guards assigned to this location)
   │
   ├─ Level 2: If <3 guards found, expand to NEARBY BEACONS
   │          (Use BeaconProximity table for priority order)
   │
   └─ Level 3: Continue expanding until 3 guards found or all beacons exhausted

Step 3: Filter Guards
   ├─ Guard must be is_active=True (on duty)
   ├─ Guard must be is_available=True (not handling other incidents)
   ├─ Guard must not already be alerted for THIS incident
   └─ Guard must not be assigned to ANOTHER active incident
```

**Example:**
```
Incident at Library (Beacon A)
↓
Search Level 1: Library (Beacon A)
  → Guard John (distance 0m) ✓
  → Guard Sarah (distance 0m) ✓
  
Found 2 guards. Need 1 more.
↓
Search Level 2: Nearby Beacons (by priority)
  → Cafeteria (Beacon B) - priority 1
    → Guard Ahmed (distance 50m) ✓
  
Found 3 guards total. STOP SEARCH.
```

### 1.3 Decision Making for Each Guard
For EACH guard to be alerted, system checks:

| Check | Condition | Action |
|-------|-----------|--------|
| Active on Duty? | `is_active = True` | Skip if False |
| Available Now? | `is_available = True` | Skip if False (busy with another incident) |
| Already Alerted? | Not in GuardAlert table | Skip if already sent/acknowledged/declined alert |
| Assigned Elsewhere? | No active GuardAssignment to other incident | Skip if busy |

### 1.4 How Guards Are Notified (Push Notification)

**What Happens:**
1. System creates `GuardAlert` record (status = "SENT")
2. Retrieves guard's `DeviceToken` (FCM token for Android/iOS)
3. Sends **Push Notification** with:
   - Incident details (location, type, priority)
   - Incident ID
   - Map coordinates (beacon location)
   - "ACCEPT" and "REJECT" buttons

**Example Notification:**
```
🚨 NEW INCIDENT ALERT
Location: Library Ground Floor
Type: Panic Button Activated
Priority: CRITICAL
Action: [ACCEPT] [REJECT]
```

---

## 2. GUARD ACCEPTS ASSIGNMENT ✓

### 2.1 Flow When Guard Taps "ACCEPT"

```
Guard taps ACCEPT button
        ↓
POST /api/guard-alerts/{alert_id}/acknowledge/
        ↓
System validates guard is still available
        ↓
Create GuardAssignment
  ├─ incident_id = [incident]
  ├─ guard = [guard user]
  ├─ is_active = True
  └─ assigned_at = NOW
        ↓
Update GuardAlert
  ├─ status = "ACKNOWLEDGED"
  └─ assignment = [link to new GuardAssignment]
        ↓
Update Incident Status
  ├─ status = CREATED → ASSIGNED
  ├─ Message: "Guard assigned to incident"
  └─ Incident now has active guardian
        ↓
EXPIRE all other alerts for this incident
  ├─ Set all other GuardAlert status = "EXPIRED"
  ├─ Notification: "Another guard accepted"
  └─ Other guards' ACCEPT/REJECT buttons become disabled
        ↓
Guard receives confirmation
  ├─ "Assignment confirmed - head to location"
  ├─ Real-time map link
  └─ Incident chat opens (for guard-admin communication)
```

### 2.2 What Happens After Acceptance

**Guard Can Now:**
- View incident details
- See live map to incident location
- Chat with incident coordinator
- Update incident status (arriving, on-site, resolved)
- Receive real-time updates if new signals arrive

**Incident Status:**
- Status changes to `ASSIGNED`
- No new guards will be alerted
- If new signals arrive at same location:
  - New signal added to SAME incident
  - Priority may escalate
  - **Same guard remains assigned** (unless resolves/escalates)

**System Behavior:**
```
Guard Accepted ✓
  ├─ GuardAssignment.is_active = True
  ├─ Incident.status = ASSIGNED
  ├─ No more alerts sent to other guards
  └─ Guard is "locked in" until incident resolves/reassigns
```

---

## 3. GUARD REJECTS ASSIGNMENT ✗

### 3.1 Flow When Guard Taps "REJECT"

```
Guard taps REJECT button
        ↓
POST /api/guard-alerts/{alert_id}/decline/
        ↓
Update GuardAlert
  ├─ status = "DECLINED"
  └─ Guard marked as declined (not interested)
        ↓
Get Already-Declined Guards
  ├─ Find all guards who declined this incident
  └─ Add their IDs to exclusion list
        ↓
Continue Beacon-Proximity Search
  ├─ Same expansion logic as original search
  ├─ BUT: Skip guards in exclusion list
  └─ Find NEXT available guard
        ↓
IF next guard found:
  ├─ Create NEW GuardAlert for next guard
  ├─ Send notification: "New incident - accept or reject?"
  └─ Repeat process (they can also accept/reject)
        ↓
IF NO next guard available:
  ├─ Log warning: "All guards exhausted/declined"
  ├─ Incident remains CREATED (not assigned)
  ├─ Admin notified: "No guards available"
  └─ Escalate to manual assignment or admin response
```

### 3.2 What Happens After Rejection

**System Behavior:**
```
Guard Rejected ✗
  ├─ GuardAlert.status = "DECLINED"
  ├─ Alert NOT linked to assignment (no assignment created)
  ├─ Incident status stays CREATED (not assigned)
  └─ Search for next guard (expanding radius continues)
```

**Guard Can:**
- Continue doing other work
- Not involved in this incident anymore
- May receive alerts for OTHER incidents

**If All Guards Decline:**
```
Exhausted/Declined for Incident #123
  ├─ No assignment created
  ├─ Incident stays in CREATED status
  ├─ Admin gets notification
  ├─ Admin options:
  │  ├─ Manually assign a specific guard
  │  ├─ Escalate to emergency services
  │  └─ Keep on pending queue
  └─ Timeout: If no assignment after X minutes → escalate
```

---

## 4. INCIDENT ESCALATION & REASSIGNMENT

### 4.1 Incident Status Transitions

```
NEW INCIDENT
     ↓
[CREATED] ← No guard assigned yet
     ├─→ Guards being alerted
     ├─→ Some decline, some pending
     ↓
[ASSIGNED] ← Guard accepted and assigned
     ├─→ Guard heading to location
     ├─→ Guard on-site handling
     ↓
[IN_PROGRESS] ← Guard confirmed arrival/involvement
     ├─→ Guard taking action
     ├─→ May escalate to higher priority
     ↓
[RESOLVED] ← Guard handled incident
     └─→ Incident concluded
```

### 4.2 Priority Escalation Rules

**Incident Priority Levels:**
- CRITICAL: Panic button, violence detected
- HIGH: Screaming detected, student in severe distress
- MEDIUM: Student SOS, student report

**Escalation Logic:**
```
IF new signal arrives at same beacon within 5 minutes (dedup window)
  AND new signal is higher priority than current
  THEN escalate incident priority
  
Example:
  Incident created: STUDENT_SOS (MEDIUM)
    5 min later
  New signal: SCREAM_DETECTED (HIGH)
    → Incident priority escalates to HIGH
    → Same guard remains assigned
    → If guard unavailable → reassign to higher priority
```

---

## 5. COMMUNICATION & STATUS UPDATES

### 5.1 Real-Time Communication

**During Assignment:**
```
Guard ←→ System ←→ Admin/Coordinator
  ↓
Guard receives incident
  ├─ Location via map
  ├─ Incident type & details
  └─ Priority level
  
Guard can send:
  ├─ "I'm heading to location"
  ├─ "Arrived at location"
  ├─ "Situation is under control"
  ├─ "Need backup/escalate"
  └─ Chat messages
  
Admin sees:
  ├─ Guard status in real-time
  ├─ Guard location (current beacon)
  ├─ Incident updates from guard
  └─ Can send instructions
```

### 5.2 Notification Types

| Event | Who | Notification |
|-------|-----|--------------|
| Incident Created | Nearest Guards (3) | 🚨 NEW INCIDENT - [ACCEPT/REJECT] |
| Guard Accepted | Admin | ✓ Guard assigned - {guard name} |
| Guard Rejected | Next Guard | 🚨 INCIDENT ALERT - [ACCEPT/REJECT] |
| All Declined | Admin | ⚠️ NO GUARDS - Manual action needed |
| Guard Arriving | Admin | Guard heading to location |
| Guard On-Site | Admin | Guard on-site - handling incident |

---

## 6. KEY DATA MODELS

### GuardAlert (Notification)
```
GuardAlert
├─ incident_id (which incident)
├─ guard_id (which guard to alert)
├─ status (SENT / ACKNOWLEDGED / DECLINED / EXPIRED)
├─ priority_rank (1st, 2nd, 3rd nearest)
├─ assignment_id (link to assignment if accepted)
└─ alert_sent_at (when notified)
```

### GuardAssignment (Active Assignment)
```
GuardAssignment
├─ incident_id (which incident)
├─ guard_id (assigned guard)
├─ is_active (True = currently assigned)
├─ assigned_at (when assigned)
└─ (Unique constraint: only 1 active per incident)
```

### GuardProfile (Guard Status)
```
GuardProfile
├─ user_id (linked to User)
├─ is_active (on duty?)
├─ is_available (free for new incidents?)
├─ current_beacon (where is guard assigned)
└─ last_beacon_update (when location updated)
```

---

## 7. EDGE CASES & HANDLING

### 7.1 Guard Goes Offline While Alert Pending

```
Guard receives alert
  ↓ (no response for 30 seconds - adjust timeout)
  ↓
Alert expires (status = EXPIRED)
  ↓
Automatically alert next guard
```

### 7.2 Guard Accepts But Then Becomes Unavailable

```
Guard accepted assignment ✓
  ↓
Guard's is_available becomes False (logged out / incident handled)
  ↓
Guard unassigned automatically
  ↓
Incident reverts to CREATED
  ↓
Alert next guard
```

### 7.3 New Signal Arrives on Assigned Incident

```
Incident already ASSIGNED to Guard A
  ↓
New signal arrives at same beacon
  ↓
Check: Is GuardAssignment still active?
  ├─ YES → Add signal to same incident
  │       Priority may escalate
  │       Guard remains assigned
  │
  └─ NO → Incident moved to CREATED
         Alert new guards
```

---

## 8. SUMMARY TABLE

| Stage | Status | Who Involved | Action | Next |
|-------|--------|-------------|--------|------|
| **Incident Triggered** | CREATED | System | Find & alert 3 guards | Wait for response |
| **Guard Gets Alert** | SENT | Guard 1,2,3 | Receives push notification | Accept/Reject |
| **Guard Accepts** ✓ | ASSIGNED | Guard + Admin | Assignment created | Guard heads to location |
| **Guard Rejects** ✗ | SENT (next) | Guard + System | Alert next guard in queue | Wait for next response |
| **All Reject** | CREATED | Admin | Manual intervention needed | Admin assigns or escalates |
| **On-Site** | IN_PROGRESS | Guard | Updates incident status | Handle situation |
| **Resolved** | RESOLVED | Guard | Mark complete | Incident closed |

---

## 9. API ENDPOINTS (Quick Reference)

```
Guard Alert Actions:
POST   /api/guard-alerts/{id}/acknowledge/  → Accept
POST   /api/guard-alerts/{id}/decline/      → Reject
GET    /api/guard-alerts/                   → List my alerts

Incident Updates:
GET    /api/incidents/{id}/                 → Get incident details
PATCH  /api/incidents/{id}/                 → Update status
POST   /api/incidents/{id}/chat/            → Send message

Guard Status:
POST   /api/guards/update_location/         → Update my location (beacon)
PATCH  /api/guards/me/                      → Update availability
```

---

## 10. WORKFLOW DIAGRAM

```
┌─────────────────────┐
│  INCIDENT CREATED   │
│  (Signal received)  │
└──────────┬──────────┘
           │
           ├─→ Determine incident beacon
           │
           ├─→ Find nearest guards (beacon proximity)
           │   ├─ Search incident beacon
           │   ├─ Expand to nearby beacons
           │   └─ Collect 3 available guards
           │
           ├─→ Create GuardAlert (status=SENT) for each
           │
           └─→ Send Push Notifications
               │
               ├─────────────────────────────┐
               │                             │
          ┌────▼─────┐              ┌───────▼────┐
          │ ACCEPT ✓  │              │ REJECT ✗  │
          └────┬─────┘              └───────┬────┘
               │                            │
        ┌──────▼─────────┐         ┌────────▼────────┐
        │ Create         │         │ Mark as DECLINED│
        │ GuardAssignment│         │ Find next guard │
        │ Set           │         │ in proximity    │
        │ is_active=True │         └────────┬────────┘
        │ Link alert    │                  │
        └──────┬─────────┘         ┌────────▼────────┐
               │                  │  Repeat loop:   │
        ┌──────▼──────────┐       │ Accept/Reject?  │
        │ Update incident │       └────────┬────────┘
        │ status =        │                │
        │ ASSIGNED        │         ┌──────┴────────┐
        │ Mark other      │         │               │
        │ alerts as       │    [Next Guard] [No More Guards]
        │ EXPIRED         │         │               │
        │ Guard goes to  │     Continue loop    Escalate to
        │ location       │                      Admin
        └────────────────┘
```

---

**Last Updated:** December 2025
**System:** ResQ Campus Security - Backend
