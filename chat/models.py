from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """Conversation tied to an incident."""

    id = models.AutoField(primary_key=True)
    incident = models.OneToOneField(
        "incidents.Incident",
        on_delete=models.CASCADE,
        related_name="conversation",
        help_text="One conversation per incident"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["incident"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"Conversation for Incident {str(self.incident.id)[:8]}"


class Message(models.Model):
    """Individual message in a conversation."""

    id = models.AutoField(primary_key=True)
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
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "-created_at"]),
            models.Index(fields=["sender", "-created_at"]),
        ]

    def __str__(self):
        return f"Message from {self.sender.full_name} at {self.created_at}"
