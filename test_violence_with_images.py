#!/usr/bin/env python
"""
Test script for Violence Detection with Images feature.
Tests both JSON and multipart endpoints.
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api"

def test_violence_json_only():
    """Test violence detection with JSON only (no images)"""
    print("\n" + "="*70)
    print("TEST 1: Violence Detection - JSON Only")
    print("="*70)
    
    data = {
        "beacon_id": "ab907856-3412-3412-3412-341278563412",
        "confidence_score": 0.92,
        "description": "Fight detected near library entrance",
        "device_id": "AI-VISION-001"
    }
    
    response = requests.post(
        f"{BASE_URL}/violence-detected/",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code in [200, 201]:
        print("✅ TEST PASSED")
        return result.get('incident_id')
    else:
        print("❌ TEST FAILED")
        return None


def test_violence_with_single_image():
    """Test violence detection with single image"""
    print("\n" + "="*70)
    print("TEST 2: Violence Detection - Single Image")
    print("="*70)
    
    image_path = Path("test_images/sample1.jpg")
    if not image_path.exists():
        print(f"❌ Test image not found: {image_path}")
        return None
    
    files = {
        'images': ('sample1.jpg', open(image_path, 'rb'), 'image/jpeg')
    }
    data = {
        'beacon_id': 'ab907856-3412-3412-3412-341278563412',
        'confidence_score': '0.95',
        'description': 'Violent confrontation with single evidence photo',
        'device_id': 'AI-VISION-SURVEILLANCE-01'
    }
    
    response = requests.post(
        f"{BASE_URL}/violence-detected/",
        data=data,
        files=files
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code in [200, 201]:
        print(f"✅ TEST PASSED")
        print(f"   Images uploaded: {len(result.get('images', []))}")
        if result.get('images'):
            print(f"   Image URL: {result['images'][0]['image']}")
        return result.get('incident_id')
    else:
        print("❌ TEST FAILED")
        return None


def test_violence_with_multiple_images():
    """Test violence detection with multiple images"""
    print("\n" + "="*70)
    print("TEST 3: Violence Detection - Multiple Images (3)")
    print("="*70)
    
    files = [
        ('images', ('sample1.jpg', open('test_images/sample1.jpg', 'rb'), 'image/jpeg')),
        ('images', ('sample2.jpg', open('test_images/sample2.jpg', 'rb'), 'image/jpeg')),
        ('images', ('sample1_copy.jpg', open('test_images/sample1.jpg', 'rb'), 'image/jpeg')),
    ]
    data = {
        'beacon_id': 'safe:uuid:403:403',
        'confidence_score': '0.88',
        'description': 'Multiple suspects with 3 evidence photos',
        'device_id': 'AI-VISION-MULTI-01'
    }
    
    response = requests.post(
        f"{BASE_URL}/violence-detected/",
        data=data,
        files=files
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code in [200, 201]:
        print(f"✅ TEST PASSED")
        print(f"   Images uploaded: {len(result.get('images', []))}")
        return result.get('incident_id')
    else:
        print("❌ TEST FAILED")
        return None


def test_violence_below_threshold_with_images():
    """Test violence detection below threshold with images (logged only)"""
    print("\n" + "="*70)
    print("TEST 4: Violence Detection - Below Threshold with Images")
    print("="*70)
    
    files = {
        'images': ('sample1.jpg', open('test_images/sample1.jpg', 'rb'), 'image/jpeg')
    }
    data = {
        'beacon_id': 'ab907856-3412-3412-3412-341278563412',
        'confidence_score': '0.65',
        'description': 'Uncertain violence - below threshold',
    }
    
    response = requests.post(
        f"{BASE_URL}/violence-detected/",
        data=data,
        files=files
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    # Below threshold should still return 200 with "logged_only" status
    if response.status_code == 200 and result.get('status') == 'logged_only':
        print("✅ TEST PASSED")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Images received: {result.get('images_received')}")
        return None
    else:
        print("❌ TEST FAILED")
        return None


def test_violence_too_many_images():
    """Test violence detection with too many images (should fail)"""
    print("\n" + "="*70)
    print("TEST 5: Violence Detection - Too Many Images (Error Test)")
    print("="*70)
    
    files = [
        ('images', ('sample1.jpg', open('test_images/sample1.jpg', 'rb'), 'image/jpeg')),
        ('images', ('sample2.jpg', open('test_images/sample2.jpg', 'rb'), 'image/jpeg')),
        ('images', ('sample1_2.jpg', open('test_images/sample1.jpg', 'rb'), 'image/jpeg')),
        ('images', ('sample2_2.jpg', open('test_images/sample2.jpg', 'rb'), 'image/jpeg')),
    ]
    data = {
        'beacon_id': 'ab907856-3412-3412-3412-341278563412',
        'confidence_score': '0.90',
        'description': 'Test with 4 images - should fail',
    }
    
    response = requests.post(
        f"{BASE_URL}/violence-detected/",
        data=data,
        files=files
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code == 400 and 'Maximum 3 images' in result.get('error', ''):
        print("✅ TEST PASSED (correctly rejected)")
        print(f"   Error: {result.get('error')}")
        return True
    else:
        print("❌ TEST FAILED - should have rejected 4 images")
        return False


def test_scream_with_images():
    """Test scream detection with images"""
    print("\n" + "="*70)
    print("TEST 6: Scream Detection - With Images")
    print("="*70)
    
    files = {
        'images': ('sample2.jpg', open('test_images/sample2.jpg', 'rb'), 'image/jpeg')
    }
    data = {
        'beacon_id': 'safe:uuid:402:402',
        'confidence_score': '0.92',
        'description': 'High-pitched screaming with distress screenshot',
        'device_id': 'AI-AUDIO-MONITORING-02'
    }
    
    response = requests.post(
        f"{BASE_URL}/scream-detected/",
        data=data,
        files=files
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code in [200, 201]:
        print(f"✅ TEST PASSED")
        print(f"   Priority: {result.get('incident_priority')}")
        print(f"   Images uploaded: {len(result.get('images', []))}")
        return result.get('incident_id')
    else:
        print("❌ TEST FAILED")
        return None


def test_missing_description():
    """Test violence detection with missing description (should fail)"""
    print("\n" + "="*70)
    print("TEST 7: Violence Detection - Missing Description (Error Test)")
    print("="*70)
    
    files = {
        'images': ('sample1.jpg', open('test_images/sample1.jpg', 'rb'), 'image/jpeg')
    }
    data = {
        'beacon_id': 'ab907856-3412-3412-3412-341278563412',
        'confidence_score': '0.90',
        # Missing 'description' field
    }
    
    response = requests.post(
        f"{BASE_URL}/violence-detected/",
        data=data,
        files=files
    )
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if response.status_code == 400 and 'description' in result.get('error', ''):
        print("✅ TEST PASSED (correctly rejected)")
        print(f"   Error: {result.get('error')}")
        return True
    else:
        print("❌ TEST FAILED")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "🚀 "*35)
    print("VIOLENCE DETECTION WITH IMAGES - TEST SUITE")
    print("🚀 "*35)
    
    results = {
        "JSON Only": test_violence_json_only(),
        "Single Image": test_violence_with_single_image(),
        "Multiple Images": test_violence_with_multiple_images(),
        "Below Threshold with Images": test_violence_below_threshold_with_images(),
        "Too Many Images (Error)": test_violence_too_many_images(),
        "Scream with Images": test_scream_with_images(),
        "Missing Description (Error)": test_missing_description(),
    }
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    success_count = sum(1 for v in results.values() if v is not None or v is True)
    total_count = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if (result is not None or result is True) else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {success_count}/{total_count} tests passed")
    print("="*70)


if __name__ == "__main__":
    run_all_tests()
