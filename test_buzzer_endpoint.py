#!/usr/bin/env python
"""
Test script for Buzzer Feature
Tests the public /api/incidents/buzzer-status/ endpoint
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"
BEACON_IDS = [
    "safe:uuid:403:403",
    "safe:uuid:402:402", 
    "ab907856-3412-3412-3412-341278563412",
    "test:uuid:3:3",
    "invalid:uuid:999:999"
]

def test_buzzer_endpoint():
    """Test the buzzer status endpoint for each beacon"""
    print("\n" + "="*70)
    print("🔔 BUZZER STATUS ENDPOINT TEST")
    print("="*70)
    print(f"Testing endpoint: {BASE_URL}/incidents/buzzer-status/")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*70 + "\n")
    
    for beacon_id in BEACON_IDS:
        print(f"\n📍 Testing Beacon: {beacon_id}")
        print("-" * 70)
        
        try:
            response = requests.get(
                f"{BASE_URL}/incidents/buzzer-status/",
                params={"beacon_id": beacon_id},
                timeout=5
            )
            
            print(f"   HTTP Status: {response.status_code}")
            
            if response.status_code in [200, 404, 400]:
                data = response.json()
                
                # Check if this is a success response
                if "incident_active" in data:
                    incident_active = data.get("incident_active")
                    buzzer_status = data.get("buzzer_status", "N/A")
                    incident_id = data.get("incident_id", "N/A")
                    location = data.get("location", "N/A")
                    
                    buzzer_symbol = "🔴 BUZZING" if incident_active else "🔇 SILENT"
                    print(f"   ✓ Response: {buzzer_symbol}")
                    print(f"   Buzzer Status: {buzzer_status}")
                    print(f"   Location: {location}")
                    if incident_id != "N/A":
                        print(f"   Incident ID: {incident_id}")
                    
                    # Validation
                    if response.status_code == 200:
                        if incident_active:
                            print("   ✓ Incident is active - ESP32 should BUZZ")
                        else:
                            print("   ✓ No incident - ESP32 should be SILENT")
                    elif response.status_code == 404:
                        print(f"   ⚠️  Beacon not found: {data.get('error', 'Unknown')}")
                    elif response.status_code == 400:
                        print(f"   ⚠️  Bad request: {data.get('error', 'Unknown')}")
                else:
                    print(f"   ❌ Unexpected response format: {data}")
            else:
                print(f"   ❌ Unexpected HTTP status: {response.status_code}")
                print(f"      Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection Error - Server not running!")
        except requests.exceptions.Timeout:
            print(f"   ❌ Timeout - Server too slow")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Test missing beacon_id parameter
    print(f"\n\n📍 Testing Missing Parameter")
    print("-" * 70)
    try:
        response = requests.get(f"{BASE_URL}/incidents/buzzer-status/")
        print(f"   HTTP Status: {response.status_code}")
        if response.status_code == 400:
            data = response.json()
            print(f"   ✓ Correctly returned 400 Bad Request")
            print(f"   Error: {data.get('error', 'N/A')}")
            print(f"   incident_active: {data.get('incident_active', 'N/A')}")
        else:
            print(f"   ❌ Expected 400, got {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "="*70)
    print("✓ Test Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("\n⏳ Starting Buzzer Endpoint Tests...\n")
    test_buzzer_endpoint()
