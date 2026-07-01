/**
 * Federation portal iframe bridge (realm frontend side).
 */
import { DelegationIdentity, DelegationChain, Ed25519KeyIdentity } from '@dfinity/identity';

const BRIDGE_VERSION = '1';
const PORTAL_SESSION_KEY = 'realms:portal-embed';
let port = null;
let portalConfig = null;
let pendingDelegationRequest = false;
/** @type {Ed25519KeyIdentity | null} */
let sessionIdentity = null;
/** @type {DelegationIdentity | null} */
let delegationIdentity = null;

function markPortalEmbedded() {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.setItem(PORTAL_SESSION_KEY, '1');
  } catch {
    // private mode / sandbox without storage
  }
}

function isPortalEmbedded() {
  if (typeof window === 'undefined') return false;
  if (new URLSearchParams(window.location.search).get('portal') === '1') {
    markPortalEmbedded();
    return true;
  }
  if (port) return true;
  try {
    return sessionStorage.getItem(PORTAL_SESSION_KEY) === '1';
  } catch {
    return false;
  }
}

function post(msg) {
  if (!port) return;
  port.postMessage(msg);
}

function ensureSessionIdentity() {
  if (!sessionIdentity) {
    sessionIdentity = Ed25519KeyIdentity.generate();
  }
  return sessionIdentity;
}

function onPortMessage(event) {
  const msg = event.data;
  if (!msg || typeof msg.type !== 'string') return;

  switch (msg.type) {
    case 'config:realm':
      portalConfig = msg.payload || null;
      break;
    case 'auth:delegation':
      applyDelegation(msg.payload).catch((e) => {
        console.error('[portal-bridge] delegation apply failed:', e);
      });
      break;
    case 'auth:logout':
      delegationIdentity = null;
      window.dispatchEvent(new CustomEvent('portal:logout'));
      break;
    case 'auth:error':
      window.dispatchEvent(
        new CustomEvent('portal:auth-error', { detail: { error: msg.error || 'auth failed' } })
      );
      break;
    case 'nav:sync': {
      const path = msg.payload?.path || '/';
      window.dispatchEvent(new CustomEvent('portal:nav-sync', { detail: { path } }));
      break;
    }
    default:
      break;
  }
}

async function applyDelegation(payload) {
  if (!payload?.delegation) return;
  const session = ensureSessionIdentity();
  const json =
    typeof payload.delegation === 'string'
      ? payload.delegation
      : JSON.stringify(payload.delegation);
  const chain = DelegationChain.fromJSON(json);
  delegationIdentity = DelegationIdentity.fromDelegation(session, chain);
  window.dispatchEvent(
    new CustomEvent('portal:auth', {
      detail: {
        identity: delegationIdentity,
        backendCanisterId: payload.backendCanisterId,
        expiresAt: payload.expiresAt
      }
    })
  );
}

function requestDelegation() {
  if (!port) {
    pendingDelegationRequest = true;
    return;
  }
  pendingDelegationRequest = false;
  const session = ensureSessionIdentity();
  post({
    type: 'auth:request-delegation',
    payload: {
      sessionPublicKeyDer: Array.from(new Uint8Array(session.getPublicKey().toDer()))
    }
  });
}

export function getPortalDelegationIdentity() {
  return delegationIdentity;
}

export function getPortalConfig() {
  return portalConfig;
}

export function isEmbeddedInPortal() {
  return isPortalEmbedded();
}

export function initPortalBridge() {
  if (!isPortalEmbedded()) return () => {};
  if (typeof window === 'undefined') return () => {};

  markPortalEmbedded();

  const onWindowMessage = (event) => {
    if (event.data?.type !== 'bridge:init' || !event.ports?.[0]) return;
    port = event.ports[0];
    port.onmessage = onPortMessage;
    post({ type: 'bridge:ready', payload: { version: BRIDGE_VERSION } });
    requestDelegation();
  };

  window.addEventListener('message', onWindowMessage);

  return () => {
    window.removeEventListener('message', onWindowMessage);
    port = null;
  };
}

export function portalNavPush(path) {
  if (!isPortalEmbedded() || !port) return false;
  post({ type: 'nav:push', payload: { path } });
  return true;
}

export function reportResize(height) {
  if (!port) return;
  post({ type: 'resize:report', payload: { height } });
}

export function requestAuthRefresh() {
  requestDelegation();
}

/**
 * Wait for the portal host to deliver a scoped II delegation.
 * @param {{ timeoutMs?: number }} [opts]
 * @returns {Promise<DelegationIdentity | null>}
 */
export function waitForPortalDelegation({ timeoutMs = 60_000 } = {}) {
  const existing = getPortalDelegationIdentity();
  if (existing) return Promise.resolve(existing);

  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      window.removeEventListener('portal:auth', onAuth);
      resolve(value);
    };

    const onAuth = () => {
      const identity = getPortalDelegationIdentity();
      if (identity) finish(identity);
    };

    const timer = setTimeout(() => finish(null), timeoutMs);
    window.addEventListener('portal:auth', onAuth);
    requestAuthRefresh();
  });
}
