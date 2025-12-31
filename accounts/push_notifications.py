"""
Push notification service for Expo push notifications.
Handles sending notifications to mobile devices via Expo's push API.
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Expo push endpoint
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class ExpoNotificationError(Exception):
    """Custom exception for Expo notification errors."""
    pass


class PushNotificationService:
    """Service to send push notifications via Expo."""

    @staticmethod
    def send_notification(
        expo_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        sound: str = "default"
    ) -> Dict[str, Any]:
        """
        Send a single push notification via Expo.

        Args:
            expo_token: Expo push token
            title: Notification title
            body: Notification body/message
            data: Additional data payload for the mobile app
            sound: Sound to play (default: "default")

        Returns:
            Response from Expo API

        Raises:
            ExpoNotificationError: If the notification fails to send
        """
        if not expo_token:
            raise ExpoNotificationError("Expo token is required")

        payload = {
            "to": expo_token,
            "sound": sound,
            "title": title,
            "body": body,
        }

        if data:
            payload["data"] = data

        try:
            response = requests.post(EXPO_PUSH_URL, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            # Check for errors in Expo response
            if "errors" in result:
                logger.error(f"Expo API error: {result['errors']}")
                raise ExpoNotificationError(f"Expo API error: {result['errors']}")

            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send notification to {expo_token}: {str(e)}")
            raise ExpoNotificationError(f"Failed to send notification: {str(e)}")

    @staticmethod
    def send_batch_notifications(
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple push notifications in a single batch request.

        Args:
            messages: List of message dicts, each with 'to', 'title', 'body', etc.

        Returns:
            Response from Expo API

        Raises:
            ExpoNotificationError: If the batch fails to send
        """
        if not messages:
            raise ExpoNotificationError("At least one message is required")

        try:
            response = requests.post(EXPO_PUSH_URL, json=messages, timeout=30)
            response.raise_for_status()
            result = response.json()

            # Check for errors in Expo response
            if "errors" in result:
                logger.error(f"Expo batch API error: {result['errors']}")
                raise ExpoNotificationError(f"Expo batch API error: {result['errors']}")

            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send batch notifications: {str(e)}")
            raise ExpoNotificationError(f"Failed to send batch notifications: {str(e)}")

    @staticmethod
    def notify_guard_alert(
        expo_tokens: List[str],
        incident_id: str,
        alert_id: int,
        priority: str,
        location: str
    ) -> None:
        """
        Send GUARD_ALERT notification to one or more guards.

        Args:
            expo_tokens: List of Expo push tokens
            incident_id: Incident UUID or ID
            alert_id: Alert ID
            priority: Priority level (e.g., "CRITICAL", "HIGH")
            location: Location description
        """
        if not expo_tokens:
            return

        messages = []
        for token in expo_tokens:
            message = {
                "to": token,
                "sound": "default",
                "title": "Incoming Alert",
                "body": f"{priority} - {location}",
                "data": {
                    "type": "GUARD_ALERT",
                    "incident_id": str(incident_id),
                    "alert_id": alert_id,
                    "priority": priority,
                    "location": location,
                },
            }
            messages.append(message)

        try:
            if len(messages) == 1:
                PushNotificationService.send_notification(
                    expo_tokens[0],
                    "Incoming Alert",
                    f"{priority} - {location}",
                    messages[0].get("data"),
                )
            else:
                PushNotificationService.send_batch_notifications(messages)
        except ExpoNotificationError as e:
            logger.error(f"Failed to send guard alert notifications: {e}")

    @staticmethod
    def notify_assignment_confirmed(
        expo_tokens: List[str],
        incident_id: str
    ) -> None:
        """
        Send ASSIGNMENT_CONFIRMED notification to guard(s).

        Args:
            expo_tokens: List of Expo push tokens
            incident_id: Incident UUID or ID
        """
        if not expo_tokens:
            return

        messages = []
        for token in expo_tokens:
            message = {
                "to": token,
                "sound": "default",
                "title": "Assignment Confirmed",
                "body": "You are assigned to an incident",
                "data": {
                    "type": "ASSIGNMENT_CONFIRMED",
                    "incident_id": str(incident_id),
                },
            }
            messages.append(message)

        try:
            if len(messages) == 1:
                PushNotificationService.send_notification(
                    expo_tokens[0],
                    "Assignment Confirmed",
                    "You are assigned to an incident",
                    messages[0].get("data"),
                )
            else:
                PushNotificationService.send_batch_notifications(messages)
        except ExpoNotificationError as e:
            logger.error(f"Failed to send assignment confirmed notifications: {e}")

    @staticmethod
    def notify_new_chat_message(
        expo_tokens: List[str],
        incident_id: str,
        conversation_id: int,
        sender_name: str,
        message_preview: str
    ) -> None:
        """
        Send NEW_CHAT_MESSAGE notification to guard(s).

        Args:
            expo_tokens: List of Expo push tokens
            incident_id: Incident UUID or ID
            conversation_id: Chat conversation ID
            sender_name: Name of the message sender
            message_preview: Preview of the chat message
        """
        if not expo_tokens:
            return

        messages = []
        for token in expo_tokens:
            message = {
                "to": token,
                "sound": "default",
                "title": "New Chat Message",
                "body": f"{sender_name}: {message_preview[:50]}",
                "data": {
                    "type": "NEW_CHAT_MESSAGE",
                    "incident_id": str(incident_id),
                    "conversation_id": conversation_id,
                },
            }
            messages.append(message)

        try:
            if len(messages) == 1:
                PushNotificationService.send_notification(
                    expo_tokens[0],
                    "New Chat Message",
                    f"{sender_name}: {message_preview[:50]}",
                    messages[0].get("data"),
                )
            else:
                PushNotificationService.send_batch_notifications(messages)
        except ExpoNotificationError as e:
            logger.error(f"Failed to send chat message notifications: {e}")

    @staticmethod
    def notify_incident_escalated(
        expo_tokens: List[str],
        incident_id: str,
        new_priority: str
    ) -> None:
        """
        Send INCIDENT_ESCALATED notification to guard(s).

        Args:
            expo_tokens: List of Expo push tokens
            incident_id: Incident UUID or ID
            new_priority: New priority level (e.g., "HIGH", "CRITICAL")
        """
        if not expo_tokens:
            return

        messages = []
        for token in expo_tokens:
            message = {
                "to": token,
                "sound": "default",
                "title": "Incident Escalated",
                "body": f"Priority raised to {new_priority}",
                "data": {
                    "type": "INCIDENT_ESCALATED",
                    "incident_id": str(incident_id),
                    "new_priority": new_priority,
                },
            }
            messages.append(message)

        try:
            if len(messages) == 1:
                PushNotificationService.send_notification(
                    expo_tokens[0],
                    "Incident Escalated",
                    f"Priority raised to {new_priority}",
                    messages[0].get("data"),
                )
            else:
                PushNotificationService.send_batch_notifications(messages)
        except ExpoNotificationError as e:
            logger.error(f"Failed to send incident escalated notifications: {e}")

    @staticmethod
    def get_guard_tokens(user) -> List[str]:
        """
        Get all active device tokens for a guard user.

        Args:
            user: User instance (should be a GUARD user)

        Returns:
            List of active Expo push tokens
        """
        from .models import Device
        
        devices = Device.objects.filter(user=user, is_active=True)
        return [device.token for device in devices]

    @staticmethod
    def handle_invalid_token(token: str) -> None:
        """
        Mark a device token as invalid.

        Args:
            token: Expo push token to mark as inactive
        """
        from .models import Device
        
        try:
            device = Device.objects.get(token=token)
            device.is_active = False
            device.save()
            logger.info(f"Marked device token as inactive: {token[:20]}...")
        except Device.DoesNotExist:
            logger.warning(f"Device token not found: {token[:20]}...")
