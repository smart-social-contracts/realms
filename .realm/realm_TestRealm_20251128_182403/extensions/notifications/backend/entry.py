import json
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List

from ggg import Notification, User
from kybra_simple_logging import get_logger

logger = get_logger("notifications.entry")


def _notification_to_dict(notification: Notification) -> Dict[str, Any]:
    """Convert Notification entity to dictionary format"""
    # Handle timestamp - it could be string or datetime object
    timestamp = notification.timestamp_created
    if hasattr(timestamp, "strftime"):
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    else:
        timestamp_str = str(timestamp) if timestamp else ""

    return {
        "id": notification.notification_id,
        "title": notification.title,
        "message": notification.message,
        "timestamp": timestamp_str,
        "read": notification.read,
        "icon": notification.icon,
        "href": notification.href,
        "color": notification.color,
    }


def get_notifications(args: str = "{}"):
    """Get all notifications for the current user"""
    try:
        logger.info("Fetching notifications")

        params = json.loads(args) if args else {}
        user_id = params.get("user_id")

        # Get all notifications from database
        notifications = Notification.instances()

        # Filter by user if user_id provided
        if user_id:
            notifications = [
                n for n in notifications if n.user and n.user.id == user_id
            ]

        # Convert to dict format
        notifications_list = [_notification_to_dict(n) for n in notifications]

        # Sort by timestamp, most recent first
        notifications_list.sort(key=lambda x: x["timestamp"], reverse=True)

        unread_count = sum(1 for n in notifications if not n.read)

        response = {
            "notifications": notifications_list,
            "unread_count": unread_count,
            "total_count": len(notifications_list),
        }

        logger.info(
            f"Returning {len(notifications_list)} notifications, {unread_count} unread"
        )
        return json.dumps(response)

    except Exception as e:
        error_msg = f"Error fetching notifications: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg, "notifications": [], "unread_count": 0})


def mark_as_read(args: str):
    """Mark a notification as read"""
    try:
        args_dict = json.loads(args) if args else {}
        notification_id = args_dict.get("notification_id")

        if not notification_id:
            return json.dumps({"error": "notification_id is required"})

        logger.info(f"Marking notification {notification_id} as read")

        # Find notification in database
        notification = None
        for n in Notification.instances():
            if n.notification_id == notification_id:
                notification = n
                break

        if notification:
            notification.read = True
            notification.save()
            logger.info(f"Successfully marked notification {notification_id} as read")
            return json.dumps({"success": True, "notification_id": notification_id})

        logger.warning(f"Notification {notification_id} not found")
        return json.dumps({"error": f"Notification {notification_id} not found"})

    except Exception as e:
        error_msg = f"Error marking notification as read: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def create_notification(args: str):
    """Create a new notification"""
    try:
        args_dict = json.loads(args) if args else {}

        required_fields = ["title", "message"]
        for field in required_fields:
            if field not in args_dict:
                return json.dumps({"error": f"{field} is required"})

        # Generate notification ID
        existing_notifications = Notification.instances()
        notification_id = f"notif_{len(existing_notifications) + 1:03d}"

        # Get user if user_id provided
        user = None
        user_id = args_dict.get("user_id")
        if user_id:
            for u in User.instances():
                if u.id == user_id:
                    user = u
                    break

        # Create notification entity
        new_notification = Notification(
            notification_id=notification_id,
            title=args_dict["title"],
            message=args_dict["message"],
            user=user,
            read=False,
            icon=args_dict.get("icon", "bell"),
            href=args_dict.get("href", "/notifications"),
            color=args_dict.get("color", "blue"),
            metadata=args_dict.get("metadata", "{}"),
        )

        logger.info(f"Created new notification: {notification_id}")
        return json.dumps({"success": True, "notification_id": notification_id})

    except Exception as e:
        error_msg = f"Error creating notification: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
