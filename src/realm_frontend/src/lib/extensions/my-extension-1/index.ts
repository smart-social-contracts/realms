// Export all components from the vault-manager extension
import MyExtension1 from './MyExtension1.svelte';

export {
    MyExtension1
}

// Extension metadata for the marketplace
export const metadata = {
    id: 'my-extension-1',
    name: 'My Extension 1',
    description: 'My Extension 1',
    version: '1.0.0',
    icon: 'wallet', // Icon name from the icon library
    author: 'Smart Social Contracts Team',
    permissions: ['read_vault', 'transfer_tokens']
};
