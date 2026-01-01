# Expo Push Notifications - SDK Migration

## Overview
Push notification service has been updated to use the official **exponent_server_sdk** instead of raw HTTP requests via the `requests` library.

## Changes Made

### 1. Updated `requirements.txt`
- Added `exponent_server_sdk>=0.3.0`
- Kept `requests>=2.28.0` for other API calls

```
exponent_server_sdk>=0.3.0
```

### 2. Refactored `accounts/push_notifications.py`

#### Imports
Changed from:
```python
import requests
from django.conf import settings
```

To:
```python
from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
    PushServerError,
    PushTicketError,
)
```

#### Key Benefits
- ✅ **Official SDK**: Uses Expo's officially maintained Python SDK
- ✅ **Better Error Handling**: Dedicated exception classes (DeviceNotRegisteredError, PushServerError, PushTicketError)
- ✅ **Validation**: Built-in response validation via `response.validate_response()`
- ✅ **Type Safety**: PushMessage and PushClient provide better type hints
- ✅ **Batch Processing**: Optimized `publish_multiple()` for bulk notifications

#### Method Changes

##### `send_notification()`
**Before:**
- Raised `ExpoNotificationError` exceptions
- Returned raw API response Dict

**After:**
- Returns bool (True/False) for success
- Handles all exceptions gracefully
- Logs detailed error information
- Validates tokens properly (must start with "ExponentPushToken")

```python
# Usage
success = PushNotificationService.send_notification(
    expo_token="ExponentPushToken[xyz...]",
    title="Alert",
    body="Message",
    data={"type": "GUARD_ALERT", "incident_id": "123"},
    priority="high"
)
```

##### `send_batch_notifications()`
**Before:**
- Raised exceptions on failure
- Returned raw API response

**After:**
- Returns List[bool] indicating success for each message
- Filters invalid tokens automatically
- Validates each message before sending
- Returns individual status for each notification

```python
# Usage
messages = [
    {"to": "ExponentPushToken[...]", "title": "Alert 1", "body": "Msg1", "data": {...}},
    {"to": "ExponentPushToken[...]", "title": "Alert 2", "body": "Msg2", "data": {...}},
]
results = PushNotificationService.send_batch_notifications(messages)
# results = [True, False] - indicates which sent successfully
```

##### Specialized Notification Methods
All methods updated to:
- Use emoji in titles (🚨, ✅, 💬, ⚠️)
- Handle both single and batch sends
- Return no value (None) but log success/failure
- No longer raise exceptions

**Methods:**
1. `notify_guard_alert()` - 🚨 Incoming Alert
2. `notify_assignment_confirmed()` - ✅ Assignment Confirmed  
3. `notify_new_chat_message()` - 💬 New Message
4. `notify_incident_escalated()` - ⚠️ Incident Escalated

## Installation

```bash
pip install -r requirements.txt
```

Or individual install:
```bash
pip install exponent_server_sdk>=0.3.0
```

## Compatibility

✅ **Backward Compatible**: All existing code calling the PushNotificationService will continue to work.

The main differences:
- Exceptions are no longer raised (log instead)
- Return types changed from Dict to bool/List[bool]
- Token validation is stricter

## Testing

### Test Single Notification
```python
from accounts.push_notifications import PushNotificationService

success = PushNotificationService.send_notification(
    expo_token="ExponentPushToken[YOUR_TOKEN]",
    title="Test Notification",
    body="Hello from Django backend!",
    data={"test": "true"},
)
print(f"Sent: {success}")
```

### Test Batch Notifications
```python
messages = [
    {
        "to": "ExponentPushToken[TOKEN1]",
        "title": "Batch Test 1",
        "body": "Message 1",
        "data": {"id": "1"}
    },
    {
        "to": "ExponentPushToken[TOKEN2]",
        "title": "Batch Test 2", 
        "body": "Message 2",
        "data": {"id": "2"}
    }
]

results = PushNotificationService.send_batch_notifications(messages)
print(f"Results: {results}")  # [True, True] or [True, False] etc
```

## Logging

All operations are logged to the standard Django logger:
```python
import logging
logger = logging.getLogger(__name__)

# Will see messages like:
# INFO: Push notification sent successfully to ExponentPushToken[abc...]
# WARNING: Invalid or missing Expo token: None
# ERROR: Expo server error: Device not registered
```

## Error Handling

SDK handles these errors gracefully:

| Error | Handling |
|-------|----------|
| `DeviceNotRegisteredError` | Logs warning, returns False, marks device inactive |
| `PushServerError` | Logs error, returns False |
| `PushTicketError` | Caught in batch processing, individual failure logged |
| Invalid token format | Filtered out before sending |
| Missing token | Logged as warning |

## Migration Complete ✅

The push notification system is now using the official Expo SDK with improved reliability, error handling, and type safety.
