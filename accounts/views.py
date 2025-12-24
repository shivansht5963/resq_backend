from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from .serializers import LoginSerializer


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
    
    try:
        request.user.auth_token.delete()
        return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)
    except:
        return Response({'detail': 'Logout failed.'}, status=status.HTTP_400_BAD_REQUEST)
