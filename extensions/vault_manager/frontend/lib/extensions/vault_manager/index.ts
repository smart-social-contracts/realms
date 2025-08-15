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

