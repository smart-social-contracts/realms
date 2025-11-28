import Notifications from './Notifications.svelte';

export const metadata = {
  "name": "notifications",
  "version": "1.0.0",
  "description": "Real-time notifications and alerts system",
  "permissions": [],
  "entry_points": [
    "get_notifications",
    "mark_as_read",
    "create_notification"
  ],
  "profiles": [
    "member",
    "admin"
  ],
  "categories": [
    "other"
  ],
  "icon": "bell",
  "doc_url": "https://github.com/smart-social-contracts/realms/tree/main/extensions/notifications",
  "url_path": null,
  "show_in_sidebar": true
};

export default Notifications;
