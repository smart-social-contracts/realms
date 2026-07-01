import { createScopedDelegation } from '$lib/delegation.js';
import { getIdentity } from '$lib/auth.js';
import { portalPath } from '$lib/federation.js';

const BRIDGE_VERSION = '1';

/**
 * Host-side portal bridge: MessageChannel handshake + scoped delegation to iframe.
 * @param {HTMLIFrameElement} iframe
 * @param {{ slug: string, backendCanisterId: string, frontendCanisterId: string, env?: string }} realm
 */
export function attachPortalBridge(iframe, realm) {
	const channel = new MessageChannel();
	let port = channel.port1;
	let disposed = false;
	/** @type {Uint8Array | null} */
	let lastSessionKeyDer = null;

	const dispose = () => {
		if (disposed) return;
		disposed = true;
		port.onmessage = null;
		port.close?.();
	};

	port.onmessage = async (event) => {
		const msg = event.data;
		if (!msg || typeof msg.type !== 'string') return;

		switch (msg.type) {
			case 'bridge:ready':
				await sendDelegation(lastSessionKeyDer);
				break;
			case 'auth:request-delegation':
				lastSessionKeyDer = msg.payload?.sessionPublicKeyDer?.length
					? new Uint8Array(msg.payload.sessionPublicKeyDer)
					: null;
				await sendDelegation(lastSessionKeyDer);
				break;
			case 'nav:push': {
				const path = msg.payload?.path || '/';
				const full = portalPath(realm.slug, path);
				window.history.pushState({}, '', full);
				break;
			}
			case 'nav:external': {
				const url = msg.payload?.url;
				if (url && /^https?:\/\//.test(url)) {
					window.open(url, '_blank', 'noopener,noreferrer');
				}
				break;
			}
			case 'resize:report':
				if (typeof msg.payload?.height === 'number' && iframe) {
					iframe.style.height = `${Math.min(Math.max(msg.payload.height, 320), 4000)}px`;
				}
				break;
			default:
				break;
		}
	};

	async function sendDelegation(sessionPublicKeyDer) {
		try {
			if (!sessionPublicKeyDer?.length) return;
			const identity = await getIdentity();
			if (!identity) {
				post({
					type: 'auth:error',
					error: 'Portal session required — sign in at /join first'
				});
				return;
			}
			const scoped = await createScopedDelegation(
				identity,
				realm.backendCanisterId,
				sessionPublicKeyDer
			);
			post({
				type: 'auth:delegation',
				payload: {
					delegation: scoped.delegationChain,
					backendCanisterId: realm.backendCanisterId,
					expiresAt: scoped.expiresAt
				}
			});
		} catch (e) {
			console.error('[portal-bridge] delegation failed:', e);
			post({ type: 'auth:error', error: String(e?.message || e) });
		}
	}

	function post(msg) {
		if (disposed) return;
		port.postMessage({ ...msg, id: msg.id });
	}

	function handshake() {
		if (disposed || !iframe?.contentWindow) return;
		post({
			type: 'config:realm',
			payload: {
				slug: realm.slug,
				backendCanisterId: realm.backendCanisterId,
				frontendCanisterId: realm.frontendCanisterId,
				env: realm.env || ''
			}
		});
		iframe.contentWindow.postMessage(
			{ type: 'bridge:init', port: channel.port2, version: BRIDGE_VERSION },
			'*',
			[channel.port2]
		);
	}

	iframe.addEventListener('load', handshake);
	// Parent usually calls attachPortalBridge from a load handler — run handshake now too.
	queueMicrotask(handshake);

	return {
		dispose,
		syncPath(path) {
			post({ type: 'nav:sync', payload: { path } });
		},
		logout() {
			post({ type: 'auth:logout', payload: {} });
		}
	};
}
