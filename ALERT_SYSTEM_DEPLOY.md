# Alert & Assignment System - Quick Implementation Guide

## 🚀 How to Deploy These Changes

### Step 1: Database Migration
```bash
python manage.py makemigrations security
python manage.py migrate security
```

**Migration will:**
- Add `alert_type` field (CharField, choices=['ASSIGNMENT', 'BROADCAST'])
- Add `requires_response` field (BooleanField, default=True)
- Add `response_deadline` field (DateTimeField, nullable)
- Add index on `[alert_type, status]`
- Update AlertStatus choices: ACKNOWLEDGED → ACCEPTED

### Step 2: Verify Code Changes

Check these files were updated:

**[security/models.py](security/models.py)**
- GuardAlert now has `AlertType` choices
- `response_deadline` field added
- Indexes updated

**[security/services.py](security/services.py)**
- `alert_guards_via_beacon_proximity()` now accepts `alert_type` parameter
- New function: `broadcast_alert_all_guards()`
- New function: `auto_escalate_expired_alerts()`
- Renamed: `handle_guard_alert_acknowledged_via_proximity()` → `handle_guard_alert_accepted_via_proximity()`

**[incidents/services.py](incidents/services.py)**
- New function: `get_alert_fanout_rules()`
- Updated: `alert_guards_for_incident()` uses fanout rules
- New wrapper: `handle_guard_alert_accepted()`

**[security/views.py](security/views.py)**
- New endpoint: POST `/api/alerts/{id}/accept/`
- Deprecated endpoint (redirects): POST `/api/alerts/{id}/acknowledge/`

### Step 3: Set Up Auto-Escalation (Choose One)

#### Option 1: Management Command (Simplest)
Create file: `security/management/commands/auto_escalate_alerts.py`

```python
from django.core.management.base import BaseCommand
from security.services import auto_escalate_expired_alerts

class Command(BaseCommand):
    help = 'Auto-escalate expired ASSIGNMENT alerts'

    def handle(self, *args, **options):
        result = auto_escalate_expired_alerts()
        self.stdout.write(
            self.style.SUCCESS(
                f'Escalated {result["escalated"]}, Failed {result["failed"]}'
            )
        )
```

Run via cron:
```bash
*/1 * * * * cd /app && python manage.py auto_escalate_alerts
```

Or manually for testing:
```bash
python manage.py auto_escalate_alerts
```

#### Option 2: Background Task with APScheduler

```python
# In settings.py
INSTALLED_APPS = [
    ...
    'django_apscheduler',
    ...
]

# In management/commands/start_scheduler.py
from django_apscheduler.util import disable_logging
from apscheduler.schedulers.background import BackgroundScheduler
from security.services import auto_escalate_expired_alerts
import logging

logger = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        auto_escalate_expired_alerts,
        'interval',
        seconds=10,  # Run every 10 seconds
        id='auto_escalate',
        name='Auto-escalate expired alerts'
    )
    scheduler.start()
    logger.info("Auto-escalation scheduler started")

# Call this in app initialization or management command
```

#### Option 3: Celery Beat (Production)

```python
# In celery.py
from celery.schedules import schedule

app.conf.beat_schedule = {
    'auto-escalate-alerts': {
        'task': 'security.tasks.auto_escalate_task',
        'schedule': 10.0,  # Every 10 seconds
    },
}

# In security/tasks.py
from celery import shared_task
from security.services import auto_escalate_expired_alerts

@shared_task
def auto_escalate_task():
    return auto_escalate_expired_alerts()
```

### Step 4: Test Everything

```bash
# 1. Start server
python manage.py runserver

# 2. Create test incident
python manage.py shell

from accounts.models import User
from incidents.models import Beacon, Incident, IncidentSignal
from security.models import GuardProfile, GuardAlert
from django.utils import timezone

# Create incident with CRITICAL priority
beacon = Beacon.objects.first()
incident = Incident.objects.create(
    beacon=beacon,
    status='CREATED',
    priority=Incident.Priority.CRITICAL
)

# Trigger alert
from incidents.services import alert_guards_for_incident
alerts = alert_guards_for_incident(incident)

print(f"Created {len(alerts)} ASSIGNMENT alerts")
for alert in alerts:
    print(f"  - {alert.id}: {alert.alert_type}, deadline in 45s")

# 3. Simulate timeout and auto-escalation
from datetime import timedelta
alert = alerts[0]
alert.response_deadline = timezone.now() - timedelta(seconds=1)
alert.save()

from security.services import auto_escalate_expired_alerts
result = auto_escalate_expired_alerts()
print(f"Auto-escalation result: {result}")

# 4. Verify using API
curl -X GET http://localhost:8000/api/alerts/ \
  -H "Authorization: Token <guard_token>"
```

### Step 5: Update Frontend (if needed)

When guard sees alert, check `alert.requires_response`:

```javascript
// Pseudo-code
if (alert.requires_response) {
  // ASSIGNMENT alert - show ACCEPT/REJECT buttons
  return (
    <AssignmentAlert alert={alert}>
      <button onClick={() => acceptAlert(alert.id)}>Accept</button>
      <button onClick={() => declineAlert(alert.id)}>Reject</button>
    </AssignmentAlert>
  );
} else {
  // BROADCAST alert - read-only notification
  return (
    <BroadcastAlert alert={alert}>
      <p>{alert.incident.description}</p>
      [Read Only - No Action Required]
    </BroadcastAlert>
  );
}
```

---

## 🔌 API Changes Summary

### NEW Endpoint
```
POST /api/alerts/{id}/accept/
  - Guard accepts ASSIGNMENT alert
  - Creates GuardAssignment
  - Expires other alerts
  - Status code: 200
```

### DEPRECATED Endpoint (Backward Compatible)
```
POST /api/alerts/{id}/acknowledge/
  - Redirects to /accept/ behavior
  - Kept for backward compatibility
  - Status code: 200
```

### EXISTING Endpoint (Enhanced)
```
POST /api/alerts/{id}/decline/
  - Guard declines ASSIGNMENT alert
  - Auto-searches for next guard
  - Creates new alert if available
  - Status code: 200
```

---

## 📊 Expected Behavior by Scenario

### Scenario 1: Critical Incident (Priority = CRITICAL)
```
Alert Type:     ASSIGNMENT
Max Guards:     5
Timeout:        45 seconds
Flow:           Guard 1 → (45s timeout) → Guard 2 → Guard 3 → ...
Result:         One guard eventually accepts (or all decline)
```

### Scenario 2: Fire Alarm (System Broadcast)
```
Alert Type:     BROADCAST
Max Guards:     ALL
Timeout:        NONE
Flow:           All guards notified instantly
Result:         No assignments, pure awareness
```

### Scenario 3: High Priority (Priority = HIGH)
```
Alert Type:     ASSIGNMENT
Max Guards:     3
Timeout:        45 seconds
Flow:           Guard 1 → (45s timeout) → Guard 2 → Guard 3
Result:         One guard accepts or all decline
```

---

## 🧪 Quick Test Checklist

- [ ] Run migrations successfully
- [ ] Verify `alert_type` appears in GuardAlert admin
- [ ] Create test incident → alerts have `alert_type='ASSIGNMENT'`
- [ ] Guard accepts → `status='ACCEPTED'`, GuardAssignment created
- [ ] Guard declines → `status='DECLINED'`, next guard alerted
- [ ] 45s timeout expires → `status='EXPIRED'`, auto-escalate runs
- [ ] Auto-escalation finds next guard → new alert created
- [ ] BROADCAST alert has `requires_response=False`
- [ ] API endpoint `/accept/` works (POST)
- [ ] Old `/acknowledge/` still works (redirects)

---

## 🚨 Rollback Plan

If something breaks:

```bash
# Revert migrations
python manage.py migrate security 0009_previous_migration

# Or remove new code and use git
git revert <commit>

# Restart app
python manage.py runserver
```

The model fields are backward compatible, so safe to remove.

---

## 📞 Support

**Issues?**

1. Check logs: `tail -f logs/django.log`
2. Check auto-escalation task is running
3. Verify response_deadline is set (45s from now)
4. Check GuardAlert status transitions in admin

---

**Deployment Status:** READY FOR HACKATHON ✅
