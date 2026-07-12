/**
 * Generic host bridge for runtime extensions.
 *
 * Extensions publish document focus; the host routes actions (open assistant,
 * clipboard, etc.) without codex- or extension-specific types.
 */
import { get, writable, type Readable } from 'svelte/store';

export interface DocumentFocusSnapshot {
	languageId: string;
	range: { startLine: number; endLine: number };
	text: string;
}

export interface DocumentFocus {
	/** Extension id that published this focus. */
	source: string;
	/** Opaque, extension-owned deep link for sharing / server resolution. */
	uri: string;
	/** Human-readable label, e.g. "tax_collection, lines 9–31". */
	label?: string;
	/** Optional snapshot so consumers need not call back to the publisher. */
	snapshot?: DocumentFocusSnapshot;
}

export type HostAction =
	| { type: 'assistant.open' }
	| { type: 'assistant.prompt'; message?: string; autoSend?: boolean }
	| { type: 'clipboard.write'; text: string };

export interface PendingPrompt {
	message: string;
	autoSend: boolean;
	id: number;
}

export interface HostActionEvent {
	action: HostAction;
	id: number;
}

const focusStore = writable<DocumentFocus | null>(null);
const pendingPromptStore = writable<PendingPrompt | null>(null);
const actionEventStore = writable<HostActionEvent | null>(null);

let promptSeq = 0;
let actionSeq = 0;

export const documentFocus: Readable<DocumentFocus | null> = {
	subscribe: focusStore.subscribe,
};

export const pendingAssistantPrompt: Readable<PendingPrompt | null> = {
	subscribe: pendingPromptStore.subscribe,
};

export const hostActionEvents: Readable<HostActionEvent | null> = {
	subscribe: actionEventStore.subscribe,
};

export function setDocumentFocus(focus: DocumentFocus | null): void {
	focusStore.set(focus);
}

function emitAction(action: HostAction): void {
	actionEventStore.set({ action, id: ++actionSeq });
}

export function buildPromptFromFocus(focus: DocumentFocus | null): string | null {
	if (!focus) return null;

	const snap = focus.snapshot;
	if (snap?.text?.trim()) {
		const lines =
			snap.range.startLine === snap.range.endLine
				? `line ${snap.range.startLine}`
				: `lines ${snap.range.startLine}-${snap.range.endLine}`;
		const label = focus.label ?? focus.uri;
		return (
			`Explain the following ${snap.languageId} code (${label}, ${lines}):\n\n` +
			'```' +
			snap.languageId +
			'\n' +
			snap.text +
			'\n```'
		);
	}

	const label = focus.label ?? focus.uri;
	return label ? `Please explain: ${label}` : null;
}

function copyTextWithFallback(text: string): void {
	const execCopy = (): boolean => {
		try {
			const ta = document.createElement('textarea');
			ta.value = text;
			ta.setAttribute('readonly', '');
			ta.style.position = 'fixed';
			ta.style.left = '-9999px';
			document.body.appendChild(ta);
			ta.select();
			const ok = document.execCommand('copy');
			document.body.removeChild(ta);
			return ok;
		} catch {
			return false;
		}
	};

	if (execCopy()) return;
	void navigator.clipboard?.writeText(text).catch(() => {});
}

export function dispatchHostAction(action: HostAction): void {
	if (action.type === 'clipboard.write') {
		copyTextWithFallback(action.text);
		return;
	}

	if (action.type === 'assistant.prompt') {
		const message = action.message ?? buildPromptFromFocus(get(focusStore));
		if (message) {
			pendingPromptStore.set({
				message,
				autoSend: action.autoSend ?? false,
				id: ++promptSeq,
			});
		}
		emitAction({ type: 'assistant.open' });
		return;
	}

	emitAction(action);
}

export function createHostContext(): {
	host: {
		focus: Readable<DocumentFocus | null>;
		setFocus: typeof setDocumentFocus;
		dispatch: typeof dispatchHostAction;
		pendingPrompt: Readable<PendingPrompt | null>;
	};
} {
	return {
		host: {
			focus: documentFocus,
			setFocus: setDocumentFocus,
			dispatch: dispatchHostAction,
			pendingPrompt: pendingAssistantPrompt,
		},
	};
}
