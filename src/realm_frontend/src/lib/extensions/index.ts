import type { ComponentType } from 'svelte';
import { getIcon } from '$lib/utils/iconMap';

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
    enabled?: boolean;  // New field to control visibility
}

// Type for dynamically imported modules
interface ExtensionModule {
    default: ComponentType;
    metadata: Omit<ExtensionMetadata, 'id' | 'component' | 'enabled'>;
}

// Auto-discover extensions from the filesystem
// This runs at build time with Vite, compatible with IC deployment
const extensionModules = import.meta.glob<ExtensionModule>('./*/index.ts', { eager: true });

// Registry of all available extensions
const extensionsRegistry: Record<string, ExtensionMetadata> = {};

// Process discovered extensions
Object.entries(extensionModules).forEach(([path, module]) => {
    // Extract the extension ID from the path (e.g., './my_extension/index.ts' -> 'my_extension')
    const id = path.split('/')[1];
    
    // Add to registry with module metadata and component
    if (module.metadata && module.default) {
        extensionsRegistry[id] = {
            ...module.metadata,
            id,
            component: module.default,
            enabled: true // Default to enabled
        };
        console.log(`Registered extension: ${id}`);
    } else {
        console.warn(`Failed to register extension at ${path}: missing metadata or component`);
    }
});

// Function to get all registered extensions
export function getAllExtensions(): ExtensionMetadata[] {
    return Object.values(extensionsRegistry).filter(ext => ext.enabled);
}

// Function to get a specific extension by ID
export function getExtension(id: string): ExtensionMetadata | undefined {
    return extensionsRegistry[id];
}

// Function to toggle extension visibility
export function toggleExtension(id: string, enabled: boolean): void {
    if (extensionsRegistry[id]) {
        extensionsRegistry[id].enabled = enabled;
    }
}

// Get an extension icon component
export function getExtensionIcon(extension: ExtensionMetadata): any {
    return getIcon(extension.icon);
}
