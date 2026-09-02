import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
	actionLabel,
	formatAudience,
	formatFullDate,
	formatNoticeMeta,
	formatRelativeTime,
	formatSender,
	isActionHref,
	isMemberInboxExtension,
	MEMBER_INBOX_EXTENSION_ID,
	MEMBER_INBOX_HREF,
	type NoticeItem,
} from './messages';

const notice = (overrides: Partial<NoticeItem> = {}): NoticeItem => ({
	id: '1',
	title: 'Hello',
	message: 'Body',
	timestamp_ms: 1,
	read: false,
	...overrides,
});

describe('member inbox identity', () => {
	it('treats the notifications extension as the same inbox', () => {
		expect(MEMBER_INBOX_HREF).toBe('/messages');
		expect(MEMBER_INBOX_EXTENSION_ID).toBe('notifications');
		expect(isMemberInboxExtension('notifications')).toBe(true);
		expect(isMemberInboxExtension('department_docs')).toBe(false);
	});
});

describe('isActionHref', () => {
	it('rejects empty and inbox placeholders', () => {
		expect(isActionHref(undefined)).toBe(false);
		expect(isActionHref('')).toBe(false);
		expect(isActionHref('/notifications')).toBe(false);
		expect(isActionHref('/notifications/')).toBe(false);
		expect(isActionHref('/extensions/notifications')).toBe(false);
		expect(isActionHref('/messages')).toBe(false);
		expect(isActionHref('#')).toBe(false);
	});

	it('accepts real destinations', () => {
		expect(isActionHref('/extensions/department_docs')).toBe(true);
		expect(isActionHref('/settings')).toBe(true);
		expect(isActionHref('/join?invite=x')).toBe(true);
	});
});

describe('formatSender / formatAudience', () => {
	it('prefers nickname, then principal, then Realm', () => {
		expect(formatSender(notice({ sender_name: 'Marina', sender: 'abc' }))).toBe('Marina');
		expect(formatSender(notice({ sender: 'admin' }))).toBe('admin');
		expect(formatSender(notice({ sender: '' }))).toBe('Realm');
		expect(
			formatSender(notice({ sender: '2eqns-rmzes-7npxw-dxpw2-qdy2s-mw6ix-svdo2-oya7o-a6ldc-sqgwh-bqe' })),
		).toBe('2eqns-rm…wh-bqe');
	});

	it('labels audience as you / department / realm', () => {
		expect(formatAudience(notice({ audience_type: 'user' }))).toBe('you');
		expect(formatAudience(notice({ audience_type: 'department', department: 'root' }))).toBe('root');
		expect(formatAudience(notice({ audience_type: 'department' }))).toBe('a department');
		expect(formatAudience(notice({ audience_type: 'realm' }))).toBe('everyone in this realm');
	});

	it('builds a From / To line', () => {
		expect(
			formatNoticeMeta(
				notice({
					sender_name: 'InitArgDemo',
					audience_type: 'realm',
				}),
			),
		).toBe('From InitArgDemo · To everyone in this realm');
	});
});

describe('actionLabel', () => {
	it('humanizes the last path segment', () => {
		expect(actionLabel('/extensions/department_docs')).toBe('Open department docs');
		expect(actionLabel('/settings')).toBe('Open settings');
	});
});

describe('time formatting', () => {
	const now = Date.parse('2026-09-02T12:00:00Z');

	it('uses relative labels', () => {
		expect(formatRelativeTime(now - 30_000, now)).toBe('just now');
		expect(formatRelativeTime(now - 5 * 60_000, now)).toBe('5m ago');
		expect(formatRelativeTime(now - 3 * 3600_000, now)).toBe('3h ago');
		expect(formatRelativeTime(now - 24 * 3600_000, now)).toBe('Yesterday');
		expect(formatRelativeTime(now - 10 * 24 * 3600_000, now)).toBe('10d ago');
		expect(formatRelativeTime(0, now)).toBe('');
	});

	it('formats a full date when a timestamp exists', () => {
		expect(formatFullDate(0)).toBe('');
		expect(formatFullDate(Date.parse('2026-03-15T10:00:00Z'))).toMatch(/2026/);
	});
});

describe('Messages page is the member inbox', () => {
	it('opens notices, does not claim legal standing, and does not compose', () => {
		const page = readFileSync(
			resolve(dirname(fileURLToPath(import.meta.url)), '../../routes/(sidebar)/messages/+page.svelte'),
			'utf8',
		);
		expect(page).toContain('Notices addressed to you');
		expect(page).not.toContain('legal standing');
		expect(page).toContain('handleOpen');
		expect(page).toContain('Mark all read');
		expect(page).toContain('formatNoticeMeta');
		expect(page).toContain('isActionHref');
		expect(page).not.toContain('Compose');
		expect(page).not.toContain('handleMarkAsRead(message.id, !message.read)');
	});
});
