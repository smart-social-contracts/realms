import PublicDashboard from './PublicDashboard.svelte';

export const metadata = {
  "name": "public_dashboard",
  "version": "1.0.0",
  "description": "Public dashboard with analytics and statistics for the realm",
  "author": "Smart Social Contracts",
  "permissions": [],
  "profiles": [
    "member",
    "admin"
  ],
  "categories": [
    "oversight"
  ],
  "icon": "table",
  "doc_url": "https://github.com/smart-social-contracts/realms/tree/main/extensions/public_dashboard",
  "url_path": null,
  "show_in_sidebar": true
};

export default PublicDashboard;
