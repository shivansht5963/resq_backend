#!/usr/bin/env python
"""Comprehensive API test for all endpoints."""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
STUDENT_EMAIL = "student@example.com"
STUDENT_PASS = "student123"
GUARD_EMAIL = "guard@example.com"
GUARD_PASS = "guard123"

def test_login_and_get_token(email, password, role):
    """Test login endpoint and return token."""
    print(f"\n=== LOGIN - {role} ===")
    resp = requests.post(
        f"{BASE_URL}/api/auth/login/",
        json={"email": email, "password": password}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✓ Token: {data['auth_token'][:20]}...")
        print(f"  User ID: {data['user_id']}, Role: {data['role']}")
        return data['auth_token']
    else:
        print(f"✗ Failed: {resp.text}")
        return None

def test_list_endpoint(token, endpoint, name):
    """Test GET endpoint."""
    print(f"\n=== GET {endpoint} ===")
    headers = {"Authorization": f"Token {token}"}
    resp = requests.get(f"{BASE_URL}/api/{endpoint}/", headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        count = len(data.get('results', []))
        print(f"✓ {name} count: {count}")
        return True
    else:
        print(f"✗ Failed: {resp.text}")
        return False

def test_create_incident(token):
    """Test creating an incident."""
    print(f"\n=== CREATE INCIDENT ===")
    headers = {"Authorization": f"Token {token}"}
    payload = {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "description": "Emergency situation"
    }
    resp = requests.post(
        f"{BASE_URL}/api/incidents/",
        json=payload,
        headers=headers
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 201:
        data = resp.json()
        print(f"✓ Incident created: ID={data['id']}")
        return data['id']
    else:
        print(f"✗ Failed: {resp.text}")
        return None

# Run tests
print("=" * 60)
print("CAMPUS SECURITY API TESTS")
print("=" * 60)

# Test 1: Authentication
student_token = test_login_and_get_token(STUDENT_EMAIL, STUDENT_PASS, "STUDENT")
guard_token = test_login_and_get_token(GUARD_EMAIL, GUARD_PASS, "GUARD")

if not student_token or not guard_token:
    print("\n✗ Authentication failed. Stopping tests.")
    exit(1)

# Test 2: List endpoints
print("\n" + "=" * 60)
print("ENDPOINT TESTS")
print("=" * 60)

test_list_endpoint(student_token, "beacons", "Beacons")
test_list_endpoint(student_token, "incidents", "Incidents")
test_list_endpoint(student_token, "guards", "Guards")
test_list_endpoint(student_token, "assignments", "Assignments")
test_list_endpoint(student_token, "conversations", "Conversations")
test_list_endpoint(student_token, "messages", "Messages")
test_list_endpoint(student_token, "ai-events", "AI Events")

# Test 3: Create incident
print("\n" + "=" * 60)
print("CREATE TESTS")
print("=" * 60)

incident_id = test_create_incident(student_token)

# Test 4: Logout
print(f"\n=== LOGOUT ===")
headers = {"Authorization": f"Token {student_token}"}
resp = requests.post(f"{BASE_URL}/api/auth/logout/", headers=headers)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(f"✓ Logout successful")
else:
    print(f"✗ Failed: {resp.text}")

print("\n" + "=" * 60)
print("TESTS COMPLETE")
print("=" * 60)
