import type { ComponentType } from 'svelte';

// Import all available extensions
import * as VaultManager from './vault-manager';
import * as MyExtension1 from './my-extension-1';

// Extension metadata interface
export interface ExtensionMetadata {
    id: string;
    name: string;
    description: string;
    version: string;
    icon: string;
    author: string;
    permissions: string[];
    component?: ComponentType;
}

// Registry of all available extensions
const extensionsRegistry: Record<string, ExtensionMetadata> = {
    'vault-manager': {
        ...VaultManager.metadata,
        component: VaultManager.VaultManager
    },
    'my-extension-1': {
        ...MyExtension1.metadata,
        component: MyExtension1.MyExtension1
    }
};

// Function to get all registered extensions
export function getAllExtensions(): ExtensionMetadata[] {
    return Object.values(extensionsRegistry);
}

// Function to get a specific extension by ID
export function getExtension(id: string): ExtensionMetadata | undefined {
    return extensionsRegistry[id];
}

// Export individual extensions
export { VaultManager };
export { MyExtension1 };
