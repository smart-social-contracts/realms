export const ERROR_CODE_PERMISSION_DENIED = 'permission_denied';
export const DEFAULT_PERMISSION_MESSAGE = "You don't have permission to view this.";

export interface AccessError {
  isAccessDenied: boolean;
  operation: string;
  message: string;
}

export class AccessDeniedError extends Error {
  operation: string;
  constructor(info: AccessError) {
    super(info.message);
    this.name = 'AccessDeniedError';
    this.operation = info.operation;
  }
}

/**
 * Detects whether a backend extension_sync_call result (or a caught error)
 * represents a permission-denied response and extracts structured info.
 *
 * Canonical inner/outer JSON:
 *   {"success":false,"error_code":"permission_denied","error":"...","denied_operation":"..."}
 *
 * Legacy payloads with only ``denied_operation`` are still recognized.
 *
 * Returns null when the result is not a permission error.
 */
export function parseAccessError(
  resultOrError: unknown
): AccessError | null {
  if (!resultOrError) return null;

  if (typeof resultOrError === 'object' && resultOrError !== null) {
    const obj = resultOrError as Record<string, unknown>;
    const direct = accessErrorFromObject(obj);
    if (direct) return direct;

    if (typeof obj.response === 'string') {
      const nested = parseAccessError(obj.response);
      if (nested) return nested;
      if (
        obj.response.includes('Access denied') ||
        obj.response.includes('denied_operation')
      ) {
        return {
          isAccessDenied: true,
          operation: extractOperation(obj.response),
          message: DEFAULT_PERMISSION_MESSAGE,
        };
      }
    }
  }

  if (resultOrError instanceof Error) {
    return parseAccessError({ response: resultOrError.message });
  }

  if (typeof resultOrError === 'string') {
    try {
      const parsed = JSON.parse(resultOrError);
      const fromJson = parseAccessError(parsed);
      if (fromJson) return fromJson;
    } catch {
      if (
        resultOrError.includes('Access denied') &&
        resultOrError.includes('denied_operation')
      ) {
        return {
          isAccessDenied: true,
          operation: extractOperation(resultOrError),
          message: DEFAULT_PERMISSION_MESSAGE,
        };
      }
    }
  }

  return null;
}

function accessErrorFromObject(obj: Record<string, unknown>): AccessError | null {
  const deniedOp = obj.denied_operation;
  if (obj.error_code === ERROR_CODE_PERMISSION_DENIED || deniedOp) {
    const raw = String(obj.error || '');
    return {
      isAccessDenied: true,
      operation: deniedOp ? String(deniedOp) : extractOperation(raw),
      message: DEFAULT_PERMISSION_MESSAGE,
    };
  }
  return null;
}

function extractOperation(text: string): string {
  const match = text.match(/permission '([^']+)'/);
  return match?.[1] || '';
}

/**
 * Detects whether an error is an expired IC delegation (HTTP 400 from replica).
 * Returns a user-friendly message if so, null otherwise.
 */
export function formatDelegationExpiredError(error: unknown): string | null {
  if (!error) return null;
  const msg = error instanceof Error ? error.message : String(error);
  if (
    msg.includes('Invalid delegation expiry') ||
    msg.includes('delegation has expired') ||
    msg.includes('Specified sender delegation has expired')
  ) {
    return 'Your session expired. Please refresh the page to continue.';
  }
  return null;
}
