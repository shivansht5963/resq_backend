from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from .serializers import (
    LoginSerializer, 
    UserCreateSerializer,
    DeviceSerializer, 
    DeviceRegisterSerializer, 
    DeviceUnregisterSerializer
)
from .models import Device


@api_view(['POST'])
def login(request):
    """
    Login endpoint.
    
    Request:
        {
            "email": "user@example.com",
            "password": "password123"
        }
    
    Response:
        {
            "auth_token": "token_string",
            "user_id": "uuid",
            "role": "STUDENT"
        }
    """
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'auth_token': token.key,
            'user_id': str(user.id),
            'role': user.role,
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def signup(request):
    """
    User signup endpoint - create new user account.
    
    Request:
        {
            "email": "student@example.com",
            "full_name": "John Doe",
            "phone_number": "9876543210",  (optional, 10 digits only for Indian numbers)
            "role": "STUDENT",  (STUDENT, GUARD, or ADMIN)
            "password": "SecurePass123",
            "password2": "SecurePass123"
        }
    
    Response (201 Created):
        {
            "id": "user-uuid",
            "email": "student@example.com",
            "full_name": "John Doe",
            "phone_number": "9876543210",
            "role": "STUDENT",
            "auth_token": "token_string"
        }
    
    Response (400 Bad Request):
        {
            "field_name": ["error message"]
        }
    """
    serializer = UserCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'id': str(user.id),
            'email': user.email,
            'full_name': user.full_name,
            'phone_number': user.phone_number,
            'role': user.role,
            'auth_token': token.key,
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout endpoint - deletes user token.
    
    Requires: Token authentication in header
    Authorization: Token <token_key>
    """
    try:
        request.user.auth_token.delete()
        return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'detail': f'Logout failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def register_device(request):
    """
    Register a mobile device for push notifications.
    
    Requires: Token authentication in header
    Authorization: Token <token_key>
    
    Request:
        {
            "token": "ExponentPushToken[abc123...]",
            "platform": "android"
        }
    
    Response:
        {
            "id": 1,
            "token": "ExponentPushToken[abc123...]",
            "platform": "android",
            "is_active": true,
            "last_seen_at": "2025-01-01T10:00:00Z",
            "created_at": "2025-01-01T10:00:00Z"
        }
    """
    serializer = DeviceRegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        platform = serializer.validated_data['platform']
        
        # Create or update device
        device, created = Device.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'platform': platform,
                'is_active': True,
            }
        )
        
        # If device existed but was inactive, reactivate it
        if not created and not device.is_active:
            device.is_active = True
            device.save()
        
        device_serializer = DeviceSerializer(device)
        return Response(
            device_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def unregister_device(request):
    """
    Unregister a mobile device (mark as inactive).
    
    Requires: Token authentication in header
    Authorization: Token <token_key>
    
    Request:
        {
            "token": "ExponentPushToken[abc123...]"
        }
    
    Response:
        {
            "detail": "Device unregistered successfully."
        }
    """
    serializer = DeviceUnregisterSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        
        try:
            device = Device.objects.get(token=token, user=request.user)
            device.is_active = False
            device.save()
            return Response(
                {'detail': 'Device unregistered successfully.'},
                status=status.HTTP_200_OK
            )
        except Device.DoesNotExist:
            return Response(
                {'detail': 'Device not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def list_devices(request):
    """
    List all registered devices for the current user.
    
    Requires: Token authentication in header
    Authorization: Token <token_key>
    
    Response:
        [
            {
                "id": 1,
                "token": "ExponentPushToken[abc123...]",
                "platform": "android",
                "is_active": true,
                "last_seen_at": "2025-01-01T10:00:00Z",
                "created_at": "2025-01-01T10:00:00Z"
            }
        ]
    """
    devices = Device.objects.filter(user=request.user).order_by('-created_at')
    serializer = DeviceSerializer(devices, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
