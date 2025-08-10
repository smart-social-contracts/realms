// Export the component as default for dynamic loading
import TestbenchComponent from './Testbench.svelte';
export default TestbenchComponent;

// Extension metadata for the marketplace
export const metadata = {
    name: 'test_bench',
    description: 'Test bench extension',
    version: '0.1.0',
    icon: 'clipboard',
    author: 'Smart Social Contracts Team',
    permissions: ['read_vault', 'transfer_tokens'],
    profiles: ['admin']
};
