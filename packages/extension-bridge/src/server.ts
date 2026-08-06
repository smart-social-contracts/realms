import {
	BRIDGE_PROTOCOL_VERSION,
	BRIDGE_SOURCE,
	type BridgeErrorPayload,
	type HostState,
	type ExtToHostMessage,
	type HostToExtMessage,
	isBridgeMessage,
	bridgeVersionsCompatible,
} from './protocol.js';

export interface BridgeServerOptions {
	extensionId: string;
	/** Expected sdk_version from the extension manifest. */
	requiredSdkVersion?: string;
	/** Declared manifest capabilities — closed-world enforcement. */
	capabilities: string[];
	/** Optional entry_access.functions allowlist (fn name → role). */
	entryAccessFunctions?: Record<string, string>;
	getState: () => HostState;
	onCallExtension?: (fn: string, args: Record<string, unknown>) => Promise<unknown>;
	onNavigate?: (path: string) => void | Promise<void>;
	onNotify?: (level: 'info' | 'success' | 'error', message: string) => void;
	onOpenModal?: (payload: {
		title: string;
		body: string;
		actions: Array<{ id: string; label: string; tone?: string }>;
	}) => Promise<{ actionId: string }>;
	onResize?: (height: number) => void;
	onHandshakeComplete?: () => void;
	onHandshakeFailed?: (reason: string) => void;
}

export interface BridgeServer {
	pushState(state: HostState): void;
	destroy(): void;
}

function deny(message: string): BridgeErrorPayload {
	return { code: 'denied', message };
}

function failed(message: string): BridgeErrorPayload {
	return { code: 'failed', message };
}

export function createBridgeServer(
	iframe: HTMLIFrameElement,
	options: BridgeServerOptions,
): BridgeServer {
	const requiredSdk =
		options.requiredSdkVersion ?? BRIDGE_PROTOCOL_VERSION;
	let handshakeDone = false;
	let destroyed = false;

	function targetWindow(): Window | null {
		return iframe.contentWindow;
	}

	function post(msg: HostToExtMessage): void {
		if (destroyed) return;
		const win = targetWindow();
		if (!win) return;
		win.postMessage(msg, '*');
	}

	function replyError(id: number, error: BridgeErrorPayload): void {
		post({ source: BRIDGE_SOURCE, kind: 'error', id, error });
	}

	function hasCapability(cap: string): boolean {
		return options.capabilities.includes(cap);
	}

	function isFunctionAllowed(fn: string): boolean {
		const allowlist = options.entryAccessFunctions;
		if (!allowlist) return true;
		return Object.prototype.hasOwnProperty.call(allowlist, fn);
	}

	async function handleRequest(msg: ExtToHostMessage): Promise<void> {
		switch (msg.kind) {
			case 'hello': {
				if (handshakeDone) return;
				if (!bridgeVersionsCompatible(msg.sdkVersion, requiredSdk)) {
					const reason = `SDK version mismatch: extension requires ${msg.sdkVersion}, host supports ${BRIDGE_PROTOCOL_VERSION}`;
					post({ source: BRIDGE_SOURCE, kind: 'hello_nack', reason });
					options.onHandshakeFailed?.(reason);
					return;
				}
				const state = options.getState();
				handshakeDone = true;
				post({
					source: BRIDGE_SOURCE,
					kind: 'hello_ack',
					sdkVersion: BRIDGE_PROTOCOL_VERSION,
					extensionId: options.extensionId,
					capabilities: options.capabilities,
					state,
				});
				options.onHandshakeComplete?.();
				return;
			}

			case 'call_extension': {
				if (!handshakeDone) {
					replyError(msg.id, deny('Handshake not complete'));
					return;
				}
				if (!hasCapability('call_extension')) {
					replyError(msg.id, deny("Capability 'call_extension' not declared"));
					return;
				}
				if (!isFunctionAllowed(msg.fn)) {
					replyError(
						msg.id,
						deny(`Function '${msg.fn}' not in entry_access.functions allowlist`),
					);
					return;
				}
				if (!options.onCallExtension) {
					replyError(msg.id, { code: 'unsupported', message: 'call_extension handler not configured' });
					return;
				}
				try {
					const result = await options.onCallExtension(msg.fn, msg.args ?? {});
					post({ source: BRIDGE_SOURCE, kind: 'call_result', id: msg.id, result });
				} catch (e) {
					const message = e instanceof Error ? e.message : String(e);
					replyError(msg.id, failed(message));
				}
				return;
			}

			case 'navigate': {
				if (!handshakeDone) return;
				if (!hasCapability('navigate')) return;
				await options.onNavigate?.(msg.path);
				return;
			}

			case 'notify': {
				if (!handshakeDone) return;
				if (!hasCapability('notify')) return;
				options.onNotify?.(msg.level, msg.message);
				return;
			}

			case 'open_modal': {
				if (!handshakeDone) {
					replyError(msg.id, deny('Handshake not complete'));
					return;
				}
				if (!options.onOpenModal) {
					replyError(msg.id, { code: 'unsupported', message: 'open_modal handler not configured' });
					return;
				}
				try {
					const { actionId } = await options.onOpenModal({
						title: msg.title,
						body: msg.body,
						actions: msg.actions,
					});
					post({ source: BRIDGE_SOURCE, kind: 'modal_result', id: msg.id, actionId });
				} catch (e) {
					const message = e instanceof Error ? e.message : String(e);
					replyError(msg.id, failed(message));
				}
				return;
			}

			case 'resize': {
				if (!handshakeDone) return;
				options.onResize?.(msg.height);
				return;
			}

			case 'get_state': {
				if (!handshakeDone) {
					replyError(msg.id, deny('Handshake not complete'));
					return;
				}
				post({
					source: BRIDGE_SOURCE,
					kind: 'state',
					state: options.getState(),
				});
				return;
			}
		}
	}

	const messageHandler = (event: MessageEvent) => {
		if (destroyed) return;
		if (event.source !== iframe.contentWindow) return;
		if (!isBridgeMessage(event.data)) return;
		void handleRequest(event.data as ExtToHostMessage);
	};

	window.addEventListener('message', messageHandler);

	return {
		pushState(state: HostState): void {
			if (!handshakeDone || destroyed) return;
			post({ source: BRIDGE_SOURCE, kind: 'state', state });
		},
		destroy(): void {
			destroyed = true;
			window.removeEventListener('message', messageHandler);
		},
	};
}
