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
 * The backend returns permission errors in `result.response` as JSON:
 *   {"error":"Access denied: ...","denied_operation":"extension.sync_call"}
 *
 * Returns null when the result is not a permission error.
 */
export function parseAccessError(
  resultOrError: unknown
): AccessError | null {
  if (!resultOrError) return null;

  // Case 1: raw backend result object with `response` containing JSON
  if (typeof resultOrError === 'object' && resultOrError !== null) {
    const obj = resultOrError as Record<string, unknown>;

    // Direct denied_operation on result (e.g. update_realm_config pattern)
    if (obj.denied_operation) {
      return {
        isAccessDenied: true,
        operation: String(obj.denied_operation),
        message: String(obj.error || 'Access denied'),
      };
    }

    // response field containing JSON with denied_operation
    if (typeof obj.response === 'string') {
      try {
        const parsed = JSON.parse(obj.response);
        if (parsed?.denied_operation) {
          return {
            isAccessDenied: true,
            operation: String(parsed.denied_operation),
            message: String(parsed.error || 'Access denied'),
          };
        }
      } catch {
        // not JSON — check for stringified access denied pattern
        if (obj.response.includes('Access denied') || obj.response.includes('denied_operation')) {
          return {
            isAccessDenied: true,
            operation: extractOperation(obj.response),
            message: 'Access denied',
          };
        }
      }
    }
  }

  // Case 2: Error object whose message contains access denied JSON
  if (resultOrError instanceof Error) {
    return parseAccessError({ response: resultOrError.message });
  }

  // Case 3: plain string (e.g. directly assigned error text)
  if (typeof resultOrError === 'string') {
    try {
      const parsed = JSON.parse(resultOrError);
      if (parsed?.denied_operation) {
        return {
          isAccessDenied: true,
          operation: String(parsed.denied_operation),
          message: String(parsed.error || 'Access denied'),
        };
      }
    } catch {
      if (resultOrError.includes('Access denied') && resultOrError.includes('denied_operation')) {
        return {
          isAccessDenied: true,
          operation: extractOperation(resultOrError),
          message: 'Access denied',
        };
      }
    }
  }

  return null;
}

function extractOperation(text: string): string {
  const match = text.match(/permission '([^']+)'/);
  return match?.[1] || 'unknown';
}
