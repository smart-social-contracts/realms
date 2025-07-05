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
    enabled?: boolean;
    profiles?: string[];
    [key: string]: any;
}

// Registry of all available extensions
const extensionsRegistry: Record<string, ExtensionMetadata> = {};

const isDevDummyMode = typeof window !== 'undefined' && import.meta.env.DEV_DUMMY_MODE === 'true';

async function initializeExtensions() {
    if (isDevDummyMode) {
        console.log('DEV_DUMMY_MODE: Loading safe extensions without backend dependencies');
        
        const safeExtensionImports = [
            { id: 'vault_manager', path: './vault_manager/index.ts' },
            { id: 'public_dashboard', path: './public_dashboard/index.ts' },
            { id: 'metrics', path: './metrics/index.ts' },
            { id: 'notifications', path: './notifications/index.ts' }
        ];
        
        await Promise.all(safeExtensionImports.map(async ({ id, path }) => {
            try {
                const module = await import(path);
                if (module.metadata && module.default) {
                    extensionsRegistry[id] = {
                        ...module.metadata,
                        id,
                        component: module.default as ComponentType,
                        enabled: true
                    } as ExtensionMetadata;
                    console.log(`Registered safe extension: ${id}`);
                } else {
                    console.warn(`Failed to register extension ${id}: missing metadata or component`);
                }
            } catch (error) {
                console.warn(`Failed to load safe extension ${id}:`, error);
            }
        }));
    } else {
        console.log('Normal mode: Loading extensions with manual imports');
        
        const extensionImports = [
            { id: 'vault_manager', path: './vault_manager/index.ts' },
            { id: 'llm_chat', path: './llm_chat/index.ts' },
            { id: 'citizen_dashboard', path: './citizen_dashboard/index.ts' },
            { id: 'public_dashboard', path: './public_dashboard/index.ts' },
            { id: 'land_registry', path: './land_registry/index.ts' },
            { id: 'justice_litigation', path: './justice_litigation/index.ts' },
            { id: 'metrics', path: './metrics/index.ts' },
            { id: 'notifications', path: './notifications/index.ts' }
        ];
        
        await Promise.all(extensionImports.map(async ({ id, path }) => {
            try {
                const module = await import(path);
                if (module.metadata && module.default) {
                    extensionsRegistry[id] = {
                        ...module.metadata,
                        id,
                        component: module.default as ComponentType,
                        enabled: true
                    } as ExtensionMetadata;
                    console.log(`Registered extension: ${id}`);
                } else {
                    console.warn(`Failed to register extension ${id}: missing metadata or component`);
                }
            } catch (error) {
                console.warn(`Failed to load extension ${id}:`, error);
            }
        }));
    }
}

initializeExtensions().catch(error => {
    console.error('Failed to initialize extensions:', error);
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
