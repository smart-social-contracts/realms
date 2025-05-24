/**
 * Script to replace version and commit hash placeholders in app.html
 * Run this during prebuild to ensure that the HTML template has proper values
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get directory paths
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '../../..');
const versionFilePath = path.join(rootDir, 'version.txt');
const appHtmlPath = path.join(__dirname, '../src/app.html');

// Get version from version.txt
let version = '0.0.0';
try {
  version = fs.readFileSync(versionFilePath, 'utf8').trim();
  console.log(`Using version: ${version}`);
} catch (error) {
  console.warn(`Failed to read version.txt: ${error.message}`);
  console.warn('Using default version: 0.0.0');
}

// Generate a commit hash (for development, just use a timestamp)
const commitHash = `dev-${Date.now().toString(16)}`;

// Read the app.html file
console.log(`Reading app.html from: ${appHtmlPath}`);
let appHtml;
try {
  appHtml = fs.readFileSync(appHtmlPath, 'utf8');
} catch (error) {
  console.error(`Failed to read app.html: ${error.message}`);
  process.exit(1);
}

// Replace placeholders
appHtml = appHtml
  .replace('VERSION_PLACEHOLDER', version)
  .replace('COMMIT_HASH_PLACEHOLDER', commitHash);

// Write the updated app.html
try {
  fs.writeFileSync(appHtmlPath, appHtml);
  console.log('Successfully updated app.html with version and commit hash');
} catch (error) {
  console.error(`Failed to write app.html: ${error.message}`);
  process.exit(1);
}