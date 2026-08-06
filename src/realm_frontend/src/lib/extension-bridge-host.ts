/**
 * Host-side bridge service for sandboxed extensions.
 *
 * Wraps createBridgeServer, wires callbacks to real host capabilities, and
 * pushes principal/locale/theme/realmInfo via injected state providers.
 */
import {
	createBridgeServer,
	BRIDGE_PROTOCOL_VERSION,
	type BridgeServer,
	type HostState,
} from '@realms/extension-bridge';
import { showBridgeToast } from '$lib/stores/bridge-toast';
import { requestBridgeModal, type BridgeModalAction } from '$lib/stores/bridge-modal';
import { parseAccessError, AccessDeniedError } from '$lib/utils/errors';

export interface SandboxManifest {
	sdk_version?: string;
	capabilities?: string[];
	entry_access?: { functions?: Record<string, string> };
}

export interface SandboxBridgeDeps {
	extensionId: string;
	manifest: SandboxManifest;
	callSync: (fn: string, args?: Record<string, unknown>) => Promise<unknown>;
	navigate: (path: string) => Promise<void>;
	getHostState: () => HostState;
	subscribeHostState: (onChange: (state: HostState) => void) => () => void;
	onHandshakeFailed?: (reason: string) => void;
	onHandshakeComplete?: () => void;
}

export class SandboxBridgeService {
	private server: BridgeServer;
	private unsubState: () => void;
	readonly ready: Promise<void>;

	constructor(iframe: HTMLIFrameElement, deps: SandboxBridgeDeps) {
		let resolveReady!: () => void;
		let rejectReady!: (err: Error) => void;
		this.ready = new Promise((resolve, reject) => {
			resolveReady = resolve;
			rejectReady = reject;
		});

		const capabilities = deps.manifest.capabilities ?? [];

		this.server = createBridgeServer(iframe, {
			extensionId: deps.extensionId,
			requiredSdkVersion: deps.manifest.sdk_version ?? BRIDGE_PROTOCOL_VERSION,
			capabilities,
			entryAccessFunctions: deps.manifest.entry_access?.functions,
			getState: deps.getHostState,
			onHandshakeComplete: () => {
				deps.onHandshakeComplete?.();
				resolveReady();
			},
			onHandshakeFailed: (reason) => {
				deps.onHandshakeFailed?.(reason);
				rejectReady(new Error(reason));
			},
			onCallExtension: async (fn, args) => {
				try {
					return await deps.callSync(fn, args);
				} catch (e) {
					if (e instanceof AccessDeniedError) throw e;
					const denied = parseAccessError(e);
					if (denied) {
						const err = new Error(denied.operation);
						(err as Error & { code: string }).code = 'denied';
						throw err;
					}
					throw e;
				}
			},
			onNavigate: (path) => deps.navigate(path),
			onNotify: (level, message) => showBridgeToast(level, message),
			onOpenModal: (payload) =>
				requestBridgeModal({
					title: payload.title,
					body: payload.body,
					actions: payload.actions.map(
						(a): BridgeModalAction => ({
							id: a.id,
							label: a.label,
							tone: a.tone as BridgeModalAction['tone'],
						}),
					),
				}),
			onResize: (height) => {
				const MIN_HEIGHT = 100;
				const MAX_HEIGHT = 4000;
				if (
					Number.isFinite(height) &&
					height >= MIN_HEIGHT &&
					height <= MAX_HEIGHT
				) {
					iframe.style.height = `${Math.ceil(height)}px`;
					iframe.style.width = '100%';
					iframe.style.border = 'none';
					iframe.style.display = 'block';
				}
			},
		});

		this.unsubState = deps.subscribeHostState((state) => {
			this.server.pushState(state);
		});
	}

	destroy(): void {
		this.unsubState();
		this.server.destroy();
	}
}
