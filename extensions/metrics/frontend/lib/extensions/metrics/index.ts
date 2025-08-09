// Export the main component as default for dynamic loading
import MetricsComponent from './Metrics.svelte';
export default MetricsComponent;

import TaxAllocationChart from './TaxAllocationChart.svelte';
import AssetPortfolioChart from './AssetPortfolioChart.svelte';
import TaxContributionTreemap from './TaxContributionTreemap.svelte';
import MonthlyCashFlow from './MonthlyCashFlow.svelte';

export {
    TaxAllocationChart,
    AssetPortfolioChart,
    TaxContributionTreemap,
    MonthlyCashFlow
};

// Extension metadata for the marketplace
export const metadata = {
    name: 'Budget Metrics',
    description: 'Comprehensive budget visualization including charts, cash flow analysis, and tax contribution metrics',
    version: '1.0.0',
    icon: 'chart-bar',
    author: 'Smart Social Contracts Team',
    permissions: ['read_budget', 'read_treasury'],
    profiles: ['member', 'admin']
};
