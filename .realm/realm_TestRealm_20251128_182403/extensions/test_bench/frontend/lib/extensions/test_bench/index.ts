import Testbench from './Testbench.svelte';

export const metadata = {
  "name": "test_bench",
  "version": "0.1.0",
  "description": "Development testing and debugging tools",
  "author": "Smart Social Contracts Team",
  "permissions": [
    "read_vault",
    "transfer_tokens"
  ],
  "profiles": [
    "admin"
  ],
  "enabled": false,
  "categories": [
    "other"
  ],
  "icon": "lightbulb",
  "doc_url": "https://github.com/smart-social-contracts/realms/tree/main/extensions/test_bench",
  "url_path": null,
  "show_in_sidebar": false
};

export default Testbench;
