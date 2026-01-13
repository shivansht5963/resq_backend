#!/usr/bin/env python3
"""
Test image upload to backend API using requests library.
This properly sends multipart/form-data with actual binary image data.
"""
import requests
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000/api"  # Change to https://resq-server.onrender.com/api for production
STUDENT_TOKEN = "0ae475f9cf39e1134b4003d17a2b1b9f47b1e386"  # Replace with actual token
BEACON_ID = "ab907856-3412-3412-3412-341278563412"
IMAGE_FILE = Path(__file__).parent / "test1.png"

if not IMAGE_FILE.exists():
    print(f"❌ Error: Image file not found: {IMAGE_FILE}")
    exit(1)

print("=" * 70)
print("TESTING IMAGE UPLOAD TO API")
print("=" * 70)

headers = {
    "Authorization": f"Token {STUDENT_TOKEN}"
}

# Prepare multipart form data
data = {
    "beacon_id": BEACON_ID,
    "type": "Safety Concern",
    "description": "Test image upload via Python requests",
    "location": "Library 3F, Main Entrance"
}

# Open image file in binary mode
with open(IMAGE_FILE, 'rb') as f:
    files = {
        'images': ('test1.png', f, 'image/png')
    }
    
    print(f"\nSending POST request to: {BASE_URL}/incidents/report/")
    print(f"Headers: {headers}")
    print(f"Data: {data}")
    print(f"Image file: {IMAGE_FILE.name} ({IMAGE_FILE.stat().st_size} bytes)")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/incidents/report/",
            headers=headers,
            data=data,
            files=files,
            timeout=10
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code in [200, 201]:
            print("✅ SUCCESS!")
            result = response.json()
            print(f"Incident ID: {result.get('id')}")
            print(f"Images: {result.get('images')}")
            
            if result.get('images'):
                for img in result['images']:
                    print(f"\n  Image ID: {img.get('id')}")
                    print(f"  URL: {img.get('image')}")
                    print(f"  Size: {img.get('size')}")
                    
                    # Try to access the image URL
                    print(f"  Testing URL access...")
                    img_response = requests.head(img.get('image'), timeout=5)
                    if img_response.status_code == 200:
                        print(f"  ✅ Image accessible: HTTP {img_response.status_code}")
                    else:
                        print(f"  ❌ Image NOT accessible: HTTP {img_response.status_code}")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("Make sure backend is running: python manage.py runserver")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 70)
