import { describe, expect, it } from 'vitest';
import {
	canAdvanceFromCodexStep,
	isCodexInstalled,
	reconcileCodexVersion,
	resolveSelectedCodexVersion
} from './wizardLogic';
import type { SetupState } from './types';

const installedState: SetupState = {
	status: 'setup',
	creator: 'abc',
	is_caller_authorized: true,
	codex: { package: 'agora', version: '0.9.5' },
	token: null,
	branding: null
};

describe('wizardLogic', () => {
	it('detects installed codex from setup state', () => {
		expect(isCodexInstalled(installedState)).toBe(true);
		expect(isCodexInstalled({ ...installedState, codex: null })).toBe(false);
	});

	it('allows advancing when backend has codex regardless of UI version binding', () => {
		expect(canAdvanceFromCodexStep(installedState)).toBe(true);
		expect(canAdvanceFromCodexStep(null)).toBe(false);
	});

	it('falls back to installed version when UI selection is empty', () => {
		expect(resolveSelectedCodexVersion('', installedState)).toBe('0.9.5');
		expect(resolveSelectedCodexVersion('0.9.4', installedState)).toBe('0.9.4');
	});

	it('keeps installed version when catalog list omits it', () => {
		const versions = ['0.9.6', '1.0.0'];
		expect(
			reconcileCodexVersion(versions, '', '0.9.5', (v) => v[v.length - 1] ?? '')
		).toBe('0.9.5');
	});

	it('uses latest catalog version when nothing is selected or installed', () => {
		const versions = ['0.9.4', '0.9.5'];
		expect(reconcileCodexVersion(versions, '', undefined, (v) => v[v.length - 1] ?? '')).toBe(
			'0.9.5'
		);
	});
});
