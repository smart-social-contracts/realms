/**
 * Upload deployment files (branding images + realm data) to the deploy service.
 *
 * Returns an object like:
 *   { logo_url: "https://deploy.../branding/files/abc/logo.png",
 *     welcome_image_url: "https://deploy.../branding/files/def/bg.png",
 *     realm_data_url: "https://deploy.../branding/files/ghi/realm_data.json" }
 */
import { CONFIG } from './config.js';

/**
 * @param {{ logo?: File|null, welcome_image?: File|null, realm_data?: File|null }} files
 * @returns {Promise<{ logo_url?: string, welcome_image_url?: string, realm_data_url?: string }>}
 */
export async function uploadBrandingFiles(files) {
  const { logo, welcome_image, realm_data } = files;
  if (!logo && !welcome_image && !realm_data) return {};

  const form = new FormData();
  if (logo) form.append('logo', logo);
  if (welcome_image) form.append('welcome_image', welcome_image);
  if (realm_data) form.append('realm_data', realm_data);

  const base = CONFIG.deploy_service_url.replace(/\/+$/, '');
  const resp = await fetch(`${base}/branding/upload`, {
    method: 'POST',
    body: form,
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Deploy file upload failed (${resp.status}): ${body}`);
  }

  const { uploaded } = await resp.json();
  const result = {};
  if (uploaded?.logo?.download_path) {
    result.logo_url = `${base}${uploaded.logo.download_path}`;
  }
  if (uploaded?.welcome_image?.download_path) {
    result.welcome_image_url = `${base}${uploaded.welcome_image.download_path}`;
  }
  if (uploaded?.realm_data?.download_path) {
    result.realm_data_url = `${base}${uploaded.realm_data.download_path}`;
  }
  return result;
}
