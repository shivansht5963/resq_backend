# COMMON FRONTEND GUIDELINES - Campus Security System

## 1. Polling Strategy

**REST API ONLY** - No WebSockets, no real-time connections. Use polling with exponential backoff on failures.

| Data Type | Interval | When to Poll | When to Stop |
|-----------|----------|--------------|--------------|
| Alerts (Guard) | 5-10 sec | On-duty | Logged out / Off-duty |
| Incident Status | 5 sec | Active incident | Incident resolved |
| Messages | 3 sec | Chat open | Chat closed |
| Assignments | 30 sec | On-duty | Logged out |
| Beacons | On-load | App startup | N/A (cache) |
| Location (Guard) | 10-15 sec | After login | Logout |

**Pattern:**
```javascript
const poll = async () => {
  try {
    const response = await fetch(endpoint, {headers: {Authorization: `Token ${token}`}});
    if (response.status === 401) { stopAllPolling(); redirectToLogin(); return; }
    onData(response);
  } catch (error) { onError(error); }
};
poll();
const timer = setInterval(poll, interval);
// Later: clearInterval(timer);
```

## 2. Error Handling

| Code | Action |
|------|--------|
| **200/201** | Process response |
| **400** | Show validation error |
| **401** | **STOP ALL POLLING → Clear token → Login screen** |
| **403** | Show "Permission denied" |
| **404** | Show "Not found" |
| **5xx** | Show "Server error, retry in 5-10s" |

**401 Response:** Clear token from storage, stop all polling timers, redirect to login, show "Session expired."
**400 Response:** Show field-specific errors, allow user to retry.
**5xx Response:** Show error, provide retry button, log for debugging.

## 3. When to Stop Polling

**Student App:**
- ✅ Stop incident polling when: `status === "RESOLVED"`
- ✅ Stop message polling when: Chat screen closed
- ✅ Stop all polling on logout

**Guard App:**
- ✅ Stop location updates on logout
- ✅ Stop alert polling when: Logged out / Off-duty
- ✅ Stop incident polling when: `status === "RESOLVED"`
- ✅ Stop message polling when: Chat screen closed
- ✅ Stop all polling on logout

## 4. Data Caching

**Cache (with TTL):**
- Beacons: 1 hour (cache on load, refresh on button)
- Guard/User profile: 30 min (refresh on focus)

**Never Cache (always fresh):**
- Alerts, incident status, messages, assignments, location data

**Pattern:**
```javascript
const getCachedData = (key, ttl) => {
  const cached = localStorage.getItem(key);
  const time = localStorage.getItem(key + '_time');
  if (cached && (Date.now() - time) < ttl) return JSON.parse(cached);
  return fetchFresh();
};
```

## 5. Token Management

**Storage:**
- ✅ SecureStore (iOS) / EncryptedSharedPreferences (Android)
- ❌ Never localStorage, plaintext, or logs

**Usage:**
- ✅ Include `Authorization: Token {token}` in ALL requests
- ✅ Check validity before polling
- ❌ Never use Bearer, include in body/URL, or modify

**Lifecycle:** Login → Store → Use in all requests → On 401/logout → Clear token

## 6. Request Headers (All Requests)

```
Content-Type: application/json
Authorization: Token {auth_token}
```

## 7. Read-Only Data (Frontend Cannot Modify)

```json
{
  "incident": ["id", "student_id", "created_at", "updated_at"],
  "guard": ["id", "name", "role", "user_id"],
  "assignment": ["id", "created_at", "guard_id", "incident_id"],
  "beacon": ["id", "name", "location"],
  "alert": ["id", "created_at", "incident_id"]
}
```

**Frontend Can Modify:**
- Message content (via send_message endpoint)
- Incident status (via resolve endpoint)
- Location data (guard only, via update_location endpoint)

## 8. Network Reliability

**Retry Strategy:**
```javascript
const fetchWithRetry = async (url, options, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return response;
      if (response.status === 401) throw new AuthError();
      if (response.status >= 500) { await sleep(1000 * Math.pow(2, i)); continue; }
      return response;
    } catch (error) {
      if (i === retries - 1) throw error;
      await sleep(1000 * Math.pow(2, i));
    }
  }
};
```

**Connection Loss:**
- Show "Offline" indicator
- Queue messages until online
- Resume polling on reconnect
- Show "Retrying..." message

## 9. Security Best Practices

✅ **DO:**
- Use HTTPS only (never HTTP)
- Store token securely
- Validate user input before sending
- Clear sensitive data on logout
- Log out on 401 errors

❌ **DO NOT:**
- Store passwords in app
- Log token values or sensitive data
- Use HTTP or hard-code API keys
- Send sensitive data in URL
- Keep expired tokens

## 10. Response Validation

Always validate required fields and status values:
```javascript
const validateIncident = (data) => {
  const required = ['id', 'status', 'created_at', 'student_id', 'beacon_id'];
  for (const field of required) if (!data[field]) throw new Error(`Missing: ${field}`);
  
  const validStatuses = ['PENDING', 'IN_PROGRESS', 'RESOLVED'];
  if (!validStatuses.includes(data.status)) throw new Error(`Invalid status: ${data.status}`);
  return data;
};
```

## 11. Logging

✅ **LOG:** Endpoints, HTTP codes, error types, user actions, polling intervals, timestamps
❌ **NEVER:** Token values, passwords, personal info, full response bodies, sensitive beacon IDs

```javascript
// ✅ Good
console.log('API: POST /incidents/report_sos/', 'Status: 201', 'Incident ID:', id);

// ❌ Bad
console.log('Token:', token);
console.log('Full Response:', data);
```

## 12. Performance Optimization

- Cache beacon list on app load
- Cache user profile after login
- Stop polling when not needed
- Use staggered intervals (don't poll simultaneously)
- Minimize payload size

## 13. API Base URL

```
Dev:      http://localhost:8000/api
Staging:  https://resq-staging.onrender.com/api
Prod:     https://resq-server.onrender.com/api
```

## 14. Testing Checklist

- [ ] Token stored securely
- [ ] Authorization header on all requests
- [ ] Polling stops on 401
- [ ] Polling stops when resolved
- [ ] No sensitive data in logs
- [ ] Network failures handled
- [ ] Offline mode works
- [ ] Token persists across restart
- [ ] All timestamps ISO 8601 format
- [ ] Error messages user-friendly

## 15. Student vs Guard Comparison

| Feature | Student | Guard |
|---------|---------|-------|
| Location Updates | ❌ | ✅ 10-15 sec |
| Report SOS | ✅ | ❌ |
| Accept Alerts | ❌ | ✅ |
| Poll Alerts | ❌ | ✅ 5-10 sec |
| Poll Incident | ✅ 5 sec | ✅ 5 sec |
| Send Messages | ✅ | ✅ |
| Resolve Incident | ✅ | ✅ |
| View Own Incidents | ✅ | ❌ |
| View Assigned | ❌ | ✅ |
