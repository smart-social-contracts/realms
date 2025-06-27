import json
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List

from kybra import Record
from kybra_simple_logging import get_logger

logger = get_logger("notifications.entry")


class NotificationItem(Record):
    id: str
    title: str
    message: str
    timestamp: str
    read: bool
    icon: str
    href: str
    color: str


notifications_storage: List[Dict[str, Any]] = [
    {
        "id": "1",
        "title": "Welcome to Realms",
        "message": "Your account has been successfully created and verified. Welcome to the digital governance platform!",
        "timestamp": "a few moments ago",
        "read": False,
        "icon": "users",
        "href": "/dashboard",
        "color": "green",
    },
    {
        "id": "2",
        "title": "New Task Assignment",
        "message": "You have been assigned a new governance task that requires your attention. Please review the details and take appropriate action.",
        "timestamp": "10 minutes ago",
        "read": False,
        "icon": "clipboard",
        "href": "/ggg",
        "color": "blue",
    },
    {
        "id": "3",
        "title": "Vault Transaction Completed",
        "message": "A transfer of 100 tokens has been completed successfully. Your vault balance has been updated.",
        "timestamp": "1 hour ago",
        "read": True,
        "icon": "wallet",
        "href": "/extensions/vault_manager",
        "color": "purple",
    },
    {
        "id": "4",
        "title": "System Maintenance Notice",
        "message": "Scheduled maintenance will occur tonight from 2:00 AM to 4:00 AM UTC. Some services may be temporarily unavailable.",
        "timestamp": "2 hours ago",
        "read": False,
        "icon": "cog",
        "href": "/settings",
        "color": "red",
    },
    {
        "id": "5",
        "title": "New Extension Available",
        "message": "The Justice Litigation extension has been added to the marketplace. Check it out to manage legal processes.",
        "timestamp": "1 day ago",
        "read": True,
        "icon": "layers",
        "href": "/extensions",
        "color": "purple",
    },
]


def get_notifications(args: str = "{}"):
    """Get all notifications for the current user"""
    try:
        logger.info("Fetching notifications")

        unread_count = sum(1 for n in notifications_storage if not n["read"])

        response = {
            "notifications": notifications_storage,
            "unread_count": unread_count,
            "total_count": len(notifications_storage),
        }

        logger.info(
            f"Returning {len(notifications_storage)} notifications, {unread_count} unread"
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

        for notification in notifications_storage:
            if notification["id"] == notification_id:
                notification["read"] = True
                logger.info(
                    f"Successfully marked notification {notification_id} as read"
                )
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

        notification_id = str(len(notifications_storage) + 1)

        new_notification = {
            "id": notification_id,
            "title": args_dict["title"],
            "message": args_dict["message"],
            "timestamp": "just now",
            "read": False,
            "icon": args_dict.get("icon", "bell"),
            "href": args_dict.get("href", "/notifications"),
            "color": args_dict.get("color", "blue"),
        }

        notifications_storage.insert(0, new_notification)

        logger.info(f"Created new notification: {notification_id}")
        return json.dumps({"success": True, "notification_id": notification_id})

    except Exception as e:
        error_msg = f"Error creating notification: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
