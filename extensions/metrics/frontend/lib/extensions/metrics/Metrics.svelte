<script>
  import TaxAllocationChart from './TaxAllocationChart.svelte';
  import AssetPortfolioChart from './AssetPortfolioChart.svelte';
  import TaxContributionTreemap from './TaxContributionTreemap.svelte';
  import MonthlyCashFlow from './MonthlyCashFlow.svelte';
  import { _ } from 'svelte-i18n';
  import SafeText from '$lib/components/SafeText.svelte';

  // Budget visualization data with translation keys (charts need string values)
  $: budgetData = {
    taxAllocation: [
      { category: $_('extensions.metrics.universal_basic_income'), amount: 45000, color: '#3B82F6' },
      { category: $_('extensions.metrics.innovation_grants'), amount: 25000, color: '#10B981' },
      { category: $_('extensions.metrics.infrastructure'), amount: 15000, color: '#F59E0B' },
      { category: $_('extensions.metrics.healthcare_system'), amount: 8000, color: '#8B5CF6' },
      { category: $_('extensions.metrics.education_programs'), amount: 5000, color: '#EF4444' },
      { category: $_('extensions.metrics.emergency_reserve'), amount: 2000, color: '#6B7280' }
    ],
    assetPortfolio: [
      { symbol: 'ckBTC', balance: 2.5, value: 112500, color: '#F7931A' },
      { symbol: 'ckBTC', balance: 850000, value: 850000, color: '#3B82F6' },
      { symbol: 'ICP', balance: 12000, value: 156000, color: '#29ABE2' },
      { symbol: 'USDC', balance: 75000, value: 75000, color: '#2775CA' },
      { symbol: 'ckETH', balance: 45, value: 103500, color: '#627EEA' }
    ],
    taxContributions: [
      // Citizens
      { name: 'Alice Chen', type: 'citizen', contribution: 12500, color: '#3B82F6', category: 'Individual' },
      { name: 'Bob Martinez', type: 'citizen', contribution: 8900, color: '#3B82F6', category: 'Individual' },
      { name: 'Carol Johnson', type: 'citizen', contribution: 15200, color: '#3B82F6', category: 'Individual' },
      { name: 'David Kim', type: 'citizen', contribution: 7800, color: '#3B82F6', category: 'Individual' },
      { name: 'Eva Rodriguez', type: 'citizen', contribution: 11300, color: '#3B82F6', category: 'Individual' },
      { name: 'Frank Wilson', type: 'citizen', contribution: 9600, color: '#3B82F6', category: 'Individual' },
      
      // Organizations
      { name: 'Nova Tech Corp', type: 'organization', contribution: 45000, color: '#10B981', category: 'Technology' },
      { name: 'Green Energy Solutions', type: 'organization', contribution: 32000, color: '#059669', category: 'Energy' },
      { name: 'Digital Finance Ltd', type: 'organization', contribution: 28500, color: '#0D9488', category: 'Finance' },
      { name: 'Smart Healthcare Inc', type: 'organization', contribution: 22000, color: '#0891B2', category: 'Healthcare' },
      { name: 'Education Plus', type: 'organization', contribution: 18000, color: '#0284C7', category: 'Education' },
      { name: 'Infrastructure Co', type: 'organization', contribution: 35000, color: '#2563EB', category: 'Infrastructure' }
    ]
  };
</script>

<div class="charts-extension">
  <!-- Budget Visualization Charts -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
    <!-- Tax Allocation Pie Chart -->
    <TaxAllocationChart data={budgetData.taxAllocation} />
    
    <!-- Asset Portfolio Donut Chart -->
    <AssetPortfolioChart data={budgetData.assetPortfolio} />
  </div>
  
  <!-- Tax Contribution Treemap -->
  <div class="mt-6">
    <TaxContributionTreemap data={budgetData.taxContributions} />
  </div>
  
  <!-- Monthly Cash Flow -->
  <div class="mt-6">
    <MonthlyCashFlow />
  </div>
</div>

<style>
  .charts-extension {
    width: 100%;
  }
</style>
