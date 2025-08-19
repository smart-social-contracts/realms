<script>
  import { Chart } from 'flowbite-svelte';
  import { _ } from 'svelte-i18n';
  
  export let data = [];
</script>

<div class="bg-white rounded-lg p-6 border border-gray-200">
  <h4 class="font-semibold text-gray-700 mb-4 flex items-center">
    📊 <span class="ml-2">{$_('extensions.metrics.tax_allocation_breakdown')}</span>
  </h4>
  <Chart options={{
    chart: {
      type: 'pie',
      height: 350,
      fontFamily: 'Inter, sans-serif',
      toolbar: { show: false }
    },
    labels: data.map(item => item.category),
    series: data.map(item => item.amount),
    colors: data.map(item => item.color),
    legend: {
      position: 'bottom',
      fontSize: '12px',
      labels: {
        colors: '#4B5563'
      }
    },
    tooltip: {
      y: {
        formatter: (value) => `${value.toLocaleString()} ckBTC`
      }
    },
    dataLabels: {
      enabled: true,
      formatter: (val) => `${val.toFixed(1)}%`,
      style: {
        fontSize: '12px',
        fontWeight: 'bold'
      }
    },
    responsive: [{
      breakpoint: 640,
      options: {
        chart: {
          height: 300
        },
        legend: {
          position: 'bottom'
        }
      }
    }]
  }} />
</div>
