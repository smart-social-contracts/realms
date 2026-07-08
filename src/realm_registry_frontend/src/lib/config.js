const viteEnv = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {};

const PORTAL_HOSTS = {
	staging: 'https://staging.realmsgos.org',
	demo: 'https://demo.realmsgos.org',
	test: 'https://test.realmsgos.org',
	ic: 'https://registry.realmsgos.org',
	production: 'https://registry.realmsgos.org'
};

const network = viteEnv.VITE_DEPLOY_QUEUE_NETWORK || 'staging';

export const CONFIG = {
	internet_identity_url: viteEnv.VITE_INTERNET_IDENTITY_URL || 'https://identity.ic0.app/',
	/** Federation portal: login on this origin only — no derivationOrigin pinning. */
	federation_portal: viteEnv.VITE_FEDERATION_PORTAL !== 'false',
	ii_derivation_origin:
		viteEnv.VITE_II_DERIVATION_ORIGIN ||
		(viteEnv.VITE_FEDERATION_PORTAL === 'false' ? PORTAL_HOSTS[network] || '' : ''),
	portal_base_url: viteEnv.VITE_PORTAL_BASE_URL || PORTAL_HOSTS[network] || PORTAL_HOSTS.staging,
	portal_hosts: PORTAL_HOSTS,
	deploy_queue_network: network,
	billing_service_url: viteEnv.VITE_BILLING_SERVICE_URL || 'https://billing.realmsgos.dev',
	realm_installer_canister_id:
		viteEnv.VITE_REALM_INSTALLER_CANISTER_ID || viteEnv.CANISTER_ID_REALM_INSTALLER || '',
	default_deploy_queue_network: network,
	deploy_release_tag: viteEnv.VITE_DEPLOY_RELEASE_TAG || 'v0.4.0',
	default_deploy_version: viteEnv.VITE_DEFAULT_DEPLOY_VERSION || 'main',
	casals_section: viteEnv.VITE_CASALS_SECTION || 'Deployments',
	deploy_release_checksums: {
		'realm_backend.wasm.gz':
			viteEnv.VITE_DEPLOY_RELEASE_BACKEND_CHECKSUM ||
			'c9c38a714762fe56e53534c488e645351deb7905020001b408f054c034b5c408',
		'realm_frontend.tar.gz':
			viteEnv.VITE_DEPLOY_RELEASE_FRONTEND_CHECKSUM ||
			'58cf46349679f137c9e481aa7831d367ee14f0f6aba78de9b76a2385d5031406'
	},
	deploy_service_url: viteEnv.VITE_DEPLOY_SERVICE_URL || 'https://deploy.realmsgos.dev',
	file_registry_canister_id:
		viteEnv.VITE_FILE_REGISTRY_CANISTER_ID || viteEnv.CANISTER_ID_FILE_REGISTRY || '',
	marketplace_canister_id:
		viteEnv.VITE_MARKETPLACE_CANISTER_ID || viteEnv.CANISTER_ID_MARKETPLACE_BACKEND || ''
};

function _readFlag(envKey, urlParam) {
	if (viteEnv[envKey] === 'true') return true;
	if (typeof window !== 'undefined') {
		const params = new URLSearchParams(window.location.search);
		if (params.get(urlParam) === '1') {
			sessionStorage.setItem(urlParam, '1');
			return true;
		}
		if (sessionStorage.getItem(urlParam) === '1') return true;
	}
	return false;
}

const TEST_MODE = _readFlag('VITE_TEST_MODE', 'testmode');

function _testFlag(envKey, urlParam) {
	if (!TEST_MODE) return false;
	return _readFlag(envKey, urlParam);
}

export const TEST_MODE_II_BYPASS = _testFlag('VITE_TEST_MODE_II_BYPASS', 'ii_bypass');
