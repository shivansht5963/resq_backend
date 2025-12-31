# Guard App Mobile Integration - Quick Start

## Overview

After the mobile app is successfully authenticated, it must register its push notification device with the backend. This document provides step-by-step integration instructions.

## Prerequisites

- Expo project with `expo-notifications` package installed
- Valid authentication token from backend login
- Expo project ID configured

## Step 1: Get Expo Push Token

In your React Native app, add this code to your authentication flow (e.g., after successful login):

```javascript
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

async function getExpoPushToken() {
  try {
    const token = await Notifications.getExpoPushTokenAsync({
      projectId: 'your-expo-project-id', // Replace with your actual Expo project ID
    });
    return token.data;
  } catch (error) {
    console.error('Failed to get Expo push token:', error);
    return null;
  }
}
```

## Step 2: Register Device with Backend

After successful login, register the device:

```javascript
async function registerDevice(authToken, expoPushToken) {
  try {
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
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('Device registered successfully:', data);
    return data;
  } catch (error) {
    console.error('Failed to register device:', error);
    throw error;
  }
}
```

## Step 3: Complete Login Flow

Integrate device registration into your login flow:

```javascript
async function handleLogin(email, password) {
  try {
    // 1. Login to get auth token
    const loginResponse = await fetch(
      'https://resq-server.onrender.com/api/accounts/login/',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      }
    );

    if (!loginResponse.ok) {
      throw new Error('Login failed');
    }

    const { auth_token, user_id, role } = await loginResponse.json();

    // 2. Get Expo push token
    const expoPushToken = await getExpoPushToken();
    if (!expoPushToken) {
      console.warn('Failed to get push token, but continuing with login');
    }

    // 3. Register device
    if (expoPushToken) {
      await registerDevice(auth_token, expoPushToken);
    }

    // 4. Store auth token and navigate to home screen
    await storeAuthToken(auth_token);
    navigation.navigate('Home');

    return { auth_token, user_id, role };
  } catch (error) {
    console.error('Login failed:', error);
    // Handle error (show alert, etc.)
  }
}
```

## Step 4: Setup Notification Handlers

Configure how the app handles incoming notifications:

```javascript
import * as Notifications from 'expo-notifications';
import { useNavigation } from '@react-navigation/native';

// Set default notification behavior
Notifications.setNotificationHandler({
  handleNotification: async (notification) => {
    console.log('Notification received:', notification);

    // Return true to show the notification even if the app is in foreground
    return true;
  },
});

export function NotificationManager() {
  const navigation = useNavigation();

  // Handle notifications when app is in background and user taps the notification
  Notifications.addNotificationResponseReceivedListener((response) => {
    const data = response.notification.request.content.data;
    handleNotificationNavigation(data, navigation);
  });

  // Handle notifications received while app is in foreground
  const subscription = Notifications.addNotificationReceivedListener(
    (notification) => {
      const data = notification.request.content.data;
      console.log('Foreground notification:', data);
    }
  );

  return () => {
    subscription.remove();
  };
}

function handleNotificationNavigation(data, navigation) {
  switch (data.type) {
    case 'GUARD_ALERT':
      // Navigate to alert details screen
      navigation.navigate('AlertDetails', {
        alertId: data.alert_id,
        incidentId: data.incident_id,
        priority: data.priority,
        location: data.location,
      });
      break;

    case 'ASSIGNMENT_CONFIRMED':
      // Navigate to assigned incident screen
      navigation.navigate('AssignedIncident', {
        incidentId: data.incident_id,
      });
      break;

    case 'NEW_CHAT_MESSAGE':
      // Navigate to chat/conversation screen
      navigation.navigate('Chat', {
        incidentId: data.incident_id,
        conversationId: data.conversation_id,
      });
      break;

    case 'INCIDENT_ESCALATED':
      // Navigate to incident with escalation warning
      navigation.navigate('AssignedIncident', {
        incidentId: data.incident_id,
        showEscalationAlert: true,
        newPriority: data.new_priority,
      });
      break;

    default:
      console.warn('Unknown notification type:', data.type);
  }
}
```

## Step 5: Ask for Permissions (iOS)

On iOS, you must request notification permissions from the user:

```javascript
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

async function requestNotificationPermission() {
  if (Platform.OS === 'android') {
    // Android 13+ requires runtime permission
    const permission = await Notifications.getPermissionsAsync();
    if (permission.status !== 'granted') {
      const newPermission = await Notifications.requestPermissionsAsync();
      return newPermission.status === 'granted';
    }
    return true;
  }

  // iOS
  const permission = await Notifications.getPermissionsAsync();
  if (permission.status !== 'granted') {
    const newPermission = await Notifications.requestPermissionsAsync();
    return newPermission.status === 'granted';
  }

  return true;
}
```

## Step 6: Register Device on App Start

Even if the user logs out, ensure the device is re-registered when they log back in:

```javascript
async function App() {
  const [authToken, setAuthToken] = useState(null);

  useEffect(() => {
    // Check if user is already logged in
    checkAuthToken();
  }, []);

  async function checkAuthToken() {
    try {
      const token = await getStoredAuthToken();
      if (token) {
        setAuthToken(token);
        // Re-register device on app start
        const expoPushToken = await getExpoPushToken();
        if (expoPushToken) {
          await registerDevice(token, expoPushToken);
        }
      }
    } catch (error) {
      console.error('Failed to restore session:', error);
    }
  }

  // ... rest of app
}
```

## Step 7: Handle Logout

When the user logs out, optionally unregister the device:

```javascript
async function handleLogout() {
  try {
    const authToken = await getStoredAuthToken();
    const expoPushToken = await getExpoPushToken();

    // Unregister device (optional but recommended)
    if (authToken && expoPushToken) {
      await fetch(
        'https://resq-server.onrender.com/api/accounts/devices/unregister/',
        {
          method: 'POST',
          headers: {
            'Authorization': `Token ${authToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token: expoPushToken }),
        }
      );
    }

    // Delete stored auth token
    await deleteAuthToken();

    // Navigate to login
    navigation.navigate('Login');
  } catch (error) {
    console.error('Logout failed:', error);
  }
}
```

## Complete Example Component

Here's a complete example of how to integrate everything:

```javascript
import React, { useEffect } from 'react';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = 'https://resq-server.onrender.com/api';

export function AuthService() {
  const navigation = useNavigation();

  useEffect(() => {
    setupNotifications();
    requestNotificationPermission();
  }, []);

  async function setupNotifications() {
    // Handle notifications when app is in background
    Notifications.addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data;
      handleNotificationNavigation(data);
    });

    // Handle notifications in foreground
    Notifications.addNotificationReceivedListener((notification) => {
      console.log('Notification received:', notification);
    });
  }

  async function requestNotificationPermission() {
    const permission = await Notifications.getPermissionsAsync();
    if (permission.status !== 'granted') {
      await Notifications.requestPermissionsAsync();
    }
  }

  async function handleLogin(email, password) {
    try {
      // Login
      const loginRes = await fetch(`${API_BASE_URL}/accounts/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!loginRes.ok) throw new Error('Login failed');

      const { auth_token, user_id, role } = await loginRes.json();

      // Get and register push token
      const pushToken = await Notifications.getExpoPushTokenAsync({
        projectId: 'your-expo-project-id',
      });

      await fetch(`${API_BASE_URL}/accounts/devices/register/`, {
        method: 'POST',
        headers: {
          'Authorization': `Token ${auth_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: pushToken.data,
          platform: Platform.OS === 'ios' ? 'ios' : 'android',
        }),
      });

      // Save token
      await AsyncStorage.setItem('authToken', auth_token);
      await AsyncStorage.setItem('userId', user_id);
      await AsyncStorage.setItem('userRole', role);

      navigation.navigate('Home');
      return { auth_token, user_id, role };
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  async function handleLogout() {
    try {
      const authToken = await AsyncStorage.getItem('authToken');
      const pushToken = await Notifications.getExpoPushTokenAsync({
        projectId: 'your-expo-project-id',
      });

      if (authToken && pushToken) {
        await fetch(`${API_BASE_URL}/accounts/devices/unregister/`, {
          method: 'POST',
          headers: {
            'Authorization': `Token ${authToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token: pushToken.data }),
        });
      }

      await AsyncStorage.clear();
      navigation.navigate('Login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  function handleNotificationNavigation(data) {
    switch (data.type) {
      case 'GUARD_ALERT':
        navigation.navigate('AlertDetails', { alertId: data.alert_id });
        break;
      case 'ASSIGNMENT_CONFIRMED':
        navigation.navigate('AssignedIncident', { incidentId: data.incident_id });
        break;
      case 'NEW_CHAT_MESSAGE':
        navigation.navigate('Chat', { incidentId: data.incident_id });
        break;
      case 'INCIDENT_ESCALATED':
        navigation.navigate('AssignedIncident', { incidentId: data.incident_id });
        break;
    }
  }

  return { handleLogin, handleLogout };
}
```

## Troubleshooting

### Token Generation Fails
- Ensure Expo project ID is correct
- Check that `expo-notifications` package is installed
- Verify app has `expo` SDK version 46+

### Device Registration Returns 400
- Verify token format (should start with `ExponentPushToken[`)
- Check that auth token is valid
- Ensure platform is either "android" or "ios"

### Notifications Not Received
- Verify device is registered (check `/api/accounts/devices/` endpoint)
- Check app's notification permissions are granted
- Ensure device token is still active
- Check backend logs for notification errors

### Notifications Fail Silently
- Check console logs for errors
- Verify internet connection
- Check that incident/alert was created correctly
- Review backend logs in `/var/log/resq-backend.log`

## API Reference

### Register Device
```
POST /api/accounts/devices/register/
Headers: Authorization: Token <token>
Body: { "token": "ExponentPushToken[...]", "platform": "android"|"ios" }
```

### Unregister Device
```
POST /api/accounts/devices/unregister/
Headers: Authorization: Token <token>
Body: { "token": "ExponentPushToken[...]" }
```

### List Devices
```
GET /api/accounts/devices/
Headers: Authorization: Token <token>
```

