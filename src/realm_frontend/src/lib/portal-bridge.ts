/**
 * Federation portal iframe bridge (realm frontend side).
 */
import { DelegationIdentity, DelegationChain, Ed25519KeyIdentity } from '@dfinity/identity';

const BRIDGE_VERSION = '1';
const PORTAL_SESSION_KEY = 'realms:portal-embed';
let port = null;
let portalConfig = null;
let pendingDelegationRequest = false;
/** @type {{ path: string, replace: boolean } | null} */
let pendingNavPush = null;
/** @type {{ source: string, uri: string, label?: string } | null | undefined} */
let pendingFocusPush = undefined;
/** @type {boolean} */
let pendingAssistantOpen = false;
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
    case 'auth:pending':
      // Host has no session yet; it is showing its own sign-in UI. Not fatal —
      // the delegation will arrive after the user signs in on the portal.
      window.dispatchEvent(
        new CustomEvent('portal:auth-pending', { detail: { error: msg.error || '' } })
      );
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

function requestDelegation(interactive = false) {
  if (!port) {
    pendingDelegationRequest = true;
    return;
  }
  pendingDelegationRequest = false;
  const session = ensureSessionIdentity();
  post({
    type: 'auth:request-delegation',
    payload: {
      sessionPublicKeyDer: Array.from(new Uint8Array(session.getPublicKey().toDer())),
      // Silent probes (bridge init) must not make the host pop its sign-in
      // overlay — only user-initiated logins should.
      interactive
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
    port?.close?.();
    port = event.ports[0];
    port.onmessage = onPortMessage;
    post({ type: 'bridge:ready', payload: { version: BRIDGE_VERSION } });
    requestDelegation(false); // silent probe: reuse an existing host session if any
    // Flush any navigation that fired before the MessagePort was ready
    // (common: afterNavigate during hydration races the handshake).
    if (pendingNavPush) {
      const queued = pendingNavPush;
      pendingNavPush = null;
      post({
        type: 'nav:push',
        payload: { path: queued.path, replace: queued.replace }
      });
    }
    if (pendingFocusPush !== undefined) {
      const queuedFocus = pendingFocusPush;
      pendingFocusPush = undefined;
      post({ type: 'focus:push', payload: queuedFocus });
    }
    if (pendingAssistantOpen) {
      pendingAssistantOpen = false;
      post({ type: 'assistant:open' });
    }
  };

  window.addEventListener('message', onWindowMessage);

  // The host sends bridge:init on our document's load event, which fires long
  // before this listener exists (we attach during late hydration) — that first
  // message and its transferred port are lost. Announce ourselves so the host
  // re-handshakes with a fresh channel; retry until a port arrives.
  const sayHello = () => {
    try {
      window.parent?.postMessage({ type: 'bridge:hello', version: BRIDGE_VERSION }, '*');
    } catch {
      // parent may be inaccessible outside a real embed
    }
  };
  let helloAttempts = 0;
  const helloTimer = setInterval(() => {
    if (port || ++helloAttempts > 40) {
      clearInterval(helloTimer);
      return;
    }
    sayHello();
  }, 250);
  sayHello();

  return () => {
    clearInterval(helloTimer);
    window.removeEventListener('message', onWindowMessage);
    port = null;
  };
}

/**
 * Mirror an in-realm path onto the portal address bar (`/r/<slug><path>`).
 * @param {string} path
 * @param {{ replace?: boolean }} [opts]  replace=true uses history.replaceState
 *   (auth redirects / initial sync); default pushState for real navigations.
 */
export function portalNavPush(path, { replace = false } = {}) {
  if (!isPortalEmbedded()) return false;
  const normalized = path.startsWith('/') ? path : `/${path || ''}`;
  if (!port) {
    // Handshake not ready yet — remember the latest path and flush on connect.
    pendingNavPush = { path: normalized, replace: !!replace };
    return false;
  }
  pendingNavPush = null;
  post({ type: 'nav:push', payload: { path: normalized, replace: !!replace } });
  return true;
}

/**
 * Mirror document focus onto the portal host so RegistryAssistant can include it.
 * @param {{ source: string, uri: string, label?: string } | null} focus
 */
export function portalFocusPush(focus) {
  if (!isPortalEmbedded()) return false;
  if (!port) {
    pendingFocusPush = focus;
    return false;
  }
  pendingFocusPush = undefined;
  post({ type: 'focus:push', payload: focus });
  return true;
}

/**
 * Ask the portal host to open the mundus-level RegistryAssistant.
 * Fire-and-forget; queues briefly if the MessagePort is not ready yet.
 */
export function portalAssistantOpen() {
  if (!isPortalEmbedded()) return false;
  if (!port) {
    pendingAssistantOpen = true;
    return false;
  }
  pendingAssistantOpen = false;
  post({ type: 'assistant:open' });
  return true;
}

export function reportResize(height) {
  if (!port) return;
  post({ type: 'resize:report', payload: { height } });
}

export function requestAuthRefresh() {
  // User-initiated (login click / session restore after user action): the
  // host may respond by showing its sign-in overlay.
  requestDelegation(true);
}

/**
 * Wait for the portal host to deliver a scoped II delegation.
 *
 * `portal:auth-pending` (host has no session yet and is showing its own
 * sign-in UI) does NOT settle the promise — the user may take minutes to
 * complete the II flow on the portal origin, so we keep listening until a
 * delegation arrives, a hard `portal:auth-error` fires, or the timeout hits.
 * @param {{ timeoutMs?: number }} [opts]
 * @returns {Promise<DelegationIdentity | null>}
 */
export function waitForPortalDelegation({ timeoutMs = 300_000 } = {}) {
  const existing = getPortalDelegationIdentity();
  if (existing) return Promise.resolve(existing);

  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      window.removeEventListener('portal:auth', onAuth);
      window.removeEventListener('portal:auth-error', onAuthError);
      resolve(value);
    };

    const onAuth = () => {
      const identity = getPortalDelegationIdentity();
      if (identity) finish(identity);
    };

    const onAuthError = (event) => {
      console.warn('[portal-bridge] host auth error:', event?.detail?.error);
      finish(null);
    };

    const timer = setTimeout(() => finish(null), timeoutMs);
    window.addEventListener('portal:auth', onAuth);
    window.addEventListener('portal:auth-error', onAuthError);
    requestAuthRefresh();
  });
}
