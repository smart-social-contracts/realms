/** Parse host/backend failures that carry a stable ``error_code`` (issue #393). */

const TAGGED = /^\[([a-z][a-z0-9_]*)\]\s+/i;

export const ASSIGNABLE_JOIN_CODES = new Set([
	'coordinator_only',
	'quarter_not_ready',
	'quarter_full',
	'setup_not_open',
]);

export interface BackendError {
	code: string | null;
	message: string;
}

function fromObject(obj: Record<string, unknown>): BackendError | null {
	const code = obj.error_code;
	if (typeof code === 'string' && code) {
		const message =
			typeof obj.error === 'string'
				? obj.error
				: typeof obj.message === 'string'
					? obj.message
					: '';
		return { code, message };
	}
	if (typeof obj.error === 'string') {
		return parseBackendError(obj.error);
	}
	return null;
}

export function parseBackendError(raw: unknown): BackendError {
	if (raw && typeof raw === 'object') {
		const parsed = fromObject(raw as Record<string, unknown>);
		if (parsed) return parsed;
	}

	if (typeof raw !== 'string' || !raw) {
		return { code: null, message: typeof raw === 'string' ? raw : '' };
	}

	const trimmed = raw.trim();
	if (trimmed.startsWith('{')) {
		try {
			const obj = JSON.parse(trimmed) as unknown;
			if (obj && typeof obj === 'object') {
				const parsed = fromObject(obj as Record<string, unknown>);
				if (parsed) return parsed;
			}
		} catch {
			/* not JSON */
		}
	}

	const tagged = TAGGED.exec(trimmed);
	if (tagged) {
		return { code: tagged[1], message: trimmed.slice(tagged[0].length) };
	}

	return { code: null, message: trimmed };
}

export function localizeBackendError(
	raw: unknown,
	translate: (key: string) => string,
	fallbackKey = 'errors.generic',
): string {
	const { code, message } = parseBackendError(raw);
	if (code) {
		const key = `errors.${code}`;
		const localized = translate(key);
		if (localized && localized !== key) return localized;
	}
	if (message) return message;
	return translate(fallbackKey);
}

export function isAssignableJoinError(raw: unknown): boolean {
	const { code, message } = parseBackendError(raw);
	if (code && ASSIGNABLE_JOIN_CODES.has(code)) return true;
	const m = (message || '').toLowerCase();
	return (
		m.includes('coordinator-only') ||
		m.includes('coordinator only') ||
		m.includes('join through a quarter') ||
		m.includes('quarter is full') ||
		m.includes('is full') ||
		m.includes('at capacity') ||
		m.includes('no capacity') ||
		m.includes('still setting up') ||
		m.includes('still installing')
	);
}
