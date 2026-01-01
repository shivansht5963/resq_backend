# Guard App - Complete Integration & API Guide

**Base URL**: `https://resq-server.onrender.com/api`

---

## 🚀 Quick Start - Guard Workflow

### 1. **Login** (Start of day)
```http
POST /auth/login/
Content-Type: application/json

{
  "email": "guard@example.com",
  "password": "password123"
}
```

**Response**:
```json
{
  "auth_token": "de88e903f2731983...",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "GUARD"
}
```
✅ **Save the auth_token** - You'll need it for all requests

---

## 📱 Push Notifications Setup

### Register Your Device (After Login)

**When**: Immediately after login, so you receive push alerts
**What**: Your device's Expo push token (get from mobile app)

```http
POST /devices/register/
Content-Type: application/json
Authorization: Token YOUR_AUTH_TOKEN

{
  "token": "ExponentPushToken[abc123def456...]",
  "platform": "android"
}
```

**Response**:
```json
{
  "id": 1,
  "token": "ExponentPushToken[abc123def456...]",
  "platform": "android",
  "is_active": true,
  "created_at": "2025-01-01T10:00:00Z"
}
```

✅ **Now you'll receive push notifications!**

---

## 📍 Update Your Location (Every 10-15 seconds)

**When**: Continuously while on duty
**What**: Your current beacon (indoor location - scan nearest beacon with app)

**First**: Scan nearest beacons with your mobile app's BLE scanner
**Then**: Send the beacon_id from the scan result

```http
POST /guards/update_location/
Content-Type: application/json
Authorization: Token YOUR_AUTH_TOKEN

{
  "nearest_beacon_id": "YOUR_SCANNED_BEACON_ID",
  "timestamp": "2025-12-25T10:30:15Z"
}
```

**Full Response**:
```json
{
  "status": "location_updated",
  "guard": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "user": "John Guard",
    "email": "guard@example.com",
    "is_active": true,
    "is_available": true,
    "current_beacon": {
      "id": "550e8400-e29b-41d4-a716-446655440100",
      "beacon_id": "abc123def456",
      "location_name": "Library 3F - Main Reading Area",
      "building": "Main Academic Building",
      "floor": 3,
      "latitude": 12.9716,
      "longitude": 77.5946,
      "is_active": true
    },
    "last_beacon_update": "2025-12-25T10:30:15Z",
    "last_active_at": "2025-12-25T10:30:15Z",
    "created_at": "2025-01-15T08:00:00Z",
    "updated_at": "2025-12-25T10:30:15Z"
  },
  "timestamp": "2025-12-25T10:30:15Z"
}
```

✅ **System now knows your exact location for finding nearby guards**

---

## 🚨 Receiving & Responding to Alerts

### Step 1: Poll for Alerts (Every 5-10 seconds)

```http
GET /alerts/
Authorization: Token YOUR_AUTH_TOKEN
```

**Full Response**:
```json
[
  {
    "id": 17,
    "incident": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "beacon": {
        "id": "550e8400-e29b-41d4-a716-446655440100",
        "beacon_id": "xyz789",
        "location_name": "Library Main Hall - 3rd Floor",
        "building": "Main Academic Building",
        "floor": 3,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "is_active": true
      },
      "status": "CREATED",
      "priority": 4,
      "priority_display": "CRITICAL",
      "description": "Student SOS - Help needed! I'm in danger!",
      "report_type": "Student SOS",
      "location": "Library Main Hall - 3rd Floor",
      "first_signal_time": "2025-12-25T10:30:00Z",
      "last_signal_time": "2025-12-25T10:30:00Z",
      "created_at": "2025-12-25T10:30:00Z",
      "updated_at": "2025-12-25T10:30:00Z"
    },
    "recipient": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "email": "guard@example.com",
      "full_name": "John Guard"
    },
    "status": "PENDING",
    "priority_rank": 1,
    "distance_km": 0.2,
    "alert_sent_at": "2025-12-25T10:30:00Z",
    "updated_at": "2025-12-25T10:30:00Z"
  }
]
```

✅ **New alert received! Priority: CRITICAL, Distance: 0.2 km - You're very close!**

---

### Step 2: Accept Alert (Acknowledge)

**When**: You see the alert and can respond
**What**: Tell system you're accepting this incident

```http
POST /alerts/17/acknowledge/
Content-Type: application/json
Authorization: Token YOUR_AUTH_TOKEN
```

**Full Response**:
```json
{
  "status": "ACKNOWLEDGED",
  "alert_id": 17,
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "assignment": {
    "id": 1,
    "guard": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "user": "550e8400-e29b-41d4-a716-446655440002",
      "full_name": "John Guard",
      "email": "guard@example.com"
    },
    "incident": "550e8400-e29b-41d4-a716-446655440000",
    "is_active": true,
    "assigned_at": "2025-12-25T10:30:05Z",
    "updated_at": "2025-12-25T10:30:05Z"
  },
  "conversation": {
    "id": 5,
    "incident": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-12-25T10:30:05Z"
  },
  "message": "Alert acknowledged. You are now assigned to this incident.",
  "timestamp": "2025-12-25T10:30:05Z"
}
```

✅ **You're now assigned! Chat ready at conversation_id: 5**

---

### Step 3: Decline Alert (Optional)

**When**: You can't respond to this incident
**What**: Reject the alert, system will find another guard

```http
POST /alerts/17/decline/
Content-Type: application/json
Authorization: Token YOUR_AUTH_TOKEN
```

**Full Response**:
```json
{
  "status": "DECLINED",
  "alert_id": 17,
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Alert declined. System will find another guard nearby.",
  "timestamp": "2025-12-25T10:30:05Z"
}
```

---

## 💬 Chat with Student

### Get Conversation

```http
GET /conversations/5/
Authorization: Token YOUR_AUTH_TOKEN
```

**Full Response**:
```json
{
  "id": 5,
  "incident": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "ASSIGNED",
    "priority": 4,
    "priority_display": "CRITICAL",
    "location": "Library 3F - Main Reading Area",
    "description": "Student SOS",
    "created_at": "2025-12-25T10:30:00Z"
  },
  "student": {
    "id": "550e8400-e29b-41d4-a716-446655440003",
    "full_name": "Alex Student",
    "email": "student@example.com"
  },
  "guard": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "full_name": "John Guard",
    "email": "guard@example.com"
  },
  "messages": [
    {
      "id": 1,
      "sender": "Alex Student",
      "sender_id": "550e8400-e29b-41d4-a716-446655440003",
      "content": "I'm near the reading area by the windows",
      "created_at": "2025-12-25T10:32:00Z"
    },
    {
      "id": 2,
      "sender": "John Guard",
      "sender_id": "550e8400-e29b-41d4-a716-446655440001",
      "content": "I'm on my way, just 2 minutes away",
      "created_at": "2025-12-25T10:32:30Z"
    }
  ],
  "created_at": "2025-12-25T10:30:05Z"
}
```

### Send Message to Student

```http
POST /conversations/5/send_message/
Content-Type: application/json
Authorization: Token YOUR_AUTH_TOKEN

{
  "content": "I'm arriving in 2 minutes. I'm near the main entrance."
}
```

**Full Response**:
```json
{
  "id": 2,
  "conversation": 5,
  "sender": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "full_name": "John Guard",
    "email": "guard@example.com",
    "role": "GUARD"
  },
  "content": "I'm arriving in 2 minutes. I'm near the main entrance.",
  "created_at": "2025-12-25T10:32:30Z",
  "updated_at": "2025-12-25T10:32:30Z"
}
```

✅ **Student receives push notification: NEW_CHAT_MESSAGE with your message**

---

## ✅ Resolving Incident

**When**: You've helped the student and incident is resolved

```http
POST /incidents/550e8400-e29b-41d4-a716-446655440000/resolve/
Authorization: Token YOUR_AUTH_TOKEN
```

**Full Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "RESOLVED",
  "priority": 4,
  "priority_display": "CRITICAL",
  "beacon": {
    "id": "550e8400-e29b-41d4-a716-446655440100",
    "location_name": "Library 3F",
    "building": "Main Building",
    "floor": 3
  },
  "description": "Student SOS - Help needed!",
  "student": {
    "id": "550e8400-e29b-41d4-a716-446655440003",
    "full_name": "Alex Student",
    "email": "student@example.com"
  },
  "first_signal_time": "2025-12-25T10:30:00Z",
  "last_signal_time": "2025-12-25T10:35:00Z",
  "created_at": "2025-12-25T10:30:00Z",
  "updated_at": "2025-12-25T10:37:00Z",
  "message": "Incident marked as resolved by guard"
}
```

---

## 📊 View Your Details

### Get Your Profile

```http
GET /guards/1/
Authorization: Token YOUR_AUTH_TOKEN
```

**Full Response**:
```json
{
  "id": 1,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "email": "guard@example.com",
    "full_name": "John Guard",
    "role": "GUARD",
    "is_active": true
  },
  "is_active": true,
  "is_available": true,
  "current_beacon": {
    "id": "550e8400-e29b-41d4-a716-446655440100",
    "beacon_id": "abc123",
    "location_name": "Library 3F - Main Reading Area",
    "building": "Main Academic Building",
    "floor": 3,
    "latitude": 12.9716,
    "longitude": 77.5946,
    "is_active": true
  },
  "last_beacon_update": "2025-12-25T10:35:00Z",
  "last_active_at": "2025-12-25T10:35:00Z",
  "created_at": "2025-01-15T08:00:00Z",
  "updated_at": "2025-12-25T10:35:00Z"
}
```

### Get Your Assignments

```http
GET /assignments/
Authorization: Token YOUR_AUTH_TOKEN
```

**Full Response**:
```json
[
  {
    "id": 1,
    "guard": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "user": "550e8400-e29b-41d4-a716-446655440002",
      "full_name": "John Guard",
      "email": "guard@example.com"
    },
    "incident": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "ASSIGNED",
      "priority": 4,
      "description": "Student SOS at Library 3F",
      "location": "Library 3F - Main Reading Area"
    },
    "is_active": true,
    "assigned_at": "2025-12-25T10:30:00Z",
    "updated_at": "2025-12-25T10:30:00Z"
  }
]
```

---

## 🔔 Push Notification Types

You'll receive these automatic push notifications:

| Type | When | What to Do |
|------|------|-----------|
| **GUARD_ALERT** | New incident nearby | Tap → See alert details, Accept/Decline |
| **ASSIGNMENT_CONFIRMED** | Your acceptance confirmed | Tap → Go to assigned incident |
| **NEW_CHAT_MESSAGE** | Student sends message | Tap → Open chat |
| **INCIDENT_ESCALATED** | Priority increased | Tap → Check updated incident |

---

## 🔑 Authentication Header

**Every request needs this header** (except login):
```
Authorization: Token de88e903f2731983695f8e698a4eaa3d83d05d4a
```

Replace with your actual token from login response.

---

## 📍 Getting Beacon IDs

**How to scan nearest beacons**:
1. Open your mobile app's BLE (Bluetooth Low Energy) scanner
2. Look for nearby beacon broadcasts
3. Select the nearest beacon with strongest signal
4. Copy the beacon_id from the scan result
5. Use that beacon_id in location updates

**The backend will validate** if the beacon exists and is active

---

## 🐛 Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid/missing token | Re-login, copy exact token |
| 404 Not Found | Wrong alert/incident ID | Check IDs from GET requests |
| 400 Bad Request | Invalid beacon ID | Use beacon IDs from list above |
| No push alerts | Device not registered | POST /devices/register/ |
| Old alerts showing | Stale polling | Clear cache, GET /alerts/ again |

---

## 📱 Mobile App Integration

```javascript
// 1. After login, get auth token
const response = await fetch('/auth/login/', { ... });
const { auth_token } = await response.json();
await AsyncStorage.setItem('authToken', auth_token);

// 2. Register device
const pushToken = await Notifications.getExpoPushTokenAsync({
  projectId: 'your-expo-project-id'
});
await fetch('/devices/register/', {
  method: 'POST',
  headers: {
    'Authorization': `Token ${auth_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    token: pushToken.data,
    platform: 'android'
  })
});

// 3. Start location polling
setInterval(() => {
  updateLocation(auth_token, currentBeacon);
}, 10000);

// 4. Start alert polling
setInterval(() => {
  pollAlerts(auth_token);
}, 5000);

// 5. Handle push notification taps
Notifications.addNotificationResponseReceivedListener((response) => {
  const { type, incident_id, alert_id } = response.notification.request.content.data;
  
  if (type === 'GUARD_ALERT') {
    navigation.navigate('AlertDetails', { alertId: alert_id });
  }
});
```

---

## 📞 Key Points

✅ **Always update location** - Helps system find you  
✅ **Respond quickly to alerts** - Other guards might take it  
✅ **Use chat to communicate** - Student gets push notification  
✅ **Mark incidents resolved** - Updates student in real-time  
✅ **Keep push notifications enabled** - Don't miss alerts  
✅ **Register device after login** - Required for notifications  

---

**Version**: 1.0 (Production Ready)  
**Last Updated**: Dec 31, 2025

---

## ❓ Have Questions?

If you encounter any issues, have unclear requirements, or need clarifications on any API endpoint:

1. **Check the JSON response** - All responses include full field details
2. **Verify your token** - Ensure token is copied exactly from login response
3. **Check beacon ID** - Scan with BLE scanner, don't hardcode beacon IDs
4. **Review error messages** - Backend returns descriptive error messages
5. **Ask your supervisor** - For API issues or integration problems

**Common Issues & Solutions**:
- **401 Unauthorized**: Re-login, copy exact token
- **404 Not Found**: Verify incident/alert/conversation ID exists
- **400 Bad Request**: Check JSON format and required fields
- **No push notifications**: Register device with POST /devices/register/

**Further Questions**:
- Not sure about a field in the response? Ask your admin team
- Need custom behavior? Contact backend development team
- Integration issues with mobile app? Check MOBILE_INTEGRATION_GUIDE.md
- Want to add new endpoints? Submit feature request to backend team
