import { get } from 'svelte/store';
import { backendStore, backendActorReady } from '$lib/canisters';
import type {
	AvailableCodex,
	SetupActionResult,
	SetupBackendActor,
	SetupState
} from './types';

const CODEX_CATALOG_POLL_MS = 2_500;
const CODEX_CATALOG_TIMEOUT_MS = 90_000;
const CODEX_INSTALL_POLL_MS = 5_000;
const CODEX_INSTALL_TIMEOUT_MS = 20 * 60 * 1_000;

function parseJson<T>(raw: unknown): T {
	if (typeof raw === 'string') return JSON.parse(raw) as T;
	return raw as T;
}

function asSetupActor(actor: unknown): SetupBackendActor {
	return actor as SetupBackendActor;
}

async function getActor(): Promise<SetupBackendActor> {
	// SetupStageGate restores portal auth before the wizard mounts; the store
	// may already hold an authenticated actor while backendReady is still
	// waiting on realmInfo.fetch() (e.g. a slow/hung status() on mainnet).
	await backendActorReady;
	const actor = get(backendStore);
	if (!actor) throw new Error('Backend actor not initialized');
	return asSetupActor(actor);
}

async function fallbackSetupState(actor: SetupBackendActor): Promise<SetupState | null> {
	if (!actor.get_runtime_flags) return null;
	try {
		const flags = parseJson<{ success?: boolean; realm_stage?: string }>(
			await actor.get_runtime_flags()
		);
		if (!flags?.success) return null;
		return {
			status: flags.realm_stage || 'alpha',
			creator: '',
			is_caller_authorized: false,
			codex: null,
			token: null,
			branding: null
		};
	} catch {
		return null;
	}
}

export async function fetchSetupState(): Promise<SetupState> {
	const actor = await getActor();
	try {
		if (typeof actor.get_setup_state === 'function') {
			return parseJson<SetupState>(await actor.get_setup_state());
		}
	} catch (error) {
		console.warn('get_setup_state failed, trying runtime flags fallback:', error);
	}
	const fallback = await fallbackSetupState(actor);
	if (fallback) return fallback;
	throw new Error('Unable to fetch realm setup state');
}

type CodexListEnvelope = {
	success?: boolean;
	codices?: AvailableCodex[];
	error?: string;
};

function unwrapCodexList(
	parsed: AvailableCodex[] | CodexListEnvelope
): AvailableCodex[] | null {
	const list = Array.isArray(parsed) ? parsed : parsed?.codices;
	if (!Array.isArray(list) || list.length === 0) return null;
	return list;
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readCachedCodices(actor: SetupBackendActor): Promise<AvailableCodex[] | null> {
	if (typeof actor.get_available_codices_cached !== 'function') return null;
	try {
		const parsed = parseJson<AvailableCodex[] | CodexListEnvelope>(
			await actor.get_available_codices_cached()
		);
		return unwrapCodexList(parsed);
	} catch {
		return null;
	}
}

async function pollCachedCodices(
	actor: SetupBackendActor,
	timeoutMs = CODEX_CATALOG_TIMEOUT_MS,
	intervalMs = CODEX_CATALOG_POLL_MS
): Promise<AvailableCodex[]> {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		const list = await readCachedCodices(actor);
		if (list) return list;
		await sleep(intervalMs);
	}
	throw new Error('Codex catalog is still loading. Please wait a moment and try again.');
}

export async function listAvailableCodices(): Promise<AvailableCodex[]> {
	const actor = await getActor();

	const cached = await readCachedCodices(actor);
	if (cached) return cached;

	// Fire the slow refresh without awaiting — agent-js v3 sync calls may never
	// settle even though the on-chain update completes and fills the cache.
	void actor.list_available_codices().catch(() => {});

	return pollCachedCodices(actor);
}

export function isAmbiguousInstallError(error: unknown): boolean {
	const message = error instanceof Error ? error.message : String(error);
	return /returned undefined|cannot determine if the call was successful/i.test(message);
}

export async function pollUntilCodexInstalled(
	packageName: string,
	version: string,
	timeoutMs = CODEX_INSTALL_TIMEOUT_MS,
	intervalMs = CODEX_INSTALL_POLL_MS
): Promise<void> {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		const state = await fetchSetupState();
		if (state.codex?.package === packageName && state.codex?.version === version) {
			return;
		}
		await sleep(intervalMs);
	}
	throw new Error(
		`Codex installation timed out after ${Math.round(timeoutMs / 60_000)} minutes. Please refresh and check setup state.`
	);
}

export async function installSetupCodex(payload: {
	package: string;
	version: string;
	params?: Record<string, unknown>;
}): Promise<SetupActionResult> {
	const actor = await getActor();
	let resolvedVersion = payload.version;

	try {
		const raw = await actor.setup_install_codex(JSON.stringify(payload));
		const result = parseJson<SetupActionResult>(raw);
		if (!result.success) {
			return result;
		}
		if (result.resolved_version) {
			resolvedVersion = result.resolved_version;
		}
	} catch (error) {
		if (!isAmbiguousInstallError(error)) {
			throw error;
		}
	}

	await pollUntilCodexInstalled(payload.package, resolvedVersion);

	return { success: true, resolved_version: resolvedVersion };
}

export async function configureSetupToken(payload: Record<string, unknown>): Promise<SetupActionResult> {
	const actor = await getActor();
	return parseJson<SetupActionResult>(
		await actor.setup_configure_token(JSON.stringify(payload))
	);
}

export async function setSetupBranding(payload: {
	logo_data_url?: string;
	background_data_url?: string;
	colors?: { primary?: string };
}): Promise<SetupActionResult> {
	const actor = await getActor();
	return parseJson<SetupActionResult>(
		await actor.setup_set_branding(JSON.stringify(payload))
	);
}

export async function completeSetup(): Promise<SetupActionResult> {
	const actor = await getActor();
	return parseJson<SetupActionResult>(await actor.complete_setup());
}
