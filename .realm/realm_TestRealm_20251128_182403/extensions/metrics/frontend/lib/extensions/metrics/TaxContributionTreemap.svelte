<script>
  import { Chart } from 'flowbite-svelte';
  import { _ } from 'svelte-i18n';
  
  export let data = [];
  
  // Group data by type for better visualization
  $: groupedData = [
    {
      name: $_('extensions.metrics.citizens'),
      data: data.filter(item => item.type === 'citizen').map(item => ({
        x: item.name,
        y: item.contribution
      }))
    },
    {
      name: $_('extensions.metrics.organizations'), 
      data: data.filter(item => item.type === 'organization').map(item => ({
        x: item.name,
        y: item.contribution
      }))
    }
  ];
</script>

<div class="bg-white rounded-lg p-6 border border-gray-200">
  <h4 class="font-semibold text-gray-700 mb-4 flex items-center">
    🌳 <span class="ml-2">{$_('extensions.metrics.tax_contribution_analysis')}</span>
  </h4>
  <Chart options={{
    chart: {
      type: 'treemap',
      height: 400,
      fontFamily: 'Inter, sans-serif',
      toolbar: { show: false }
    },
    series: groupedData,
    colors: ['#3B82F6', '#10B981'],
    plotOptions: {
      treemap: {
        enableShades: true,
        shadeIntensity: 0.5,
        reverseNegativeShade: true,
        colorScale: {
          ranges: [
            { from: 0, to: 10000, color: '#E0F2FE' },
            { from: 10001, to: 20000, color: '#7DD3FC' },
            { from: 20001, to: 30000, color: '#38BDF8' },
            { from: 30001, to: 50000, color: '#0EA5E9' }
          ]
        }
      }
    },
    legend: {
      show: true,
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
      style: {
        fontSize: '12px',
        fontWeight: 'bold',
        colors: ['#FFFFFF']
      },
      formatter: (text, op) => {
        return [text, `${op.value.toLocaleString()} ckBTC`];
      }
    },
    responsive: [{
      breakpoint: 640,
      options: {
        chart: {
          height: 300
        }
      }
    }]
  }} />
</div>
