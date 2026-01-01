import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_security.settings')
django.setup()

from accounts.models import Device, User

def check_duplicate_tokens():
    print("Checking for users with multiple active device tokens...")
    
    users_with_multiple_devices = []
    
    guards = User.objects.filter(role=User.Role.GUARD, is_active=True)
    
    for guard in guards:
        devices = Device.objects.filter(user=guard, is_active=True)
        count = devices.count()
        
        if count > 1:
            print(f"⚠️ Guard {guard.email} has {count} active devices:")
            for d in devices:
                print(f"   - {d.platform}: {d.token[:20]}... (Created: {d.created_at})")
            users_with_multiple_devices.append(guard.email)
        elif count == 1:
            # Check if this token exists for other users?
            token = devices.first().token
            duplicates = Device.objects.filter(token=token, is_active=True).exclude(user=guard)
            if duplicates.exists():
                print(f"❌ CRITICAL: Token {token[:20]}... is active for multiple users!")
                for d in duplicates:
                     print(f"   - User: {d.user.email}")

    if not users_with_multiple_devices:
        print("✅ No guards have multiple active devices.")
    else:
        print(f"\nFound {len(users_with_multiple_devices)} guards with multiple devices.")

if __name__ == '__main__':
    check_duplicate_tokens()
