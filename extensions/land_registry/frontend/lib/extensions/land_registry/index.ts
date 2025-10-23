import AdminControls from './AdminControls.svelte';

export const metadata = {
  "name": "land_registry",
  "version": "1.0.0",
  "description": "Property registration and land ownership management",
  "permissions": [],
  "entry_points": [
    "get_lands",
    "create_land",
    "update_land_ownership",
    "get_land_map"
  ],
  "profiles": [
    "admin"
  ],
  "categories": [
    "public_services"
  ],
  "icon": "map_pin",
  "doc_url": "https://github.com/smart-social-contracts/realms/tree/main/extensions/land_registry",
  "url_path": null,
  "show_in_sidebar": true
};

export default AdminControls;
