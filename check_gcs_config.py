import os
from decouple import config

print("Checking GCS Configuration:")
print(f"  GS_BUCKET_NAME env: {os.environ.get('GS_BUCKET_NAME', 'NOT SET')}")
print(f"  GS_PROJECT_ID env: {os.environ.get('GS_PROJECT_ID', 'NOT SET')}")
print()
print("Via decouple config:")
print(f"  GS_BUCKET_NAME config: {config('GS_BUCKET_NAME', default='NOT_SET')}")
print(f"  GS_PROJECT_ID config: {config('GS_PROJECT_ID', default='NOT_SET')}")
print()
print("Django would use defaults from settings.py")
