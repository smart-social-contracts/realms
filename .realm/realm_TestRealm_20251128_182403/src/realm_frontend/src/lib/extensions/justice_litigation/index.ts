import CreateLitigationForm from './CreateLitigationForm.svelte';

export const metadata = {
  "name": "justice_litigation",
  "version": "0.1.0",
  "description": "Legal case management and litigation tracking system",
  "permissions": [],
  "entry_points": [
    "get_litigations",
    "create_litigation",
    "execute_verdict",
    "load_demo_litigations"
  ],
  "profiles": [
    "admin",
    "member"
  ],
  "categories": [
    "public_services"
  ],
  "icon": "scale",
  "doc_url": "https://github.com/smart-social-contracts/realms/tree/main/extensions/justice_litigation",
  "url_path": null,
  "show_in_sidebar": true
};

export default CreateLitigationForm;
