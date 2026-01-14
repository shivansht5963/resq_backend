from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Device


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - read-only fields."""

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'role', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users."""

    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone_number', 'role', 'password', 'password2')

    def validate_phone_number(self, value):
        if value and (not value.isdigit() or len(value) != 10):
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed user serializer with related objects."""

    incidents_reported = serializers.StringRelatedField(many=True, read_only=True)
    guard_profile = serializers.StringRelatedField(read_only=True)
    assignments = serializers.StringRelatedField(many=True, read_only=True)
    device_tokens = serializers.StringRelatedField(many=True, read_only=True)
    sent_messages = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'full_name', 'phone_number', 'role', 'is_active', 'is_staff',
            'created_at', 'updated_at',
            'incidents_reported', 'guard_profile', 'assignments', 'device_tokens', 'sent_messages'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_staff')


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            raise serializers.ValidationError("Both email and password are required.")

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.")

        data['user'] = user
        return data

class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for device registration and management."""

    class Meta:
        model = Device
        fields = ('id', 'token', 'platform', 'is_active', 'last_seen_at', 'created_at')
        read_only_fields = ('id', 'last_seen_at', 'created_at')


class DeviceRegisterSerializer(serializers.Serializer):
    """Serializer for device registration endpoint."""

    token = serializers.CharField(
        max_length=255,
        help_text="Expo push token"
    )
    platform = serializers.ChoiceField(
        choices=['android', 'ios'],
        default='android',
        help_text="Mobile platform"
    )

    def validate_token(self, value):
        """Validate that token starts with 'ExponentPushToken'."""
        if not value.startswith('ExponentPushToken['):
            raise serializers.ValidationError(
                "Invalid Expo token format. Must start with 'ExponentPushToken['"
            )
        return value


class DeviceUnregisterSerializer(serializers.Serializer):
    """Serializer for device unregistration endpoint."""

    token = serializers.CharField(
        max_length=255,
        help_text="Expo push token"
    )