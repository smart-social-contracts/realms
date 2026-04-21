// Browser-side client for the realm_installer canister.
//
// Provides deploy_realm (kick off) and get_deploy_status (polling).
// Both methods exchange JSON-over-text with the canister.

import { Actor, HttpAgent } from '@dfinity/agent';
import { IDL } from '@dfinity/candid';
import { Principal } from '@dfinity/principal';
import { initializeAuthClient } from './auth';

const realmInstallerIdlFactory = ({ IDL: idl }) =>
  idl.Service({
    deploy_realm: idl.Func([idl.Text], [idl.Text], []),
    get_deploy_status: idl.Func([idl.Text], [idl.Text], ['query']),
  });

let _cachedActor = null;
let _cachedCanisterId = null;

async function getInstallerActor(canisterId) {
  if (_cachedActor && _cachedCanisterId === canisterId) return _cachedActor;

  const client = await initializeAuthClient();
  const identity = client.getIdentity();
  const agent = new HttpAgent({ identity });
  if (
    typeof window !== 'undefined' &&
    (window.location.hostname.includes('localhost') ||
      window.location.hostname.includes('127.0.0.1'))
  ) {
    try { await agent.fetchRootKey(); } catch (e) { /* local dev */ }
  }
  _cachedActor = Actor.createActor(realmInstallerIdlFactory, {
    agent,
    canisterId: Principal.fromText(canisterId),
  });
  _cachedCanisterId = canisterId;
  return _cachedActor;
}

/**
 * Submit a deploy_realm manifest and return the parsed response.
 * @param {string} installerCanisterId
 * @param {object} manifest
 * @returns {Promise<{success: boolean, task_id?: string, error?: string}>}
 */
export async function deployRealm(installerCanisterId, manifest) {
  const actor = await getInstallerActor(installerCanisterId);
  const raw = await actor.deploy_realm(JSON.stringify(manifest));
  return JSON.parse(String(raw));
}

/**
 * Poll deploy status.
 * @param {string} installerCanisterId
 * @param {string} taskId
 * @returns {Promise<object>}
 */
export async function getDeployStatus(installerCanisterId, taskId) {
  const actor = await getInstallerActor(installerCanisterId);
  const raw = await actor.get_deploy_status(taskId);
  return JSON.parse(String(raw));
}
