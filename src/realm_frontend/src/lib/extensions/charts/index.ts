// Export the main component as default for dynamic loading
import ChartsComponent from './Charts.svelte';
export default ChartsComponent;

import TaxAllocationChart from './TaxAllocationChart.svelte';
import AssetPortfolioChart from './AssetPortfolioChart.svelte';
import TaxContributionTreemap from './TaxContributionTreemap.svelte';

export {
    TaxAllocationChart,
    AssetPortfolioChart,
    TaxContributionTreemap
};

// Extension metadata for the marketplace
export const metadata = {
    name: 'Budget Charts',
    description: 'Comprehensive budget visualization charts including tax allocation, asset portfolio, and tax contribution analysis',
    version: '1.0.0',
    icon: 'chart-pie',
    author: 'Smart Social Contracts Team',
    permissions: ['read_budget', 'read_treasury']
};
