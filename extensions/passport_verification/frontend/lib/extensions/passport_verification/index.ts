import PassportVerification from './PassportVerification.svelte';

export const metadata = {
  "name": "passport_verification",
  "version": "1.0.0",
  "description": "Rarimo ZK Passport verification extension for secure identity verification",
  "author": "Realms Team",
  "permissions": [],
  "functions": [
    "get_verification_link",
    "check_verification_status",
    "create_passport_identity"
  ],
  "profiles": [
    "member",
    "admin"
  ],
  "categories": [
    "public_services"
  ],
  "icon": "id_card",
  "doc_url": "https://github.com/smart-social-contracts/realms/tree/main/extensions/passport_verification",
  "url_path": null,
  "show_in_sidebar": true
};

export default PassportVerification;
