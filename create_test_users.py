#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from accounts.models import User

# Create test users
users = [
    ('student@example.com', 'student123', 'Test Student', 'STUDENT'),
    ('guard@example.com', 'guard123', 'Test Guard', 'GUARD'),
]

for email, password, full_name, role in users:
    if not User.objects.filter(email=email).exists():
        User.objects.create_user(
            email=email,
            password=password,
            full_name=full_name,
            role=role
        )
        print(f"✓ Created {role}: {email}")
    else:
        print(f"✓ {email} already exists")

print("\nTest credentials:")
print("  Student: student@example.com / student123")
print("  Guard: guard@example.com / guard123")
