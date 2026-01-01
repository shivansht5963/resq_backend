# Complete Documentation Index

## 📚 Core Documentation Files

### 1. **SYSTEM_ARCHITECTURE.md** ⭐ START HERE
- Complete database schema
- Data flow timeline
- API endpoints by phase
- Business rules
- Deployment checklist

### 2. **INCIDENT_TRACKING_COMPLETE.md**
- Incident status progression
- Guard alert status progression
- Complete tracking response format (with real-world JSON)
- Frontend implementation guide (JavaScript/React)
- Real-world scenario with timeline

### 3. **ALERT_AND_PUSH_FLOW.md**
- Step-by-step flow from incident to push notification
- API request/response examples
- Alert types summary table
- Error responses
- Testing checklist

### 4. **TROUBLESHOOTING.md** 🔧
- Issue 1: Push notifications not reaching
- Issue 2: Guard not seeing alert
- Issue 3: Student app not updating
- Issue 4: Can't see which guard got alert
- Issue 5: Conversation not created
- Issue 6: Alert expired automatically
- Quick fix checklist
- Debug logging setup
- Complete test scenario with curl commands

### 5. **EXPO_SDK_MIGRATION.md**
- Migration from requests library → exponent_server_sdk
- Installation instructions
- Improved error handling
- Logging improvements

---

## 🔍 Verification & Testing

### verify_incident_flow.py
Run this script to diagnose system health:

```bash
python verify_incident_flow.py
```

**Checks:**
1. ✓ Incident creation
2. ✓ Guard alert creation
3. ✓ Guard assignments
4. ✓ Device token registration
5. ✓ Incident signals (deduplication)
6. ✓ Recent activity timeline
7. ✓ Push notification diagnostics

---

## 🎯 Quick Start Guide

### For New Developer

1. **Read:** SYSTEM_ARCHITECTURE.md (5 min)
2. **Read:** INCIDENT_TRACKING_COMPLETE.md (10 min)
3. **Read:** ALERT_AND_PUSH_FLOW.md (10 min)
4. **Run:** `python verify_incident_flow.py` (1 min)
5. **Test:** Use test.http examples

### For Troubleshooting

1. **Check:** TROUBLESHOOTING.md for your issue
2. **Run:** `python verify_incident_flow.py`
3. **Look at:** Django logs: `tail -f /var/log/django.log`
4. **Use:** curl commands in TROUBLESHOOTING.md

---

## 📊 Complete Flow Summary

```
STUDENT SOS
    ↓
POST /api/incidents/report_sos/
    ↓
[Backend finds nearest guards + creates alerts]
    ↓
[Push notifications sent: 🚨 "Incoming Alert"]
    ↓
GUARD RECEIVES
    ↓
GET /api/alerts/
    ↓
[Guard sees incident location, priority, etc]
    ↓
POST /api/alerts/{id}/accept/
    ↓
[Assignment created, incident status=ASSIGNED]
    ↓
[Push to guard: ✅ "Assignment Confirmed"]
[Push to student: 🚨 "Guard assigned (300m away)"]
    ↓
STUDENT SEES UPDATE
    ↓
GET /api/incidents/{id}/
    ↓
[Status: ASSIGNED, guard_assignment visible]
    ↓
[Chat conversation active]
    ↓
POST /api/conversations/{id}/send_message/
    ↓
[Both send/receive messages]
[💬 "New Message" push notifications]
    ↓
POST /api/incidents/{id}/resolve/
    ↓
[Both see: ✅ "RESOLVED"]
```

---

## 🔑 Key Concepts

### Incident Deduplication
- Same beacon, within 5 minutes = same incident
- Prevents duplicate alerts to guards
- All signals merged into one incident

### Guard Alert Progression
```
SENT → ACCEPTED → (Assignment created)
SENT → DECLINED → (Try next guard)
SENT → EXPIRED  → (5 min timeout, try next guard)
```

### Beacon Proximity Search
```
1. Check guards at incident beacon
2. Check guards at nearby beacons (by priority order)
3. Continue expanding radius until max_guards found
4. Skip guards already assigned to another incident
```

### Guard Assignment Rule
```
ONE active assignment per incident (enforced)
Prevents multiple guards responding to same incident
```

---

## 🚨 Most Common Issues & Fixes

| Issue | Solution | Doc |
|-------|----------|-----|
| Push not reaching guard | Device tokens not registered | TROUBLESHOOTING #1 |
| Guard doesn't see alert | GET /api/alerts/ returns empty | TROUBLESHOOTING #2 |
| Student app doesn't update | Not polling incident every 2-5s | TROUBLESHOOTING #3 |
| Can't see which guard | Check incident.guard_alerts array | TROUBLESHOOTING #4 |
| No conversation created | Accept endpoint didn't run | TROUBLESHOOTING #5 |
| Alert auto-expired | Guard took >5 min to respond | TROUBLESHOOTING #6 |

---

## 📋 Implementation Checklist

- [x] Database models (Incident, GuardAlert, GuardAssignment, etc)
- [x] Beacon proximity search logic
- [x] Alert creation in incident service
- [x] Push notification service (exponent_server_sdk)
- [x] Guard accept/decline endpoints
- [x] Assignment creation on accept
- [x] Auto-decline other alerts
- [x] Conversation auto-creation
- [x] Message notifications
- [x] Incident tracking serializers
- [x] Real-time response formats
- [x] Error handling & logging

**System is COMPLETE and PRODUCTION-READY** ✅

---

## 📞 API Reference Summary

### Student Endpoints
```
POST   /api/incidents/report_sos/           Report SOS
POST   /api/incidents/report/               Report non-emergency
GET    /api/incidents/                      List my incidents
GET    /api/incidents/{id}/                 Get incident tracking
POST   /api/incidents/{id}/resolve/         Resolve incident
GET    /api/conversations/                  List conversations
GET    /api/conversations/{id}/             Get conversation
POST   /api/conversations/{id}/send_message Send message
POST   /api/device-tokens/                  Register push token
```

### Guard Endpoints
```
GET    /api/alerts/                         Poll for alerts
GET    /api/alerts/{id}/                    Get alert details
POST   /api/alerts/{id}/accept/             Accept alert
POST   /api/alerts/{id}/decline/            Decline alert
POST   /api/guards/update_location/         Update location
GET    /api/assignments/                    Get assignments
GET    /api/incidents/                      List incidents
POST   /api/conversations/{id}/send_message Send message
POST   /api/device-tokens/                  Register push token
```

### Admin Endpoints
```
GET    /api/guards/                         List all guards
GET    /api/assignments/                    List all assignments
GET    /api/incidents/                      List all incidents
GET    /api/alerts/                         List all alerts
```

---

## 🛠 Development Commands

### Run verification script
```bash
python verify_incident_flow.py
```

### Check Django logs
```bash
tail -f /var/log/django.log | grep -E "(incident|alert|push)"
```

### Test with curl
```bash
# Get student token
curl -X POST https://api.example.com/auth/login/ \
  -d '{"email":"student@example.com","password":"pass"}' \
  -H "Content-Type: application/json"

# Report SOS
curl -X POST https://api.example.com/incidents/report_sos/ \
  -H "Authorization: Token {token}" \
  -d '{"beacon_id":"safe:uuid:403:403","description":"Help"}' \
  -H "Content-Type: application/json"
```

---

## 📖 Files Organization

```
/resq_backend/
├── SYSTEM_ARCHITECTURE.md              ← Database schema + data flow
├── INCIDENT_TRACKING_COMPLETE.md       ← Tracking responses + frontend guide
├── ALERT_AND_PUSH_FLOW.md              ← API endpoints + examples
├── TROUBLESHOOTING.md                  ← Issue diagnosis + fixes
├── EXPO_SDK_MIGRATION.md               ← Push notification setup
├── verify_incident_flow.py             ← Health check script
│
├── accounts/
│   ├── push_notifications.py           ← Push service (exponent_server_sdk)
│   ├── models.py                       ← User, Device models
│   └── views.py                        ← Auth endpoints
│
├── incidents/
│   ├── models.py                       ← Incident, IncidentSignal
│   ├── views.py                        ← report_sos, report endpoints
│   ├── services.py                     ← Alert creation logic
│   └── serializers.py                  ← Response serializers
│
├── security/
│   ├── models.py                       ← GuardAlert, GuardAssignment
│   ├── views.py                        ← Alert accept/decline endpoints
│   ├── services.py                     ← Guard search, assignment logic
│   └── serializers.py                  ← Alert serializers
│
└── test.http                           ← REST Client examples
```

---

## ✅ Production Readiness

- [x] All database relationships defined
- [x] Serializers return full tracking data
- [x] Alert logic implemented and tested
- [x] Push notifications use official SDK
- [x] Error handling comprehensive
- [x] Logging throughout system
- [x] Deduplication working
- [x] Proximity search optimized
- [x] Real-time updates supported
- [x] Security/permissions enforced

**Status: READY FOR PRODUCTION** ✅

---

## 📞 Support

For issues:
1. Check TROUBLESHOOTING.md
2. Run verify_incident_flow.py
3. Check Django logs
4. Reference SYSTEM_ARCHITECTURE.md

For API questions:
- See ALERT_AND_PUSH_FLOW.md for all endpoints
- See INCIDENT_TRACKING_COMPLETE.md for response formats
- Use test.http for examples

For push notification issues:
- See TROUBLESHOOTING.md #1
- Check EXPO_SDK_MIGRATION.md
- Verify device tokens are registered (ExponentPushToken format)

---

## 🎓 Learning Path

**Beginner:**
1. Read SYSTEM_ARCHITECTURE.md
2. Look at database schema
3. Follow the timeline

**Intermediate:**
1. Read INCIDENT_TRACKING_COMPLETE.md
2. Study API response formats
3. Look at serializer code

**Advanced:**
1. Study alert creation logic (incidents/services.py)
2. Study guard search logic (security/services.py)
3. Study push notification implementation (accounts/push_notifications.py)
4. Study frontend polling logic

**Troubleshooting:**
1. Run verify_incident_flow.py
2. Check TROUBLESHOOTING.md
3. Read relevant log outputs
4. Reference SYSTEM_ARCHITECTURE.md

---

**Last Updated:** January 1, 2026
**Status:** Production Ready ✅
