import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
	EMPTY_MEMBERSHIP,
	GUEST_PROFILE_LABEL,
	formatDepartmentValues,
	formatProfileValues,
	titleCaseProfile,
} from './membershipLabels';

describe('titleCaseProfile', () => {
	it('title-cases Cedar profile ids', () => {
		expect(titleCaseProfile('admin')).toBe('Admin');
		expect(titleCaseProfile('member')).toBe('Member');
		expect(titleCaseProfile('court_judge')).toBe('Court Judge');
	});
});

describe('formatProfileValues', () => {
	it('uses Guest when unauthenticated or no profiles', () => {
		expect(formatProfileValues(null)).toBe(GUEST_PROFILE_LABEL);
		expect(formatProfileValues([])).toBe('Guest');
	});

	it('joins several profiles on one row', () => {
		expect(formatProfileValues(['member', 'judge'])).toBe('Member, Judge');
	});
});

describe('formatDepartmentValues', () => {
	it('keeps an em dash so the Dept row stays visible when empty', () => {
		expect(formatDepartmentValues(null)).toBe(EMPTY_MEMBERSHIP);
		expect(formatDepartmentValues([])).toBe('—');
	});

	it('does not title-case department names', () => {
		expect(formatDepartmentValues(['root', 'justice'])).toBe('root, justice');
	});
});

describe('AuthButton host chrome', () => {
	it('renders two icon rows for profiles and departments', () => {
		const source = readFileSync(
			join(dirname(fileURLToPath(import.meta.url)), '../components/AuthButton.svelte'),
			'utf8'
		);
		expect(source).toContain('formatProfileValues');
		expect(source).toContain('formatDepartmentValues');
		expect(source).toContain('IconUser');
		expect(source).toContain('IconBuilding');
		expect(source).toContain('userDepartments');
		expect(source).not.toMatch(/userTypeLabel/);
	});
});
