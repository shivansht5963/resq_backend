# Troubleshooting Guide: Alert & Push Notification Issues

## Quick Diagnosis

Run this to see current state:
```bash
python verify_incident_flow.py
```

---

## Issue 1: "Push Notifications Not Reaching Guards"

### Step 1: Check Device Tokens Are Registered

```http
GET /api/device-tokens/
Authorization: Token guard-token
```

**If returns empty array:**
```json
{
  "count": 0,
  "results": []
}
```

**Solution:** Guard needs to register token first
```http
POST /api/device-tokens/
Authorization: Token guard-token
Content-Type: application/json

{
  "token": "ExponentPushToken[xxx...]",
  "platform": "ANDROID"
}
```

---

### Step 2: Verify Token Format

Token MUST start with `ExponentPushToken[`

**Invalid tokens:**
- `abc123def456` ❌
- `FCM_token_xxx` ❌
- `push_token_xxxx` ❌

**Valid token:**
- `ExponentPushToken[abc123...]` ✓

If you see invalid tokens in database:
```sql
SELECT id, user_id, token FROM accounts_device WHERE NOT token LIKE 'ExponentPushToken%';
-- Delete invalid ones
DELETE FROM accounts_device WHERE NOT token LIKE 'ExponentPushToken%';
```

---

### Step 3: Check Alert Was Created

When student reports SOS:

```http
POST /api/incidents/report_sos/
Authorization: Token student-token
Content-Type: application/json

{
  "beacon_id": "safe:uuid:403:403",
  "description": "Help needed"
}
```

**Response should include:**
```json
{
  "incident_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
  "status": "incident_created",
  "incident": {
    "guard_alerts": [
      {
        "id": 1,
        "guard": {"full_name": "Guard Name"},
        "status": "SENT",
        "alert_sent_at": "2025-01-01T12:00:15Z"
      }
    ]
  }
}
```

**If guard_alerts is empty:**
❌ Alerts weren't created!

**Check:**
- Is `alert_guards_for_incident()` being called in `report_sos` view?
- Are there any guards in the system?

---

### Step 4: Check Push Was Actually Sent

**Look in logs:**
```bash
tail -f /var/log/django.log | grep "push notification"
```

**Should see:**
```
INFO: Push notification sent successfully to ExponentPushToken[abc...]
```

**If you see:**
```
ERROR: Failed to send notification
ERROR: Expo server error
ERROR: Device token no longer registered
```

→ There's an issue with Expo API or token

---

## Issue 2: "Guard Not Seeing Alert in App"

### Step 1: Verify Guard Can Get Alerts

```http
GET /api/alerts/
Authorization: Token guard-token
```

**Response example:**
```json
{
  "count": 1,
  "results": [
    {
      "id": 1,
      "incident": {
        "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "location": "Library 3F",
        "priority": 5
      },
      "status": "SENT",
      "alert_type": "ASSIGNMENT",
      "alert_sent_at": "2025-01-01T12:00:15Z"
    }
  ]
}
```

**If returns empty:**
❌ No alerts for this guard

**Check:**
- Did alert system create GuardAlert for this guard?
- Run: `python verify_incident_flow.py` and check "GUARD ALERT VERIFICATION"

---

### Step 2: Verify Guard Can See Incident Details

```http
GET /api/incidents/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/
Authorization: Token guard-token
```

**Should return:**
```json
{
  "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
  "location": "Library 3F - Main Hall",
  "status": "CREATED",
  "guard_alerts": [
    {
      "id": 1,
      "guard": {"full_name": "This Guard Name"},
      "status": "SENT"
    }
  ]
}
```

**If guard_alerts doesn't show this guard:**
→ Alert wasn't created for this guard

---

## Issue 3: "Student App Not Updating After Guard Accepts"

### Step 1: Student Polls Incident

```http
GET /api/incidents/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/
Authorization: Token student-token
```

**Before guard accepts:**
```json
{
  "status": "CREATED",
  "guard_assignment": null,
  "guard_alerts": [
    {"status": "SENT", "guard": {"full_name": "Guard 1"}},
    {"status": "SENT", "guard": {"full_name": "Guard 2"}}
  ]
}
```

**After guard accepts:**
```json
{
  "status": "ASSIGNED",
  "guard_assignment": {
    "guard": {"full_name": "Guard 1", "id": "guard-uuid"},
    "assigned_at": "2025-01-01T12:01:30Z"
  },
  "guard_alerts": [
    {"status": "ACCEPTED", "guard": {"full_name": "Guard 1"}},
    {"status": "AUTO_DECLINED", "guard": {"full_name": "Guard 2"}}
  ]
}
```

**If still shows CREATED after accept:**
❌ Accept endpoint didn't update incident status

**Check:**
- Did POST /api/alerts/{id}/accept/ return 200?
- Check response for guard_assignment

---

### Step 2: Verify Guard Accept Endpoint Works

```http
POST /api/alerts/1/accept/
Authorization: Token guard-token
Content-Type: application/json

{}
```

**Success response (200):**
```json
{
  "id": 1,
  "status": "ACCEPTED",
  "assignment": {
    "id": 10,
    "incident": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "is_active": true
  }
}
```

**If error (400/500):**
- Check error message
- Look in logs for stack trace

---

## Issue 4: "Can't See Which Guard Got Which Alert"

### Check Incident Details

```http
GET /api/incidents/{incident_id}/
```

**Response includes:**
```json
{
  "guard_alerts": [
    {
      "id": 1,
      "guard": {
        "id": "guard-uuid-001",
        "full_name": "Sarah Smith"
      },
      "status": "SENT",
      "distance_km": 0.3,
      "priority_rank": 1,
      "alert_sent_at": "2025-01-01T12:00:15Z"
    },
    {
      "id": 2,
      "guard": {
        "id": "guard-uuid-002",
        "full_name": "John Lee"
      },
      "status": "DECLINED",
      "distance_km": 0.7,
      "priority_rank": 2,
      "alert_sent_at": "2025-01-01T12:00:15Z"
    }
  ]
}
```

✓ **Now you can see:**
- Guard #1 got alert, still pending (SENT)
- Guard #2 got alert, declined (DECLINED)
- Distances and priorities

---

## Issue 5: "Conversation Not Created After Accept"

### Check Conversation Exists

```http
GET /api/incidents/{incident_id}/
```

**Response should include:**
```json
{
  "conversation": {
    "id": 42,
    "student": {
      "id": "student-uuid",
      "full_name": "John Doe"
    },
    "guard": {
      "id": "guard-uuid",
      "full_name": "Sarah Smith"
    },
    "message_count": 0,
    "created_at": "2025-01-01T12:01:30Z"
  }
}
```

**If conversation is null:**
❌ Not created when guard accepted

**Check:**
- Did `handle_guard_alert_accepted()` run?
- Check logs for errors during accept

---

## Issue 6: "Alert Expired Automatically"

### Check Response Deadline

```http
GET /api/alerts/1/
Authorization: Token guard-token
```

**Response:**
```json
{
  "id": 1,
  "status": "SENT",
  "response_deadline": "2025-01-01T12:05:15Z"
}
```

**If status is EXPIRED:**
- Guard didn't respond within 5 minutes
- System automatically tries next guard
- Original alert stays EXPIRED

**Next guard gets new alert:**
```http
GET /api/alerts/
```

Should show new alert (ID 3, 4, etc.) with status SENT

---

## Quick Fix Checklist

| Issue | Check | Fix |
|-------|-------|-----|
| No push received | Device tokens registered? | POST /api/device-tokens/ |
| Token format wrong | Starts with ExponentPushToken? | Re-register with correct format |
| No alerts created | Alert system called? | Check view code, add logging |
| Guard can't see alert | GET /api/alerts/ returns any? | Check if alert created for guard |
| Student doesn't see update | Poll GET /api/incidents/{id}/ | Check guard_assignment field |
| After accept, still CREATED | Did accept endpoint return 200? | Check response, look for errors |
| Conversation missing | Check incident.conversation field | Should be created during accept |
| Alert auto-expired | Check response_deadline | Guard took >5 minutes to respond |

---

## Enable Debug Logging

### In Django settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'incidents': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'security': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'accounts.push_notifications': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
    },
}
```

Then restart Django and check logs:
```bash
tail -f /var/log/django.log
```

---

## Test Scenario: Complete Flow

### 1. Register Guard Device Token

```bash
# Get guard token first
curl -X POST https://api.example.com/auth/login/ \
  -d '{"email":"guard@example.com","password":"password"}' \
  -H "Content-Type: application/json"

# Copy auth_token from response
export GUARD_TOKEN="de88e903f2731983695f8e698a4eaa3d83d05d4a"

# Register device token
curl -X POST https://api.example.com/device-tokens/ \
  -H "Authorization: Token $GUARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "ExponentPushToken[ExponentPushToken...]",
    "platform": "ANDROID"
  }'
```

### 2. Student Reports SOS

```bash
export STUDENT_TOKEN="0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"

curl -X POST https://api.example.com/incidents/report_sos/ \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "beacon_id": "safe:uuid:403:403",
    "description": "Emergency test"
  }'

# Copy incident_id from response
export INCIDENT_ID="a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6"
```

### 3. Guard Polls Alerts

```bash
curl -X GET https://api.example.com/alerts/ \
  -H "Authorization: Token $GUARD_TOKEN"

# Copy alert id (first one should be SENT)
export ALERT_ID=1
```

### 4. Guard Accepts Alert

```bash
curl -X POST https://api.example.com/alerts/$ALERT_ID/accept/ \
  -H "Authorization: Token $GUARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 5. Verify Everything

```bash
# Check incident status changed to ASSIGNED
curl -X GET https://api.example.com/incidents/$INCIDENT_ID/ \
  -H "Authorization: Token $STUDENT_TOKEN"

# Check guard assignment created
curl -X GET https://api.example.com/assignments/ \
  -H "Authorization: Token $GUARD_TOKEN"

# Check alert status changed to ACCEPTED
curl -X GET https://api.example.com/alerts/$ALERT_ID/ \
  -H "Authorization: Token $GUARD_TOKEN"
```

---

## Need More Help?

Check these files:
- `INCIDENT_TRACKING_COMPLETE.md` - Architecture overview
- `ALERT_AND_PUSH_FLOW.md` - API endpoint documentation
- `accounts/push_notifications.py` - Push notification implementation
- `incidents/services.py` - Alert creation logic
- `security/services.py` - Guard assignment logic
