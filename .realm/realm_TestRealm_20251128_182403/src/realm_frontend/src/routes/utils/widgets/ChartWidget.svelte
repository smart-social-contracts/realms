<script lang="ts">
	import { Chart, Card, A, Button, Dropdown, DropdownItem } from 'flowbite-svelte';
	import { ChevronRightOutline, ChevronDownOutline } from 'flowbite-svelte-icons';

	export let title;
	export let description;
	export let dateValues: [string[], number[]] = [[], []];

	console.log(`dateValues (2)`, dateValues);

	let chart;

	$: if (chart && dateValues) {
		console.log('Updating chart with new data:', dateValues);
		chart.updateOptions({
			series: [{
				name: 'New users',
				data: dateValues[1],
				color: '#1A56DB'
			}],
			xaxis: {
				categories: dateValues[0]
			},
			theme: {
				mode: 'light'
			}
		});
	}

	$: seriesData = [
		{
			name: 'New users',
			data: dateValues[1],
			color: '#1A56DB'
		}
	];

	$: options = {
		chart: {
			height: '400px',
			maxWidth: '100%',
			type: 'area',
			fontFamily: 'Inter, sans-serif',
			dropShadow: {
				enabled: false
			},
			toolbar: {
				show: false
			},
			background: '#ffffff',
			foreColor: '#333333'
		},
		theme: {
			mode: 'light'
		},
		tooltip: {
			enabled: true,
			x: {
				show: false
			},
			theme: 'light'
		},
		fill: {
			type: 'gradient',
			gradient: {
				opacityFrom: 0.55,
				opacityTo: 0,
				shade: '#1C64F2',
				gradientToColors: ['#1C64F2']
			}
		},
		dataLabels: {
			enabled: false
		},
		stroke: {
			width: 6
		},
		grid: {
			show: true,
			strokeDashArray: 4,
			padding: {
				left: 10,
				right: 10,
				top: 0
			},
			borderColor: '#e5e7eb'
		},
		series: seriesData,
		xaxis: {
			categories: dateValues[0],
			labels: {
				show: true,
				style: {
					colors: '#6b7280'
				}
			},
			axisBorder: {
				show: true,
				color: '#e5e7eb'
			},
			axisTicks: {
				show: true,
				color: '#e5e7eb'
			}
		},
		yaxis: {
			labels: {
				show: true,
				style: {
					colors: '#6b7280'
				},
				formatter: (value) => value.toLocaleString() // Format values as comma-separated numbers
			},
			axisBorder: {
				show: true,
				color: '#e5e7eb'
			},
			axisTicks: {
				show: true,
				color: '#e5e7eb'
			}
		}
	};
</script>

<Card size="xl" class="bg-white">
	<div class="flex justify-between">
		<div>
			<h5 class="pb-2 text-3xl font-bold leading-none text-gray-900">{title}</h5>
			<p class="text-base font-normal text-gray-500">{description}</p>
		</div>
		<div
			class="flex items-center px-2.5 py-0.5 text-center text-base font-semibold text-green-500"
		>
			12%
			<ChevronRightOutline class="ms-1 h-6 w-6" />
		</div>
	</div>
	<Chart bind:chart={chart} {options} class="py-6" />
	<div
		class="grid grid-cols-1 items-center justify-between border-t border-gray-200"
	>
		<div class="flex items-center justify-between pt-5">
			<Button
				class="inline-flex items-center bg-transparent py-0 text-center text-sm font-medium text-gray-500 hover:bg-transparent hover:text-gray-900 focus:ring-transparent"
			>
				Last 7 days<ChevronDownOutline class="m-2.5 ms-1.5 w-2.5" /></Button
			>
			<Dropdown class="w-40" offset="-6">
				<DropdownItem>Yesterday</DropdownItem>
				<DropdownItem>Today</DropdownItem>
				<DropdownItem>Last 7 days</DropdownItem>
				<DropdownItem>Last 30 days</DropdownItem>
				<DropdownItem>Last 90 days</DropdownItem>
			</Dropdown>
			<A
				href="/"
				class="hover:text-primary-700 rounded-lg px-3 py-2 text-sm font-semibold uppercase hover:bg-gray-100 hover:no-underline"
			>
				Users Report
				<ChevronRightOutline class="ms-1.5 h-2.5 w-2.5" />
			</A>
		</div>
	</div>
</Card>
