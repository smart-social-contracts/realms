// Export all components from the vault-manager extension
import VaultManager from './VaultManager.svelte';
import BalanceCard from './BalanceCard.svelte';
import TransactionsList from './TransactionsList.svelte';

export {
    VaultManager,
    BalanceCard,
    TransactionsList
}

// Extension metadata for the marketplace
export const metadata = {
    id: 'vault-manager',
    name: 'Vault Manager',
    description: 'Manage your vault balances and transfer tokens',
    version: '1.0.0',
    icon: 'wallet', // Icon name from the icon library
    author: 'Smart Social Contracts Team',
    permissions: ['read_vault', 'transfer_tokens']
};
