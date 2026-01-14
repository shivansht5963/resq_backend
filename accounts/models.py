from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.conf import settings


class CustomUserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with role-based access control."""

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        GUARD = "GUARD", "Guard"
        ADMIN = "ADMIN", "Administrator"

    email = models.EmailField(unique=True, max_length=255)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=10, blank=True, null=True, help_text="10-digit Indian phone number")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    class Meta:
        db_table = "auth_user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

class Device(models.Model):
    """Mobile device registration for push notifications."""

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices"
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Expo Push Token"
    )
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        default=Platform.ANDROID
    )
    is_active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_device"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["token"]),
            models.Index(fields=["platform"]),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.platform} ({self.token[:20]}...)"


class PushNotificationLog(models.Model):
    """
    Tracks all push notifications sent through the system.
    Supports retry mechanism and delivery status tracking.
    """
    
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        SENT = "SENT", "Sent"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"
        INVALID_TOKEN = "INVALID_TOKEN", "Invalid Token"
    
    class NotificationType(models.TextChoices):
        GUARD_ALERT = "GUARD_ALERT", "Guard Alert"
        ASSIGNMENT_CONFIRMED = "ASSIGNMENT_CONFIRMED", "Assignment Confirmed"
        NEW_CHAT_MESSAGE = "NEW_CHAT_MESSAGE", "New Chat Message"
        INCIDENT_ESCALATED = "INCIDENT_ESCALATED", "Incident Escalated"
        INCIDENT_RESOLVED = "INCIDENT_RESOLVED", "Incident Resolved"
    
    id = models.AutoField(primary_key=True)
    
    # Target
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_notifications"
    )
    device_token = models.CharField(max_length=255)
    
    # Context
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        db_index=True
    )
    incident = models.ForeignKey(
        "incidents.Incident",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="push_notifications"
    )
    guard_alert = models.ForeignKey(
        "security.GuardAlert",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="push_notifications"
    )
    
    # Payload
    title = models.CharField(max_length=255)
    body = models.TextField()
    data_payload = models.JSONField(default=dict, blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True
    )
    expo_ticket_id = models.CharField(max_length=100, blank=True, help_text="From Expo API response")
    error_message = models.TextField(blank=True)
    
    # Retry tracking
    retry_count = models.PositiveIntegerField(default=0, help_text="Number of retry attempts")
    max_retries = models.PositiveIntegerField(default=3, help_text="Max retry attempts allowed")
    
    # Timestamps
    queued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "accounts_push_notification_log"
        ordering = ["-queued_at"]
        indexes = [
            models.Index(fields=["recipient", "-queued_at"]),
            models.Index(fields=["notification_type", "-queued_at"]),
            models.Index(fields=["status", "-queued_at"]),
            models.Index(fields=["incident", "-queued_at"]),
        ]
        verbose_name = "Push Notification Log"
        verbose_name_plural = "Push Notification Logs"
    
    def __str__(self):
        return f"[{self.status}] {self.notification_type} → {self.recipient.email} at {self.queued_at.strftime('%H:%M:%S')}"
    
    def can_retry(self):
        """Check if notification can be retried."""
        return self.retry_count < self.max_retries and self.status == self.Status.FAILED
