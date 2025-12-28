#!/usr/bin/env python
"""Create a test image for upload testing."""

from PIL import Image
import os

# Create test image
img = Image.new('RGB', (200, 150), color=(255, 0, 0))
img.save('test_image.jpg')
print('✓ Test image created: test_image.jpg')
print(f'✓ File size: {os.path.getsize("test_image.jpg")} bytes')
