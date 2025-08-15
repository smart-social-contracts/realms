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

