import ERDExplorer from './ERDExplorer.svelte';

export const metadata = {
  "name": "erd_explorer",
  "version": "1.0.0",
  "description": "Interactive Entity Relationship Diagram explorer for visualizing and navigating Realms data structure",
  "author": "Realms Team",
  "permissions": [],
  "entry_points": [
    "get_entity_schema",
    "get_entity_data"
  ],
  "profiles": [
    "member",
    "admin"
  ],
  "categories": [
    "other"
  ],
  "icon": "table",
  "doc_url": "https://github.com/smart-social-contracts/realms/tree/main/extensions/erd_explorer",
  "url_path": null,
  "show_in_sidebar": true
};

export default ERDExplorer;
