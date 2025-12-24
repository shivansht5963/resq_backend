#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from accounts.models import User

# Create superuser
if not User.objects.filter(email='admin@resq.local').exists():
    User.objects.create_superuser(
        email='admin@resq.local',
        password='admin123',
        full_name='Admin User'
    )
    print("✓ Superuser created")
    print("✓ Email: admin@resq.local")
    print("✓ Password: admin123")
else:
    print("✓ Admin user already exists")

# Test all models are registered
from django.contrib.admin import site
registered_models = [model for model in site._registry.keys()]
print(f"\n✓ {len(registered_models)} models registered in admin")
for model in registered_models:
    print(f"  - {model.__module__}.{model.__name__}")
