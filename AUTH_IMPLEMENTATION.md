# Token Authentication - Implementation Summary

## Overview
✅ Minimal identity handling implemented with DRF Token Authentication

---

## API Endpoints

### POST /api/auth/login/
**Purpose:** User authentication

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "auth_token": "token_string_here",
  "user_id": "uuid_here",
  "role": "STUDENT"
}
```

**Error Response (400):**
```json
{
  "email": ["Invalid email format"] or other field errors
}
```

---

### POST /api/auth/logout/
**Purpose:** User logout (delete token)

**Headers:**
```
Authorization: Token <auth_token>
```

**Response (200 OK):**
```json
{
  "detail": "Logged out successfully."
}
```

---

## Files Created/Modified

### 1. **accounts/serializers.py** (Added)
- `LoginSerializer` — Validates email/password and authenticates user

### 2. **accounts/views.py** (Created)
- `login()` — POST endpoint for user authentication
- `logout()` — POST endpoint for user logout (token deletion)

### 3. **accounts/urls.py** (Created)
- URL routing for login/logout endpoints

### 4. **campus_security/urls.py** (Updated)
- Added `path('api/auth/', include('accounts.urls'))`

### 5. **campus_security/settings.py** (Updated)
```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'rest_framework.authtoken',
    ...
]

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

ALLOWED_HOSTS = ['*']  # Development only
```

---

## How It Works

1. **User submits credentials** → `POST /api/auth/login/`
2. **LoginSerializer validates email & password**
3. **Django authenticate()** checks against custom User model
4. **Token generated/retrieved** via `Token.objects.get_or_create()`
5. **Response includes:**
   - `auth_token` — Used for subsequent API requests
   - `user_id` — User's UUID
   - `role` — User's role (STUDENT/GUARD/ADMIN)

---

## Usage in Frontend

```javascript
// Login
const response = await fetch('http://localhost:8000/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'student@example.com',
    password: 'student123'
  })
});

const data = await response.json();
const token = data.auth_token;

// Store token (localStorage/securely)
localStorage.setItem('token', token);

// Use token for authenticated requests (future)
const res = await fetch('http://localhost:8000/api/incidents/', {
  headers: {
    'Authorization': `Token ${token}`
  }
});
```

---

## Test Results

✅ Valid student login → Returns token + role
✅ Valid guard login → Returns token + role
✅ Invalid password → 400 Bad Request
✅ Non-existent user → 400 Bad Request

---

## Key Points

✓ **No registration endpoint** — Users must be created via Django admin  
✓ **No password reset** — Out of scope for MVP  
✓ **No permissions classes yet** — Just establishes user context  
✓ **Email-based authentication** — Custom User model uses email as USERNAME_FIELD  
✓ **Stateless tokens** — Perfect for React Native mobile apps  
✓ **Role included in response** — Frontend knows user's role immediately  

---

## Next Steps

1. **Permissions classes** — Role-based access control (IsStudent, IsGuard, IsAdmin)
2. **ViewSets** — Implement API endpoints for CRUD operations
3. **Token refreshing** — Implement token expiration & refresh mechanism
4. **Email verification** — Validate user email on registration
5. **Rate limiting** — Prevent brute force attacks on login endpoint
