#!/usr/bin/env python3
import requests

BASE_URL = 'http://localhost:8000/api'
TOKEN = '0ae475f9cf39e1134b4003d17a2b1b9f47b1e386'

headers = {'Authorization': f'Token {TOKEN}'}

data = {
    'beacon_id': 'ab907856-3412-3412-3412-341278563412',
    'type': 'Real Photo Test',
    'description': 'Testing with real 25MB photo from finalphoto.png',
    'location': 'Test Location'
}

print("=" * 70)
print("UPLOADING REAL IMAGE (25MB)")
print("=" * 70)

with open('final_test.png', 'rb') as f:
    files = {'images': ('finalphoto.png', f, 'image/png')}
    print(f'Uploading final_test.png (25MB)...')
    
    response = requests.post(
        f'{BASE_URL}/incidents/report/',
        headers=headers,
        data=data,
        files=files,
        timeout=60
    )
    
    print(f'\nResponse Status: {response.status_code}')
    
    if response.status_code in [200, 201]:
        result = response.json()
        imgs = result.get('images', [])
        print(f'Images uploaded: {len(imgs)}')
        
        if imgs:
            for img in imgs:
                print(f"\n  Image ID: {img.get('id')}")
                print(f"  URL: {img.get('image')}")
                
                # Test URL accessibility
                try:
                    print(f"  Testing URL access...", end=" ")
                    img_resp = requests.head(img.get('image'), timeout=10)
                    print(f"✓ {img_resp.status_code}")
                except Exception as e:
                    print(f"✗ Error: {e}")
    else:
        print(f"Error: {response.text}")

print("\n" + "=" * 70)
