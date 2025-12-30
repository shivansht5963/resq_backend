from django.db import models
from django.conf import settings
from django.utils import timezone


class GuardProfile(models.Model):
    """Guard-specific profile and beacon-based location tracking."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guard_profile"
    )
    is_active = models.BooleanField(default=True, db_index=True, help_text="Guard is on duty")
    is_available = models.BooleanField(default=True, db_index=True, help_text="Guard is available for incidents")
    
    # Beacon-based location (replaces GPS)
    current_beacon = models.ForeignKey(
        "incidents.Beacon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guards_present",
        help_text="Which beacon the guard is near (indoor location)"
    )
    last_beacon_update = models.DateTimeField(null=True, blank=True, help_text="When guard's beacon was last updated")
    
    last_active_at = models.DateTimeField(default=timezone.now, help_text="Last activity timestamp")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_active_at"]
        indexes = [
            models.Index(fields=["is_available"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["current_beacon"]),
        ]

    def __str__(self):
        return f"GuardProfile: {self.user.full_name}"


class GuardAssignment(models.Model):
    """Assignment of guard to incident. Only ONE active assignment per incident."""

    id = models.AutoField(primary_key=True)
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.CASCADE,
        related_name="guard_assignments"
    )
    guard = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["incident", "is_active"]),
            models.Index(fields=["guard", "is_active", "-assigned_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["incident"],
                condition=models.Q(is_active=True),
                name="one_active_assignment_per_incident"
            )
        ]

    def __str__(self):
        return f"{self.guard.full_name} → Incident {str(self.incident.id)[:8]} (active={self.is_active})"


class DeviceToken(models.Model):
    """FCM device tokens for push notifications."""

    class Platform(models.TextChoices):
        ANDROID = "ANDROID", "Android"
        IOS = "IOS", "iOS"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens"
    )
    token = models.TextField(unique=True, db_index=True)
    platform = models.CharField(max_length=20, choices=Platform.choices)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["platform"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.platform}"


class GuardAlert(models.Model):
    """
    Alert sent to guards when incident is created.
    
    Two types:
    1. ASSIGNMENT: Action required (specific guards must accept/reject)
    2. BROADCAST: Awareness only (sent to all, read-only)
    """
    
    class AlertStatus(models.TextChoices):
        SENT = "SENT", "Sent"
        ACCEPTED = "ACCEPTED", "Accepted (Official Response)"
        DECLINED = "DECLINED", "Declined"
        EXPIRED = "EXPIRED", "Expired (No Response / Timeout)"
    
    class AlertType(models.TextChoices):
        ASSIGNMENT = "ASSIGNMENT", "Assignment Required"
        BROADCAST = "BROADCAST", "Broadcast Only"
    
    id = models.AutoField(primary_key=True)
    incident = models.ForeignKey(
        "incidents.Incident",
        on_delete=models.CASCADE,
        related_name="guard_alerts"
    )
    guard = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="incident_alerts"
    )
    assignment = models.OneToOneField(
        GuardAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert",
        help_text="Assignment created when guard accepts (ASSIGNMENT type only)"
    )
    distance_km = models.FloatField(null=True, blank=True, help_text="Distance from guard to incident")
    
    # NEW: Alert type (ASSIGNMENT or BROADCAST)
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices,
        default=AlertType.ASSIGNMENT,
        db_index=True,
        help_text="ASSIGNMENT: requires response, BROADCAST: awareness only"
    )
    
    # NEW: Whether guard response is required
    requires_response = models.BooleanField(
        default=True,
        help_text="True = guard must accept/reject, False = read-only notification"
    )
    
    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.SENT,
        db_index=True
    )
    priority_rank = models.IntegerField(null=True, help_text="1=nearest, 2=second nearest, etc")
    alert_sent_at = models.DateTimeField(auto_now_add=True)
    response_deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deadline for guard response (auto-escalate after this)"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["priority_rank", "-alert_sent_at"]
        indexes = [
            models.Index(fields=["incident", "alert_type", "status"]),
            models.Index(fields=["guard", "status"]),
            models.Index(fields=["incident", "guard", "-alert_sent_at"]),
            models.Index(fields=["requires_response", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["incident", "guard"],
                name="unique_guard_per_incident_alert"
            )
        ]
    
    def __str__(self):
        return f"Alert[{self.alert_type}]: Guard {self.guard.full_name} → Incident {str(self.incident.id)[:8]} ({self.status})"
