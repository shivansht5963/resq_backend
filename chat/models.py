from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """Conversation tied to an incident (incident-based chat)."""

    # Support all three incident types
    reported_incident = models.OneToOneField(
        "incidents.ReportedIncident",
        on_delete=models.CASCADE,
        related_name="conversation",
        null=True,
        blank=True
    )
    beacon_incident = models.OneToOneField(
        "incidents.BeaconIncident",
        on_delete=models.CASCADE,
        related_name="conversation",
        null=True,
        blank=True
    )
    panic_incident = models.OneToOneField(
        "incidents.PanicButtonIncident",
        on_delete=models.CASCADE,
        related_name="conversation",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        incident_id = self.reported_incident.id or self.beacon_incident.id or self.panic_incident.id
        return f"Conversation for Incident {str(incident_id)[:8]}"


class Message(models.Model):
    """Individual message in a conversation."""

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_messages"
    )
    message_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "-created_at"]),
            models.Index(fields=["sender", "-created_at"]),
        ]

    def __str__(self):
        return f"Message from {self.sender.full_name} at {self.created_at}"
