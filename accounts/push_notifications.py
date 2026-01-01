"""
Push notification service for Expo push notifications.
Handles sending notifications to mobile devices via Expo's push API.
Simple, reliable implementation using requests library.
"""

import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Expo Push API endpoint
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


class PushNotificationService:
    """Service to send push notifications via Expo using requests library."""

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
        if not expo_token:
            logger.warning("Empty expo token provided")
            return False
        
        if not str(expo_token).startswith("ExponentPushToken"):
            logger.warning(f"Invalid expo token format: {expo_token}")
            return False

        payload = {
            "to": expo_token,
            "sound": sound,
            "title": title,
            "body": body,
            "priority": priority,
        }

        if data:
            payload["data"] = data

        try:
            logger.info(f"Sending push notification to {expo_token[:30]}...")
            response = requests.post(EXPO_PUSH_URL, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Push notification sent successfully: {result}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send push notification: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending push: {str(e)}")
            return False

    @staticmethod
    def send_with_logging(
        recipient,
        expo_token: str,
        notification_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        incident=None,
        guard_alert=None,
        max_retries: int = 3
    ) -> bool:
        """
        Send push notification with database logging and retry logic.
        
        Creates a PushNotificationLog entry for audit trail.
        Retries up to max_retries times on failure.
        Updates GuardAlert tracking fields if provided.
        
        Args:
            recipient: User receiving the notification
            expo_token: Expo push token
            notification_type: PushNotificationLog.NotificationType choice
            title: Notification title
            body: Notification body
            data: Additional data payload
            incident: Related Incident (optional)
            guard_alert: Related GuardAlert (optional)
            max_retries: Max retry attempts (default: 3)
        
        Returns:
            bool: True if sent successfully
        """
        from django.utils import timezone
        from .models import PushNotificationLog
        
        if not expo_token or not str(expo_token).startswith("ExponentPushToken"):
            logger.warning(f"Invalid expo token for logging: {expo_token}")
            return False
        
        # Create log entry in QUEUED status
        log = PushNotificationLog.objects.create(
            recipient=recipient,
            device_token=expo_token,
            notification_type=notification_type,
            incident=incident,
            guard_alert=guard_alert,
            title=title,
            body=body,
            data_payload=data or {},
            status=PushNotificationLog.Status.QUEUED,
            max_retries=max_retries
        )
        
        # Retry loop
        success = False
        last_error = ""
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                payload = {
                    "to": expo_token,
                    "sound": "default",
                    "title": title,
                    "body": body,
                    "priority": "high",
                }
                if data:
                    payload["data"] = data
                
                response = requests.post(EXPO_PUSH_URL, json=payload, timeout=10)
                response.raise_for_status()
                result = response.json()
                
                # Check for Expo-level errors
                if result.get("data"):
                    ticket = result["data"][0] if isinstance(result["data"], list) else result["data"]
                    if ticket.get("status") == "error":
                        error_details = ticket.get("details", {})
                        error_code = error_details.get("error")
                        
                        # Handle invalid token immediately
                        if error_code == "DeviceNotRegistered":
                            logger.warning(f"[PUSH] Device token no longer valid: {expo_token}")
                            PushNotificationService.handle_invalid_token(expo_token)
                            log.status = PushNotificationLog.Status.INVALID_TOKEN
                            log.save()
                            return False
                            
                        raise Exception(ticket.get("message", "Expo error"))
                    log.expo_ticket_id = ticket.get("id", "")
                
                # Success!
                log.status = PushNotificationLog.Status.SENT
                log.sent_at = timezone.now()
                log.save()
                
                # Update GuardAlert if provided
                if guard_alert:
                    guard_alert.push_notification_sent = True
                    guard_alert.push_notification_sent_at = timezone.now()
                    guard_alert.save(update_fields=[
                        'push_notification_sent', 
                        'push_notification_sent_at'
                    ])
                
                logger.info(
                    f"[PUSH] ✅ Notification sent to {str(recipient.id)[:8]} "
                    f"(attempt {attempt + 1}/{max_retries + 1})"
                )
                success = True
                break
                
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                log.retry_count = attempt + 1
                log.save(update_fields=['retry_count'])
                
                if attempt < max_retries:
                    logger.warning(
                        f"[PUSH] Retry {attempt + 1}/{max_retries} for {str(recipient.id)[:8]}: {e}"
                    )
                    import time
                    time.sleep(1)  # Brief delay between retries
                    
            except Exception as e:
                last_error = str(e)
                log.retry_count = attempt + 1
                log.save(update_fields=['retry_count'])
                
                if attempt < max_retries:
                    logger.warning(f"[PUSH] Retry {attempt + 1}/{max_retries}: {e}")
                    import time
                    time.sleep(1)
        
        # If all retries failed
        if not success:
            log.status = PushNotificationLog.Status.FAILED
            log.failed_at = timezone.now()
            log.error_message = last_error
            log.save()
            
            # Update GuardAlert with error
            if guard_alert:
                guard_alert.push_notification_error = last_error[:500]
                guard_alert.save(update_fields=['push_notification_error'])
            
            logger.error(
                f"[PUSH] ❌ Failed after {max_retries + 1} attempts for {str(recipient.id)[:8]}: {last_error}"
            )
        
        return success

    @staticmethod
    def send_batch_notifications(
        messages: List[Dict[str, Any]]
    ) -> List[bool]:
        """
        Send multiple push notifications in a batch.

        Args:
            messages: List of dicts with:
                - to: Expo push token
                - title: Notification title
                - body: Notification body
                - data: Optional data dict
                - priority: Optional priority level
                - sound: Optional sound

        Returns:
            List of bools indicating success for each notification
        """
        if not messages:
            logger.warning("No messages provided for batch send")
            return []

        results = []
        for idx, msg in enumerate(messages):
            token = msg.get("to")
            if not token:
                logger.warning(f"Message {idx} missing 'to' field")
                results.append(False)
                continue
            
            success = PushNotificationService.send_notification(
                expo_token=token,
                title=msg.get("title", ""),
                body=msg.get("body", ""),
                data=msg.get("data"),
                sound=msg.get("sound", "default"),
                priority=msg.get("priority", "high")
            )
            results.append(success)

        sent_count = sum(1 for r in results if r)
        logger.info(f"Batch send: {sent_count}/{len(messages)} notifications sent successfully")
        return results

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
