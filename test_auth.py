#!/usr/bin/env python
import os
import django
import json
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

# Test login
login_data = {
    "email": "student@example.com",
    "password": "student123"
}

print("=" * 60)
print("Testing Login...")
print("=" * 60)
response = requests.post('http://localhost:8000/api/auth/login/', json=login_data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    token = response.json()['auth_token']
    print(f"\n✓ Got Token: {token}")
    
    # Test logout with token
    print("\n" + "=" * 60)
    print("Testing Logout with Token...")
    print("=" * 60)
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    logout_response = requests.post('http://localhost:8000/api/auth/logout/', headers=headers)
    print(f"Status: {logout_response.status_code}")
    print(f"Response: {logout_response.json()}")
    
    if logout_response.status_code == 200:
        print("\n✓✓✓ LOGOUT SUCCESSFUL! ✓✓✓")
    else:
        print(f"\n✗ Logout failed with status {logout_response.status_code}")
