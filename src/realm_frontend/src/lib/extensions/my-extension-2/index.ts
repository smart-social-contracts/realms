// Export the component as default for dynamic loading
import MyExtension2Component from './MyExtension2.svelte';
export default MyExtension2Component;

// Extension metadata for the marketplace
export const metadata = {
    name: 'My Extension 2',
    description: 'My Extension 2',
    version: '1.0.0',
    icon: 'wallet', // Icon name from the icon library
    author: 'Smart Social Contracts Team',
    permissions: ['read_vault', 'transfer_tokens']
};
