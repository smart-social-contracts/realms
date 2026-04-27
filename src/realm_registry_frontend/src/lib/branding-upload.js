/**
 * Upload branding images to the deploy service via /upload-file.
 *
 * Returns { logo?: "https://deploy.../...", background?: "https://deploy.../..." }
 * matching the manifest branding schema.
 */
import { CONFIG } from './config.js';

async function _uploadSingleFile(file, base) {
  const form = new FormData();
  form.append('file', file);

  const resp = await fetch(`${base}/upload-file`, {
    method: 'POST',
    body: form,
  });

  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`File upload failed (${resp.status}): ${body}`);
  }

  const result = await resp.json();
  return `${base}${result.url}`;
}

/**
 * @param {{ logo?: File|null, background?: File|null }} files
 * @returns {Promise<{ logo?: string, background?: string }>}
 */
export async function uploadBrandingFiles(files) {
  const { logo, background } = files;
  if (!logo && !background) return {};

  const base = CONFIG.deploy_service_url.replace(/\/+$/, '');
  const result = {};

  if (logo) {
    result.logo = await _uploadSingleFile(logo, base);
  }
  if (background) {
    result.background = await _uploadSingleFile(background, base);
  }

  return result;
}
