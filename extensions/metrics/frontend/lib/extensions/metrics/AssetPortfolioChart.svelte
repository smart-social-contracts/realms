<script>
  import { Chart } from 'flowbite-svelte';
  import { _ } from 'svelte-i18n';
  
  export let data = [];
</script>

<div class="bg-white rounded-lg p-6 border border-gray-200">
  <h4 class="font-semibold text-gray-700 mb-4 flex items-center">
    💰 <span class="ml-2">{$_('extensions.metrics.asset_portfolio_distribution')}</span>
  </h4>
  <Chart options={{
    chart: {
      type: 'donut',
      height: 350,
      fontFamily: 'Inter, sans-serif',
      toolbar: { show: false }
    },
    labels: data.map(item => item.symbol),
    series: data.map(item => item.value),
    colors: data.map(item => item.color),
    legend: {
      position: 'bottom',
      fontSize: '12px',
      labels: {
        colors: '#4B5563'
      },
      formatter: (seriesName, opts) => {
        const index = opts.seriesIndex;
        const asset = data[index];
        return `${seriesName} (${asset.balance.toLocaleString()})`;
      }
    },
    plotOptions: {
      pie: {
        donut: {
          size: '70%',
          labels: {
            show: true,
            total: {
              show: true,
              label: $_('extensions.metrics.total_value'),
              fontSize: '14px',
              fontWeight: 'bold',
              color: '#374151',
              formatter: (w) => `${(w.globals.series.reduce((a, b) => a + b, 0) / 1000).toFixed(0)}K ckBTC`
            }
          }
        }
      }
    },
    tooltip: {
      y: {
        formatter: (value) => `${(value / 1000).toFixed(1)}K ckBTC`
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
        },
        plotOptions: {
          pie: {
            donut: {
              size: '85%'
            }
          }
        }
      }
    }]
  }} />
</div>
