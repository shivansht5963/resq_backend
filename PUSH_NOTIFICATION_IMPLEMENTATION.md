# Push Notification Implementation Guide

This document explains the push notification system that has been implemented for the Guard App backend.

## Overview

The backend now supports sending push notifications to mobile devices via the Expo Push API. Guards can register their devices, and the system automatically sends push notifications for:

- **GUARD_ALERT**: New incident alerts
- **ASSIGNMENT_CONFIRMED**: Assignment confirmations
- **NEW_CHAT_MESSAGE**: New chat messages
- **INCIDENT_ESCALATED**: Incident priority escalations

## Architecture

### 1. Device Management

**Models**:
- `accounts.Device` - Stores device registration data for each user

**Fields**:
- `user` - Foreign key to User
- `token` - Expo push token (unique)
- `platform` - "android" or "ios"
- `is_active` - Boolean flag for active devices
- `last_seen_at` - Auto-updated on each registration
- `created_at` - Timestamp of registration

**Endpoints**:
- `POST /api/accounts/devices/register/` - Register a new device
- `POST /api/accounts/devices/unregister/` - Unregister a device
- `GET /api/accounts/devices/` - List user's registered devices

### 2. Push Notification Service

**File**: `accounts/push_notifications.py`

**Main Class**: `PushNotificationService`

**Key Methods**:
- `send_notification()` - Send a single notification
- `send_batch_notifications()` - Send multiple notifications in one request
- `notify_guard_alert()` - Send GUARD_ALERT notifications
- `notify_assignment_confirmed()` - Send ASSIGNMENT_CONFIRMED notifications
- `notify_new_chat_message()` - Send NEW_CHAT_MESSAGE notifications
- `notify_incident_escalated()` - Send INCIDENT_ESCALATED notifications
- `get_guard_tokens()` - Get all active tokens for a user
- `handle_invalid_token()` - Mark a token as inactive

**Error Handling**:
- Catches Expo API errors and logs them
- Invalid tokens are marked as inactive in the database
- Failed notifications are logged but don't break the request flow

### 3. Integration Points

#### Incident Alerts
**Location**: `incidents/services.py`

When a new incident is created and alerts are sent to guards:
1. `alert_guards_for_incident()` is called
2. After guard alerts are created, `send_push_notifications_for_alerts()` is triggered
3. For each alerted guard, a GUARD_ALERT notification is sent to all their registered devices

#### Chat Messages
**Location**: `chat/views.py`

When a new message is sent in an incident conversation:
1. Message is created and saved
2. `notify_new_message()` function is called
3. Notifications are sent to all participants except the sender

### 4. Request Package

Added `requests>=2.28.0` to `requirements.txt` for HTTP communication with Expo API.

## API Usage

### Device Registration

**Endpoint**: `POST /api/accounts/devices/register/`

**Headers**:
```
Authorization: Token <auth_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "token": "ExponentPushToken[abc123def456...]",
  "platform": "android"
}
```

**Response** (201 Created or 200 OK):
```json
{
  "id": 1,
  "token": "ExponentPushToken[abc123def456...]",
  "platform": "android",
  "is_active": true,
  "last_seen_at": "2025-01-01T10:00:00Z",
  "created_at": "2025-01-01T10:00:00Z"
}
```

**Note**: If the same token is registered again, the existing device is updated (returns 200).

### Device Unregistration

**Endpoint**: `POST /api/accounts/devices/unregister/`

**Headers**:
```
Authorization: Token <auth_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "token": "ExponentPushToken[abc123def456...]"
}
```

**Response** (200 OK):
```json
{
  "detail": "Device unregistered successfully."
}
```

### List Devices

**Endpoint**: `GET /api/accounts/devices/`

**Headers**:
```
Authorization: Token <auth_token>
```

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "token": "ExponentPushToken[abc123def456...]",
    "platform": "android",
    "is_active": true,
    "last_seen_at": "2025-01-01T10:00:00Z",
    "created_at": "2025-01-01T10:00:00Z"
  }
]
```

## Mobile App Integration

### 1. Getting the Expo Push Token

The mobile app should generate an Expo Push Token on startup using:
```javascript
import * as Notifications from 'expo-notifications';

const token = await Notifications.getExpoPushTokenAsync({
  projectId: 'your-expo-project-id',
});
```

### 2. Device Registration After Login

After successful login, register the device:
```javascript
const response = await fetch('https://resq-server.onrender.com/api/accounts/devices/register/', {
  method: 'POST',
  headers: {
    'Authorization': `Token ${authToken}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    token: expoPushToken,
    platform: Platform.OS, // 'android' or 'ios'
  }),
});
```

### 3. Setting Up Notification Listeners

Configure notification handlers in the app:
```javascript
// Handle notifications while app is in foreground
Notifications.setNotificationHandler({
  handleNotification: async (notification) => {
    const data = notification.request.content.data;
    
    switch (data.type) {
      case 'GUARD_ALERT':
        // Open alert details screen
        navigation.navigate('AlertDetails', { alertId: data.alert_id });
        break;
      case 'ASSIGNMENT_CONFIRMED':
        // Open assigned incident screen
        navigation.navigate('AssignedIncident', { incidentId: data.incident_id });
        break;
      case 'NEW_CHAT_MESSAGE':
        // Open chat screen
        navigation.navigate('Chat', { incidentId: data.incident_id });
        break;
      case 'INCIDENT_ESCALATED':
        // Show escalation banner and navigate
        navigation.navigate('AssignedIncident', { incidentId: data.incident_id });
        break;
    }
    
    return true; // Show notification
  },
});

// Handle notifications when app is in background or closed
Notifications.addNotificationResponseReceivedListener((response) => {
  const data = response.notification.request.content.data;
  // Handle navigation based on data.type
});
```

## Notification Types and Payloads

### GUARD_ALERT (New Incident)

**Sent when**: A new incident is created and assigned to guards

**Payload Example**:
```json
{
  "to": "ExponentPushToken[abc123...]",
  "sound": "default",
  "title": "Incoming Alert",
  "body": "CRITICAL - Library 13 3rd Floor",
  "data": {
    "type": "GUARD_ALERT",
    "incident_id": "550e8400-e29b-41d4-a716-446655440000",
    "alert_id": 12,
    "priority": "CRITICAL",
    "location": "Library 13 3rd Floor"
  }
}
```

**Mobile App Behavior**:
- **In Background/Closed**: Shows system notification. Tap opens Alert Details screen.
- **In Foreground**: Shows full-screen alert UI with Accept/Decline actions.

### ASSIGNMENT_CONFIRMED

**Sent when**: Guard's assignment to an incident is confirmed

**Payload Example**:
```json
{
  "to": "ExponentPushToken[abc123...]",
  "sound": "default",
  "title": "Assignment Confirmed",
  "body": "You are assigned to an incident",
  "data": {
    "type": "ASSIGNMENT_CONFIRMED",
    "incident_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Mobile App Behavior**:
- **In Background/Closed**: Shows notification. Tap opens Assigned Incident screen.
- **In Foreground**: Shows confirmation banner and navigates to incident.

### NEW_CHAT_MESSAGE

**Sent when**: A new message is added to an incident conversation

**Payload Example**:
```json
{
  "to": "ExponentPushToken[abc123...]",
  "sound": "default",
  "title": "New Chat Message",
  "body": "Dispatch: Please confirm location.",
  "data": {
    "type": "NEW_CHAT_MESSAGE",
    "incident_id": "550e8400-e29b-41d4-a716-446655440000",
    "conversation_id": 5
  }
}
```

**Mobile App Behavior**:
- **In Background/Closed**: Shows notification. Tap opens Chat screen.
- **In Foreground**: Shows banner indicating new message.

### INCIDENT_ESCALATED

**Sent when**: Incident priority is raised

**Payload Example**:
```json
{
  "to": "ExponentPushToken[abc123...]",
  "sound": "default",
  "title": "Incident Escalated",
  "body": "Priority raised to HIGH",
  "data": {
    "type": "INCIDENT_ESCALATED",
    "incident_id": "550e8400-e29b-41d4-a716-446655440000",
    "new_priority": "HIGH"
  }
}
```

**Mobile App Behavior**:
- **In Background/Closed**: Shows notification. Tap opens Assigned Incident screen.
- **In Foreground**: Shows warning banner with escalation info.

## Error Handling

### Invalid Token Handling

When Expo returns a `DeviceNotRegistered` error:
1. The device token is automatically marked as `is_active=False`
2. Future notifications won't be sent to that token
3. The user should re-register the device on next app startup

### Network Errors

If the Expo API is unreachable:
1. The error is logged with context
2. The notification request fails gracefully
3. The incident/alert/message is still created and processed normally

### Retry Logic

For batch notifications, Expo handles retries internally. The backend implements:
- Single notification: Direct request to Expo
- Batch notifications: Combined request for efficiency

## Database Schema

### Device Model

```
accounts_device:
  id (PK)
  user_id (FK to auth_user)
  token (unique, indexed)
  platform (indexed)
  is_active (indexed)
  last_seen_at (auto-updated)
  created_at
  
  Indexes:
  - (user_id, is_active)
  - token
  - platform
```

## Migration Steps

After deploying this code:

1. **Create migration**:
   ```bash
   python manage.py makemigrations accounts
   ```

2. **Apply migration**:
   ```bash
   python manage.py migrate accounts
   ```

3. **Update requirements**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Device model in admin**:
   - Visit Django admin
   - Check "Devices" section under Accounts

## Testing

### 1. Register a Device

```bash
curl -X POST https://resq-server.onrender.com/api/accounts/devices/register/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "ExponentPushToken[test123...]",
    "platform": "android"
  }'
```

### 2. List Devices

```bash
curl -X GET https://resq-server.onrender.com/api/accounts/devices/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN"
```

### 3. Unregister a Device

```bash
curl -X POST https://resq-server.onrender.com/api/accounts/devices/unregister/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "ExponentPushToken[test123...]"
  }'
```

## Configuration

### Environment Variables

Currently no additional environment variables needed. The Expo endpoint is hardcoded:
```
https://exp.host/--/api/v2/push/send
```

### Logging

Push notification activities are logged with:
- Successful notifications
- Failed notifications with reasons
- Invalid token handling
- API errors from Expo

Check logs for patterns like:
```
Sent push notification to guard user@example.com for incident ...
Failed to send notification to ...
Marked device token as inactive: ...
```

## Future Enhancements

1. **Token Refresh**: Implement token expiration and refresh logic
2. **Delivery Receipts**: Track which notifications were delivered
3. **Read Receipts**: Track which notifications were read
4. **Analytics**: Dashboard for notification delivery metrics
5. **Quiet Hours**: Allow guards to set quiet hours for notifications
6. **Custom Sounds**: Use different sounds for different notification types
7. **Notification Groups**: Group related notifications on iOS
8. **Rich Notifications**: Add images/attachments to notifications

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify Expo token format (should start with `ExponentPushToken[`)
3. Ensure device is registered after login
4. Check that user has GUARD role for incident alerts
5. Verify network connectivity to `exp.host`

