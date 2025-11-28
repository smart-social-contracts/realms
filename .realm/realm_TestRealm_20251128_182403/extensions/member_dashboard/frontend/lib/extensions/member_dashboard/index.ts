import MemberDashboard from './MemberDashboard.svelte';

export const metadata = {
  "name": "member_dashboard",
  "version": "1.0.0",
  "description": "Personal dashboard for members to manage their government services and documents",
  "author": "Smart Social Contracts",
  "permissions": [],
  "profiles": [
    "member",
    "admin"
  ],
  "categories": [
    "public_services"
  ],
  "icon": "table",
  "doc_url": "https://github.com/smart-social-contracts/realms/tree/main/extensions/member_dashboard",
  "url_path": null,
  "show_in_sidebar": true
};

export default MemberDashboard;
