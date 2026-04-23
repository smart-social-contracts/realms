/**
 * Build the JSON manifest for realm_registry_backend.request_deployment.
 *
 * @param {object} formData - create-realm wizard state
 * @param {string} network - e.g. staging, demo
 */
export function buildRealmDeploymentManifest(formData, network) {
  const name = (formData.name || '').trim();
  const lang = (formData.languages && formData.languages[0]) || 'en';

  let description = (formData.descriptions && formData.descriptions[lang]) || '';
  if (!description && formData.descriptions) {
    description =
      Object.values(formData.descriptions).find((s) => s && String(s).trim()) || '';
  }
  description = String(description).trim() || `Welcome to ${name}.`;

  let welcome_message = (formData.welcome_messages && formData.welcome_messages[lang]) || '';
  if (!welcome_message && formData.welcome_messages) {
    welcome_message =
      Object.values(formData.welcome_messages).find((s) => s && String(s).trim()) || '';
  }
  welcome_message =
    String(welcome_message).trim() || `Welcome to ${name}!`;

  const realm = {
    name,
    display_name: name,
    description,
    welcome_message,
    branding: {
      logo: 'emblem.png',
      welcome_image: 'background.png',
    },
    extensions: Array.isArray(formData.extensions) ? [...formData.extensions] : ['all'],
  };

  if (formData.codex_source === 'package' && formData.codex_package_name?.trim()) {
    realm.codex = {
      package: formData.codex_package_name.trim(),
      version: (formData.codex_package_version || 'latest').trim(),
    };
  } else {
    realm.codex = { package: 'syntropia', version: 'latest' };
  }

  if (formData.assistant) {
    realm.assistant = formData.assistant;
  }

  return { realm, network: network || 'staging' };
}
