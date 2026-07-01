import { CONFIG } from '$lib/config.js';

/** IC asset canister URL for a realm frontend (iframe src). */
export function realmFrontendOrigin(frontendCanisterId, network = CONFIG.deploy_queue_network) {
	const id = (frontendCanisterId || '').trim();
	if (!id) return '';
	if (typeof window !== 'undefined') {
		const host = window.location.hostname;
		if (host.includes('localhost') || host.includes('127.0.0.1')) {
			const port = window.location.port || '4943';
			return `http://${id}.localhost:${port}`;
		}
	}
	if (network === 'local') {
		return `http://${id}.localhost:4943`;
	}
	return `https://${id}.icp0.io`;
}

export function realmIframeUrl(frontendCanisterId, slug, subPath = '') {
	const base = realmFrontendOrigin(frontendCanisterId);
	if (!base) return '';
	const path = subPath.startsWith('/') ? subPath : subPath ? `/${subPath}` : '';
	const q = new URLSearchParams({ portal: '1', slug: slug || '' });
	return `${base}${path}?${q.toString()}`;
}

export function portalPath(slug, subPath = '') {
	const p = subPath.startsWith('/') ? subPath : subPath ? `/${subPath}` : '';
	return `/r/${encodeURIComponent(slug)}${p}`;
}
