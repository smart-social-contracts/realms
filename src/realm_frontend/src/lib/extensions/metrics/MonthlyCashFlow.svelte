<script>
  // Monthly cash flow data
  const cashFlowData = {
    income: [
      { category: 'Tax Revenue', amount: 3450 },
      { category: 'License Fees', amount: 350 },
      { category: 'Healthcare Contributions', amount: 180 },
      { category: 'Housing Payments', amount: 750 }
    ],
    expenses: [
      { category: 'UBI Payments', amount: 1200 },
      { category: 'Innovation Grants', amount: 5000 },
      { category: 'Tax Refunds', amount: 125 }
    ]
  };
  
  $: totalIncome = cashFlowData.income.reduce((sum, item) => sum + item.amount, 0);
  $: totalExpenses = cashFlowData.expenses.reduce((sum, item) => sum + item.amount, 0);
  $: netFlow = totalIncome - totalExpenses;
</script>

<div class="bg-white rounded-lg p-6 border border-gray-200">
  <h4 class="font-semibold text-gray-700 mb-4 flex items-center">
    💰 <span class="ml-2">Monthly Cash Flow</span>
  </h4>
  
  <div class="space-y-3">
    <!-- Income -->
    <div class="bg-white rounded-lg p-3 border">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-green-700">📈 Income</span>
        <span class="text-lg font-bold text-green-600">+{totalIncome.toLocaleString()} NVC</span>
      </div>
      <div class="text-xs text-gray-600 space-y-1">
        {#each cashFlowData.income as item}
          <div class="flex justify-between">
            <span>{item.category}</span>
            <span>{item.amount.toLocaleString()} NVC</span>
          </div>
        {/each}
      </div>
    </div>
    
    <!-- Expenses -->
    <div class="bg-white rounded-lg p-3 border">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm font-medium text-red-700">📉 Expenses</span>
        <span class="text-lg font-bold text-red-600">-{totalExpenses.toLocaleString()} NVC</span>
      </div>
      <div class="text-xs text-gray-600 space-y-1">
        {#each cashFlowData.expenses as item}
          <div class="flex justify-between">
            <span>{item.category}</span>
            <span>{item.amount.toLocaleString()} NVC</span>
          </div>
        {/each}
      </div>
    </div>
    
    <!-- Net Flow -->
    <div class="bg-blue-50 rounded-lg p-3 border border-blue-200">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-blue-700">💰 Net Monthly Flow</span>
        <span class="text-lg font-bold {netFlow >= 0 ? 'text-blue-600' : 'text-red-600'}">
          {netFlow >= 0 ? '+' : ''}{netFlow.toLocaleString()} NVC
        </span>
      </div>
    </div>
  </div>
</div>
