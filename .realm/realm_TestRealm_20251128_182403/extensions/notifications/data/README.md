# Notifications Extension Data

This directory contains initial data for the notifications extension.

## notifications_data.json

Contains initial user notifications that will be loaded into the database during realm deployment.

### Data Structure

The file follows the GGG entity format. Each notification record includes:

- **_type**: "Notification"
- **_id**: Unique identifier for the entity
- **Standard fields**: timestamp_created, timestamp_updated, creator, updater, owner
- **Entity-specific fields**:
  - notification_id: Human-readable notification ID (e.g., "notif_001")
  - title: Notification title
  - message: Detailed notification message
  - user: Reference to User entity ID
  - read: Boolean indicating if notification has been read
  - icon: Icon name for display (e.g., "bell", "users", "clipboard")
  - href: Link URL for the notification
  - color: Color scheme (e.g., "blue", "green", "red", "purple")
  - metadata: Additional metadata as JSON string

### Loading Data

This data is automatically loaded during realm deployment via the automatic extension data loading feature.

When you run `realms realm create --deploy` or deploy a generated realm, the system will:
1. Discover all `extensions/*/data/*.json` files
2. Import them automatically

### Notes

- The `user` field references existing User entity IDs in your realm
- Default sample data uses user IDs "3" and "4" (user_001 and user_002 in default realm data)
- Adjust user references based on your actual realm data
- Notifications can be filtered by user_id when calling `get_notifications`
