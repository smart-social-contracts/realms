import { describe, expect, it } from 'vitest';
import {
  DEFAULT_PERMISSION_MESSAGE,
  parseAccessError,
} from './errors';

describe('parseAccessError', () => {
  it('recognizes error_code permission_denied without denied_operation', () => {
    const denied = parseAccessError({
      success: false,
      error_code: 'permission_denied',
      error: 'User xyz not found',
    });
    expect(denied).toEqual({
      isAccessDenied: true,
      operation: '',
      message: DEFAULT_PERMISSION_MESSAGE,
    });
  });

  it('recognizes error_code plus denied_operation on inner JSON', () => {
    const denied = parseAccessError({
      success: false,
      error_code: 'permission_denied',
      error: "Access denied: user abc lacks permission 'permission.view'",
      denied_operation: 'permission.view',
    });
    expect(denied?.operation).toBe('permission.view');
    expect(denied?.message).toBe(DEFAULT_PERMISSION_MESSAGE);
  });

  it('unwraps outer envelope response JSON', () => {
    const denied = parseAccessError({
      success: true,
      response: JSON.stringify({
        success: false,
        error_code: 'permission_denied',
        error: "Access denied: user abc lacks permission 'permission.view'",
        denied_operation: 'permission.view',
      }),
    });
    expect(denied?.operation).toBe('permission.view');
  });

  it('still recognizes legacy denied_operation-only payloads', () => {
    const denied = parseAccessError({
      error: 'Access denied',
      denied_operation: 'extension.sync_call',
    });
    expect(denied?.operation).toBe('extension.sync_call');
  });

  it('ignores ordinary validation failures', () => {
    expect(
      parseAccessError({ success: false, error: 'Department name is required' }),
    ).toBeNull();
  });
});
