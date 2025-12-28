from PIL import Image
import os

os.chdir(r'c:\Users\Shivansh\OneDrive\Desktop\resq_backend')
img = Image.new('RGB', (200, 150), color=(255, 0, 0))
img.save('test_image.jpg')
print('Test image created')
