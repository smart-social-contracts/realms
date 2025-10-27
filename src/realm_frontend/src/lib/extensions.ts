/**
 * Extension system types
 * These types are used by the core frontend to work with extensions
 */

export interface ExtensionMetadata {
  id?: string;
  name: string;
  version?: string;
  description?: string;
  icon?: string;
  enabled?: boolean;
}
