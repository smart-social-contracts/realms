export type SetupLifecycleStatus = 'setup' | 'alpha' | string;

export interface SetupCodexSelection {
	package: string;
	version: string;
}

export interface SetupState {
	status: SetupLifecycleStatus;
	creator: string;
	is_caller_authorized: boolean;
	codex: SetupCodexSelection | null;
	token: Record<string, unknown> | null;
	branding: Record<string, unknown> | null;
}

export interface AvailableCodex {
	id: string;
	versions: string[];
	name?: string;
	description?: string;
}

export interface SetupActionResult {
	success: boolean;
	error?: string;
	resolved_version?: string;
}

export interface SetupBackendActor {
	get_setup_state: () => Promise<string>;
	list_available_codices: () => Promise<string>;
	setup_install_codex: (json: string) => Promise<string>;
	setup_configure_token: (json: string) => Promise<string>;
	setup_set_branding: (json: string) => Promise<string>;
	complete_setup: () => Promise<string>;
	get_runtime_flags?: () => Promise<string>;
}
