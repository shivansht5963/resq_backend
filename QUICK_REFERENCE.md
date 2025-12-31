# Push Notifications - Quick Reference Card

## 🚀 Quick Start (5 minutes)

### Step 1: Deploy Code
```bash
cd /path/to/resq_backend
git add .
git commit -m "Add push notification system"
git push origin main
```

### Step 2: Run Migration
```bash
python manage.py migrate accounts
```

### Step 3: Verify Installation
```bash
python manage.py shell
>>> from accounts.models import Device
>>> from accounts.push_notifications import PushNotificationService
>>> print("✅ Push notification system installed")
```

---

## 📱 Mobile App Checklist

- [ ] Install `expo-notifications` package
- [ ] Get Expo Project ID from Expo dashboard
- [ ] Implement device registration after login
- [ ] Setup notification listeners
- [ ] Test with sample incident
- [ ] Test with chat message

---

## 🔑 Device Registration Code (Copy-Paste)

```javascript
// React Native / Expo
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

async function registerPushNotifications(authToken) {
  try {
    // 1. Get push token
    const { data: expoPushToken } = await Notifications.getExpoPushTokenAsync({
      projectId: 'your-expo-project-id',
    });

    // 2. Register with backend
    const response = await fetch(
      'https://resq-server.onrender.com/api/accounts/devices/register/',
      {
        method: 'POST',
        headers: {
          'Authorization': `Token ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: expoPushToken,
          platform: Platform.OS === 'ios' ? 'ios' : 'android',
        }),
      }
    );

    if (!response.ok) {
      throw new Error(`Registration failed: ${response.statusText}`);
    }

    console.log('✅ Device registered for push notifications');
    return true;
  } catch (error) {
    console.error('❌ Failed to register device:', error);
    return false;
  }
}
```

---

## 🎯 Notification Handler Code (Copy-Paste)

```javascript
// React Native / Expo
import * as Notifications from 'expo-notifications';
import { useNavigation } from '@react-navigation/native';

export function setupNotificationHandlers() {
  const navigation = useNavigation();

  // Handle notification when user taps it
  Notifications.addNotificationResponseReceivedListener((response) => {
    const { type, incident_id, alert_id, conversation_id } = response.notification.request.content.data;

    switch (type) {
      case 'GUARD_ALERT':
        navigation.navigate('AlertDetails', { alertId: alert_id, incidentId: incident_id });
        break;
      case 'ASSIGNMENT_CONFIRMED':
        navigation.navigate('AssignedIncident', { incidentId: incident_id });
        break;
      case 'NEW_CHAT_MESSAGE':
        navigation.navigate('Chat', { incidentId: incident_id, conversationId: conversation_id });
        break;
      case 'INCIDENT_ESCALATED':
        navigation.navigate('AssignedIncident', { incidentId: incident_id });
        break;
    }
  });

  // Handle notification in foreground (optional)
  Notifications.setNotificationHandler({
    handleNotification: async (notification) => true, // Show notification in foreground
  });
}

// Call this in your App.tsx useEffect
useEffect(() => {
  setupNotificationHandlers();
}, []);
```

---

## 🔌 API Endpoints

### Register Device
```bash
POST /api/accounts/devices/register/
Header: Authorization: Token <token>
Body: {
  "token": "ExponentPushToken[...]",
  "platform": "android|ios"
}
```

### Unregister Device
```bash
POST /api/accounts/devices/unregister/
Header: Authorization: Token <token>
Body: {
  "token": "ExponentPushToken[...]"
}
```

### List Devices
```bash
GET /api/accounts/devices/
Header: Authorization: Token <token>
```

---

## 🧪 Testing Commands

### Test 1: Register a Device
```bash
GUARD_TOKEN="YOUR_TOKEN_HERE"
EXPO_TOKEN="ExponentPushToken[test123...]"

curl -X POST https://resq-server.onrender.com/api/accounts/devices/register/ \
  -H "Authorization: Token $GUARD_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\": \"$EXPO_TOKEN\",
    \"platform\": \"android\"
  }"
```

### Test 2: Create Incident (Should Send Notifications)
```bash
curl -X POST https://resq-server.onrender.com/api/incidents/report-sos/ \
  -H "Authorization: Token $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"beacon_id\": \"safe:uuid:403:403\",
    \"description\": \"Test incident for push notifications\"
  }"
```

### Test 3: Send Chat Message (Should Send Notifications)
```bash
curl -X POST https://resq-server.onrender.com/api/conversations/1/send_message/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": \"Test message to trigger notifications\"
  }"
```

---

## 📊 Notification Types

| Type | When Sent | Recipients | Data Includes |
|------|-----------|-----------|---------------|
| `GUARD_ALERT` | New incident | Alerted guards | incident_id, alert_id, priority, location |
| `ASSIGNMENT_CONFIRMED` | Guard accepted | Guard | incident_id |
| `NEW_CHAT_MESSAGE` | Message in chat | Participants | incident_id, conversation_id |
| `INCIDENT_ESCALATED` | Priority raised | Assigned guards | incident_id, new_priority |

---

## 🐛 Troubleshooting

### Notifications Not Received

**Check 1: Device is registered**
```bash
curl -X GET https://resq-server.onrender.com/api/accounts/devices/ \
  -H "Authorization: Token YOUR_TOKEN"
```
Should return list with your device.

**Check 2: Incident was created**
```bash
curl -X GET https://resq-server.onrender.com/api/incidents/ \
  -H "Authorization: Token YOUR_TOKEN"
```
Should show your test incident.

**Check 3: Logs for errors**
```bash
# SSH to server and check logs
tail -f /var/log/resq-backend.log | grep -i "notification\|error"
```

### Token Registration Fails (400 Bad Request)

**Issue**: Invalid token format
- ✅ Correct: `ExponentPushToken[abc123def456...]`
- ❌ Wrong: `abc123def456` or `[abc123]`

**Fix**: Get fresh token from Expo:
```javascript
const token = await Notifications.getExpoPushTokenAsync({
  projectId: 'your-expo-project-id',
});
```

### Device Not Found (404 on Unregister)

**Issue**: Device was already unregistered or doesn't exist

**Fix**: Just try again - it's safe to call multiple times

---

## 📝 Logs to Look For

### ✅ Success Logs
```
Sent push notification to guard user@example.com for incident ...
Sent chat notification to user@example.com for incident ...
Device registered successfully
```

### ⚠️ Warning Logs
```
Marked device token as inactive: ExponentPushToken[...]
Failed to send push notifications for incident ...: [error details]
```

### ❌ Error Logs
```
Expo API error: DeviceNotRegistered
Failed to send notification to user@example.com: [error details]
```

---

## 🔒 Security Notes

1. **Always use HTTPS** - Never send tokens over HTTP
2. **Tokens are per-device** - Each device needs its own registration
3. **User-scoped** - Users can only see their own devices
4. **No hardcoded tokens** - Tokens come from Expo at runtime

---

## 📈 Performance Tips

1. **Batch notifications** - System automatically batches when sending to multiple guards
2. **Async operation** - Notification sending is non-blocking
3. **Retry friendly** - Safe to retry failed registrations
4. **Cleanup** - Invalid tokens are automatically marked inactive

---

## 🎯 Integration Checklist

- [ ] Backend deployed with migrations
- [ ] Device model created in database
- [ ] API endpoints accessible
- [ ] Push notification service tested
- [ ] Mobile app gets Expo token
- [ ] Mobile app registers device
- [ ] Mobile app handles notifications
- [ ] Test incident creation sends notifications
- [ ] Test chat messages send notifications
- [ ] Check logs for errors
- [ ] Deploy to production

---

## 📞 Support Resources

- **Expo Documentation**: https://docs.expo.dev/push-notifications/overview/
- **Django REST Framework**: https://www.django-rest-framework.org/
- **Implementation Guide**: See [PUSH_NOTIFICATION_IMPLEMENTATION.md](PUSH_NOTIFICATION_IMPLEMENTATION.md)
- **Mobile Integration**: See [MOBILE_INTEGRATION_GUIDE.md](MOBILE_INTEGRATION_GUIDE.md)

---

## ⚡ Common Pitfalls

❌ **WRONG**: Sending same token multiple times without platform info
✅ **RIGHT**: Always include platform in request

❌ **WRONG**: Storing tokens in local database instead of getting from Expo
✅ **RIGHT**: Get token fresh from Expo on each app start

❌ **WRONG**: Not handling notification permissions
✅ **RIGHT**: Request permissions before registering

❌ **WRONG**: Assuming all notifications deliver
✅ **RIGHT**: Implement retry logic and verify delivery

---

## 🎉 You're All Set!

The push notification system is fully implemented and ready to use. Follow the checklist above and you'll have full push notification support in your Guard App!

