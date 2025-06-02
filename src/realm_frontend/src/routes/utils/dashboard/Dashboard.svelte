<script lang="ts">
	import thickbars from '../graphs/thickbars';
	import ChartWidget from '../widgets/ChartWidget.svelte';
	import { Card, Chart } from 'flowbite-svelte';
	import type { PageData } from '../../(sidebar)/$types';
	import Stats from './Stats.svelte';
	import users from '../graphs/users';
	import DarkChart from '../widgets/DarkChart.svelte';
	import { onMount } from 'svelte';
	import getChartOptions from '../../(sidebar)/dashboard/chart_options';
	import ActivityList from './ActivityList.svelte';
	import Change from './Change.svelte';
	import Chat from './Chat.svelte';
	import DesktopPc from './DesktopPc.svelte';
	import Insights from './Insights.svelte';
	import Traffic from './Traffic.svelte';
	import Transactions from './Transactions.svelte';
	import OrganizationTable from './OrganizationTable.svelte';
	import { backend } from '$lib/canisters';
	import AuthButton from '$lib/components/AuthButton.svelte';
	import { principal } from '$lib/stores/auth';
	import { universe, snapshots } from '$lib/stores/auth';
	import { writable } from 'svelte/store';

	let greeting = '';

	const statsDatesValues = writable<[string[], number[]]>([[], []]);
	const orgsDatesValues = writable<[string[], number[]]>([[], []]);

	function onSubmit(event) {
		const name = event.target.name.value;
		backend.greet(name).then((response) => {
			greeting = response;
		});

		backend.get_universe().then((response) => {
			let principalText = response;
			console.log(`principalText = ${principalText}`);
			principal.set(principalText); // Update the principal store
			// Parse the string as JSON
			const jsonObject = JSON.parse(principalText);
			console.log(jsonObject); // This should log the JSON object
			console.log(jsonObject.users[0].id); // This should log the JSON object
		});

		return false;
	}

	function onSubmitGetUniverse(event) {
		backend.status().then((response) => {
			console.log('status', response);
			universe.set(response);
		});
		return false;
	}

	function get_snapshot_data() {
		backend
			.get_stats()
			.then((response) => {
				console.log('Raw response:', response);
				console.log('Response length:', response.length);
				snapshots.set(response);

				let dates: string[] = [];
				let userValues: number[] = [];
				let orgValues: number[] = [];

				// Sort snapshots by date
				const sortedSnapshots = [...response].sort((a, b) => new Date(a.id).getTime() - new Date(b.id).getTime());
				console.log('Sorted snapshots:', sortedSnapshots);

				if (sortedSnapshots.length === 0) {
					console.warn('No snapshots data received');
					return;
				}

				sortedSnapshots.forEach((snapshot) => {
					console.log('Processing snapshot:', snapshot);
					const formattedDate = new Date(snapshot.id).toLocaleDateString('en-GB', {
						day: '2-digit',
						month: 'short'
					});
					dates.push(formattedDate);
					userValues.push(snapshot.data.total_num_members);
					orgValues.push(Object.keys(snapshot.data.organizations).length);
				});

				console.log('Dates array:', dates);
				console.log('User Values array:', userValues);
				console.log('Org Values array:', orgValues);

				// Update both stores with new values
				statsDatesValues.set([[...dates], [...userValues]]);
				orgsDatesValues.set([[...dates], [...orgValues]]);

				console.log('Final statsDatesValues:', $statsDatesValues);
				console.log('Final orgsDatesValues:', $orgsDatesValues);
			})
			.catch((error) => {
				console.error('Error fetching stats:', error);
			});

		return false;
	}

	$: console.log('Parent statsDatesValues updated:', $statsDatesValues);

	onMount(() => {
		get_snapshot_data();
	});
</script>

<div class="mt-px space-y-4">
	<!-- <section id="aaa">{statsDatesValues}</section> -->
	<ChartWidget
		title="Users"
		description=""
		dateValues={$statsDatesValues}
	/>

	<ChartWidget
		title="Organizations"
		description=""
		dateValues={$orgsDatesValues}
	/>

	<ChartWidget
		title="Assets"
		description=""
		dateValues={[
			['01 Jan', '05 Jan', '10 Jan', '15 Jan', '21 Jan'],
			[22000000, 22500000, 23000000, 24000000, 25000000]
		]}
	/>

	<!-- <ChartWidget title="Assets" description="" dateValues={statsDatesValues} /> -->

	<!-- <Stats /> -->
	<OrganizationTable />
	<!-- <div class="grid grid-cols-1 gap-4 xl:grid-cols-1">
		<ActivityList />
	</div> -->

</div>
