"""
Push notification service for Expo push notifications.
Handles sending notifications to mobile devices via Expo's push API.
Uses the official exponent_server_sdk for robust notification handling.
"""

import logging
from typing import List, Dict, Any, Optional
from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
    PushServerError,
    PushTicketError,
)

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service to send push notifications via Expo using the official SDK."""

    @staticmethod
    def send_notification(
        expo_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        sound: str = "default",
        priority: str = "high"
    ) -> bool:
        """
        Send a single push notification via Expo.

        Args:
            expo_token: Expo push token (must start with ExponentPushToken[)
            title: Notification title
            body: Notification body/message
            data: Additional data payload for the mobile app
            sound: Sound to play (default: "default")
            priority: Notification priority (default, normal, high)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not expo_token or not expo_token.startswith("ExponentPushToken"):
            logger.warning(f"Invalid or missing Expo token: {expo_token}")
            return False

        try:
            message = PushMessage(
                to=expo_token,
                title=title,
                body=body,
                data=data or {},
                sound=sound,
                priority=priority,
            )
            
            response = PushClient().publish(message)
            response.validate_response()
            logger.info(f"Push notification sent successfully to {expo_token[:30]}...")
            return True
        except DeviceNotRegisteredError:
            logger.warning(f"Device token no longer registered: {expo_token[:30]}...")
            return False
        except PushServerError as e:
            logger.error(f"Expo server error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send notification to {expo_token}: {str(e)}")
            return False

    @staticmethod
    def send_batch_notifications(
        tokens_and_messages: List[Dict[str, Any]]
    ) -> List[bool]:
        """
        Send multiple push notifications in a batch.

        Args:
            tokens_and_messages: List of dicts with:
                - to: Expo push token
                - title: Notification title
                - body: Notification body
                - data: Optional data dict
                - priority: Optional priority level

        Returns:
            List of bools indicating success for each notification
        """
        if not tokens_and_messages:
            logger.warning("No messages provided for batch send")
            return []

        # Filter and build valid messages
        messages = []
        for msg in tokens_and_messages:
            token = msg.get("to")
            if token and token.startswith("ExponentPushToken"):
                try:
                    push_msg = PushMessage(
                        to=token,
                        title=msg.get("title", ""),
                        body=msg.get("body", ""),
                        data=msg.get("data", {}),
                        sound=msg.get("sound", "default"),
                        priority=msg.get("priority", "high"),
                    )
                    messages.append(push_msg)
                except Exception as e:
                    logger.error(f"Invalid message format: {str(e)}")
            else:
                logger.warning(f"Invalid token in batch: {token}")

        if not messages:
            logger.warning("No valid messages to send")
            return []

        try:
            responses = PushClient().publish_multiple(messages)
            results = []
            for idx, response in enumerate(responses):
                try:
                    response.validate_response()
                    results.append(True)
                    logger.info(f"Batch message {idx + 1} sent successfully")
                except (PushTicketError, PushServerError) as e:
                    logger.warning(f"Batch message {idx + 1} failed: {str(e)}")
                    results.append(False)
            return results
        except PushServerError as e:
            logger.error(f"Batch push failed: {str(e)}")
            return [False] * len(messages)

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
                "title": "🚨 Incoming Alert",
                "body": f"{priority} - {location}",
                "data": {
                    "type": "GUARD_ALERT",
                    "incident_id": str(incident_id),
                    "alert_id": str(alert_id),
                    "priority": priority,
                    "location": location,
                },
                "priority": "high",
            }
            messages.append(message)

        if len(messages) == 1:
            PushNotificationService.send_notification(
                expo_tokens[0],
                "🚨 Incoming Alert",
                f"{priority} - {location}",
                messages[0].get("data"),
                priority="high",
            )
        else:
            results = PushNotificationService.send_batch_notifications(messages)
            sent_count = sum(1 for r in results if r)
            logger.info(f"Guard alerts: {sent_count}/{len(messages)} sent successfully")

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
                "title": "✅ Assignment Confirmed",
                "body": "You are assigned to an incident",
                "data": {
                    "type": "ASSIGNMENT_CONFIRMED",
                    "incident_id": str(incident_id),
                },
                "priority": "high",
            }
            messages.append(message)

        if len(messages) == 1:
            PushNotificationService.send_notification(
                expo_tokens[0],
                "✅ Assignment Confirmed",
                "You are assigned to an incident",
                messages[0].get("data"),
            )
        else:
            results = PushNotificationService.send_batch_notifications(messages)
            sent_count = sum(1 for r in results if r)
            logger.info(f"Assignment confirmations: {sent_count}/{len(messages)} sent")

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
        preview = message_preview[:50] if message_preview else "(no message)"
        for token in expo_tokens:
            message = {
                "to": token,
                "sound": "default",
                "title": "💬 New Message",
                "body": f"{sender_name}: {preview}",
                "data": {
                    "type": "NEW_CHAT_MESSAGE",
                    "incident_id": str(incident_id),
                    "conversation_id": str(conversation_id),
                    "sender": sender_name,
                },
            }
            messages.append(message)

        if len(messages) == 1:
            PushNotificationService.send_notification(
                expo_tokens[0],
                "💬 New Message",
                f"{sender_name}: {preview}",
                messages[0].get("data"),
            )
        else:
            results = PushNotificationService.send_batch_notifications(messages)
            sent_count = sum(1 for r in results if r)
            logger.info(f"Chat messages: {sent_count}/{len(messages)} sent")

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
                "title": "⚠️ Incident Escalated",
                "body": f"Priority raised to {new_priority}",
                "data": {
                    "type": "INCIDENT_ESCALATED",
                    "incident_id": str(incident_id),
                    "new_priority": new_priority,
                },
                "priority": "high",
            }
            messages.append(message)

        if len(messages) == 1:
            PushNotificationService.send_notification(
                expo_tokens[0],
                "⚠️ Incident Escalated",
                f"Priority raised to {new_priority}",
                messages[0].get("data"),
                priority="high",
            )
        else:
            results = PushNotificationService.send_batch_notifications(messages)
            sent_count = sum(1 for r in results if r)
            logger.info(f"Escalation notifications: {sent_count}/{len(messages)} sent")

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
