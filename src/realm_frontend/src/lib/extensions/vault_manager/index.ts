// Export the main component as default for dynamic loading
import VaultManagerComponent from './VaultManager.svelte';
export default VaultManagerComponent;

// Also export other components for direct imports if needed
import BalanceCard from './BalanceCard.svelte';
import TransactionsList from './TransactionsList.svelte';

export {
    BalanceCard,
    TransactionsList
}

// Extension metadata for the marketplace
export const metadata = {
    name: 'Vault Manager',
    description: 'Manage your vault balances and transfer tokens',
    version: '1.0.0',
    icon: 'wallet', // Icon name from the icon library
    author: 'Smart Social Contracts Team',
    permissions: ['read_vault', 'transfer_tokens']
};
