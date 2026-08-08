import { get } from 'svelte/store';
import { backendStore, backendReady } from '$lib/canisters';
import type {
	AvailableCodex,
	SetupActionResult,
	SetupBackendActor,
	SetupState
} from './types';

function parseJson<T>(raw: unknown): T {
	if (typeof raw === 'string') return JSON.parse(raw) as T;
	return raw as T;
}

function asSetupActor(actor: unknown): SetupBackendActor {
	return actor as SetupBackendActor;
}

async function getActor(): Promise<SetupBackendActor> {
	await backendReady;
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

export async function listAvailableCodices(): Promise<AvailableCodex[]> {
	const actor = await getActor();
	const raw = await actor.list_available_codices();
	const parsed = parseJson<AvailableCodex[] | { error?: string }>(raw);
	if (!Array.isArray(parsed)) {
		throw new Error(
			typeof parsed === 'object' && parsed && 'error' in parsed
				? String(parsed.error)
				: 'Invalid codex list response'
		);
	}
	return parsed;
}

export async function installSetupCodex(payload: {
	package: string;
	version: string;
	params?: Record<string, unknown>;
}): Promise<SetupActionResult> {
	const actor = await getActor();
	return parseJson<SetupActionResult>(
		await actor.setup_install_codex(JSON.stringify(payload))
	);
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
