export {
	BRIDGE_PROTOCOL_VERSION,
	BRIDGE_SOURCE,
	type BridgeErrorCode,
	type BridgeErrorPayload,
	type HostRealmInfo,
	type HostState,
	type NotifyLevel,
	type ModalAction,
	type BridgeMessage,
	type ExtToHostMessage,
	type HostToExtMessage,
	isBridgeMessage,
	bridgeProtocolMajor,
	bridgeVersionsCompatible,
} from './protocol.js';

export {
	createExtensionClient,
	type ExtensionClient,
	type ExtensionClientOptions,
	type OpenModalOptions,
} from './client.js';

export {
	createBridgeServer,
	type BridgeServer,
	type BridgeServerOptions,
} from './server.js';
