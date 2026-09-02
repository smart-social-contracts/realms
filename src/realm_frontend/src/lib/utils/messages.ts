/** Member inbox (ME → Messages): official notices, not chat. */

export const MEMBER_INBOX_HREF = '/messages';
export const MEMBER_INBOX_EXTENSION_ID = 'notifications';

export type NoticeAudience = 'user' | 'department' | 'realm' | string;

export interface NoticeItem {
	id: string;
	title: string;
	message: string;
	timestamp_ms: number;
	read: boolean;
	sender?: string;
	sender_name?: string;
	audience_type?: NoticeAudience;
	department?: string;
	href?: string;
	icon?: string;
	color?: string;
}

const PLACEHOLDER_HREFS = new Set([
	'',
	'/',
	'#',
	'/notifications',
	'/extensions/notifications',
	MEMBER_INBOX_HREF,
]);

export function isMemberInboxExtension(id: string | undefined | null): boolean {
	return id === MEMBER_INBOX_EXTENSION_ID;
}

function normalizeHref(href: string): string {
	const trimmed = href.trim();
	if (!trimmed) return '';
	const path = trimmed.split(/[?#]/)[0].replace(/\/$/, '');
	return path || '/';
}

/** True when the notice points at a real destination, not this inbox. */
export function isActionHref(href: string | undefined | null): boolean {
	if (!href) return false;
	const path = normalizeHref(href);
	return Boolean(path) && !PLACEHOLDER_HREFS.has(path);
}

export function formatSender(notice: Pick<NoticeItem, 'sender' | 'sender_name'>): string {
	const name = (notice.sender_name || '').trim();
	if (name) return name;
	const sender = (notice.sender || '').trim();
	if (!sender) return 'Realm';
	if (sender.includes('-') && sender.length > 20) {
		return `${sender.slice(0, 8)}…${sender.slice(-6)}`;
	}
	return sender;
}

export function formatAudience(
	notice: Pick<NoticeItem, 'audience_type' | 'department'>,
): string {
	const audience = notice.audience_type || 'user';
	if (audience === 'department') {
		return notice.department?.trim() || 'a department';
	}
	if (audience === 'realm') return 'everyone in this realm';
	return 'you';
}

export function formatNoticeMeta(notice: NoticeItem): string {
	return `From ${formatSender(notice)} · To ${formatAudience(notice)}`;
}

export function actionLabel(href: string): string {
	const path = normalizeHref(href);
	const last = path.split('/').filter(Boolean).pop() || '';
	if (!last) return 'Open';
	return `Open ${last.replace(/_/g, ' ')}`;
}

export function formatRelativeTime(ts: number, now = Date.now()): string {
	if (!ts) return '';
	const diffMs = now - ts;
	if (diffMs < 0) return 'just now';
	const seconds = Math.floor(diffMs / 1000);
	if (seconds < 60) return 'just now';
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	if (days === 1) return 'Yesterday';
	if (days < 30) return `${days}d ago`;
	const months = Math.floor(days / 30);
	if (months < 12) return `${months}mo ago`;
	return `${Math.floor(months / 12)}y ago`;
}

export function formatFullDate(ts: number): string {
	if (!ts) return '';
	const d = new Date(ts);
	if (Number.isNaN(d.getTime())) return '';
	return d.toLocaleString(undefined, {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	});
}
