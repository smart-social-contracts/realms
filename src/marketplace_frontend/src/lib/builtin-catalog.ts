// Static catalog of built-in extensions and codices shipped with Realms.
//
// When the marketplace_backend canister is empty or unreachable, the UI
// falls back to this list so the marketplace always shows real content.

import type { ExtensionListing, CodexListing } from './marketplace-client';

const now = Date.now() * 1_000_000;

function ext(
  id: string,
  name: string,
  description: string,
  version: string,
  icon: string,
  cats: string,
): ExtensionListing {
  return {
    extension_id: id,
    developer: 'Realms Team',
    name,
    description,
    version,
    price_e8s: 0,
    icon,
    categories: cats,
    file_registry_canister_id: '',
    file_registry_namespace: `ext/${id}/${version}`,
    download_url: `https://github.com/smart-social-contracts/realms/tree/main/extensions/extensions/${id}`,
    installs: 0,
    likes: 0,
    verification_status: 'verified',
    verification_notes: 'Built-in',
    is_active: true,
    created_at: now,
    updated_at: now,
  };
}

function codex(
  id: string,
  alias: string,
  name: string,
  description: string,
  version: string,
  icon: string,
  cats: string,
  realmType: string,
): CodexListing {
  return {
    codex_id: id,
    codex_alias: alias,
    realm_type: realmType,
    developer: 'Realms Team',
    name,
    description,
    version,
    price_e8s: 0,
    icon,
    categories: cats,
    file_registry_canister_id: '',
    file_registry_namespace: `codex/${id}/${version}`,
    installs: 0,
    likes: 0,
    verification_status: 'verified',
    verification_notes: 'Built-in',
    is_active: true,
    created_at: now,
    updated_at: now,
  };
}

export const builtinExtensions: ExtensionListing[] = [
  ext(
    'voting',
    'Voting',
    'Governance voting system for submitting and voting on proposals to execute Python code',
    '1.0.3', '🗳️', 'public_services',
  ),
  ext(
    'vault',
    'Vault',
    'Admin treasury dashboard for Realms. View token balances, transaction history, and perform ad-hoc transfers.',
    '0.2.0', '💰', 'finances',
  ),
  ext(
    'member_dashboard',
    'Member Dashboard',
    'Personal dashboard for members to manage their government services and documents',
    '1.0.3', '📊', 'public_services',
  ),
  ext(
    'admin_dashboard',
    'Admin Dashboard',
    'Comprehensive administrative dashboard for the Generalized Global Governance System',
    '1.0.5', '⚙️', 'other',
  ),
  ext(
    'metrics',
    'Metrics',
    'Financial statements, accounting data, and analytics dashboard for realm performance',
    '1.1.0', '📈', 'oversight',
  ),
  ext(
    'public_dashboard',
    'Public Dashboard',
    'Public dashboard with analytics and statistics for the realm',
    '1.0.3', '📊', 'oversight',
  ),
  ext(
    'llm_chat',
    'AI Governance Assistant',
    'AI-powered assistant for governance and legal questions',
    '0.1.3', '🧠', 'oversight',
  ),
  ext(
    'passport_verification',
    'Passport Verification',
    'Rarimo ZK Passport verification extension for secure identity verification using zero-knowledge proofs',
    '1.0.4', '🪪', 'public_services',
  ),
  ext(
    'justice_litigation',
    'Justice & Litigation',
    'Comprehensive legal case management with courts, judges, verdicts, penalties, and appeals',
    '0.2.0', '⚖️', 'public_services',
  ),
  ext(
    'land_registry',
    'Land Registry',
    'Property registration and land ownership management',
    '1.1.0', '📍', 'public_services',
  ),
  ext(
    'zone_selector',
    'Zone Selector',
    'Allow users to set their zones of influence via geolocation or map selection',
    '1.0.0', '🗺️', 'public_services',
  ),
  ext(
    'notifications',
    'Notifications',
    'Real-time notifications and alerts system',
    '1.0.3', '🔔', 'other',
  ),
  ext(
    'erd_explorer',
    'ERD Explorer',
    'Interactive Entity Relationship Diagram explorer for visualizing and navigating Realms data structure',
    '1.0.3', '🔗', 'other',
  ),
  ext(
    'codex_viewer',
    'Codex Viewer',
    'View and browse Codex automation scripts',
    '1.0.0', '📜', 'other',
  ),
  ext(
    'package_manager',
    'Package Manager',
    'Install, update and uninstall extensions and codex packages from connected file registries',
    '0.1.0', '📦', 'other',
  ),
  ext(
    'system_info',
    'System Info',
    'System information dashboard for realm administrators',
    '1.0.0', '📈', 'oversight',
  ),
  ext(
    'task_monitor',
    'Task Monitor',
    'Task monitoring and management dashboard for administrators',
    '1.0.0', '📋', 'other',
  ),
  ext(
    'market_place',
    'Marketplace',
    'Extensions marketplace for browsing, purchasing, and publishing extensions',
    '2.0.0', '🏪', 'system',
  ),
  ext(
    'welcome',
    'Welcome',
    'Welcome page and onboarding for new users',
    '1.0.3', '🏠', 'other',
  ),
];

export const builtinCodices: CodexListing[] = [
  codex(
    'agora', 'agora',
    'Agora',
    'A direct democracy funded by monthly membership dues. Citizens verify identity via ZK passport, pay monthly bills, submit and vote on proposals, with real-time double-entry accounting.',
    '1.0.0', '🏛️', 'governance',
    'agora',
  ),
  codex(
    'dominion', 'dominion',
    'Dominion',
    'A direct democracy with progressive taxation. Citizens propose and vote on decisions collectively while a tax system funds realm operations.',
    '0.1.0', '👑', 'governance',
    'dominion',
  ),
  codex(
    'syntropia', 'syntropia',
    'Syntropia',
    'A full-featured representative democracy with three branches of government — parliament, executive, and judiciary — plus universal welfare, progressive taxation, and territorial governance.',
    '1.0.0', '🌿', 'governance',
    'syntropia',
  ),
  codex(
    'westminster', 'westminster',
    'Westminster',
    'A parliamentary democracy with land treaties, licensing, tax collection, and a full realm lifecycle from early sign-up through operation to wind-down.',
    '1.0.0', '🏰', 'governance',
    'westminster',
  ),
];
