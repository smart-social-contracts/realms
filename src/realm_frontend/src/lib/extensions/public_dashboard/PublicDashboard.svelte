<script lang="ts">
	import ChartWidget from '../../../routes/utils/widgets/ChartWidget.svelte';
	import { onMount } from 'svelte';
	import ActivityList from '../../../routes/(sidebar)/dashboard/ActivityList.svelte';
	import OrganizationTable from '../../../routes/utils/dashboard/OrganizationTable.svelte';
	import { backend } from '$lib/canisters';
	import { principal } from '$lib/stores/auth';
	import { universe, snapshots } from '$lib/stores/auth';
	import { writable } from 'svelte/store';

	let greeting = '';

	const mockUserData = [
		['01 Jan', '03 Jan', '05 Jan', '07 Jan', '09 Jan', '11 Jan', '13 Jan', '15 Jan', '17 Jan', '19 Jan', '21 Jan'],
		[120, 145, 160, 175, 185, 190, 210, 250, 290, 310, 350]
	];
	
	const mockOrgData = [
		['01 Jan', '03 Jan', '05 Jan', '07 Jan', '09 Jan', '11 Jan', '13 Jan', '15 Jan', '17 Jan', '19 Jan', '21 Jan'],
		[5, 5, 6, 6, 7, 8, 8, 9, 10, 12, 15]
	];
	
	const mockAssetData = [
		['01 Jan', '03 Jan', '05 Jan', '07 Jan', '09 Jan', '11 Jan', '13 Jan', '15 Jan', '17 Jan', '19 Jan', '21 Jan'],
		[22000000, 22200000, 22500000, 22800000, 23000000, 23400000, 23800000, 24000000, 24500000, 24800000, 25000000]
	];

	const statsDatesValues = writable<[string[], number[]]>(mockUserData);
	const orgsDatesValues = writable<[string[], number[]]>(mockOrgData);
	const assetsDatesValues = writable<[string[], number[]]>(mockAssetData);

	function onSubmit(event) {
		const name = event.target.name.value;
		backend.greet(name).then((response) => {
			greeting = response;
		});

		backend.get_universe().then((response) => {
			let principalText = response;
			console.log(`principalText = ${principalText}`);
			principal.set(principalText);
			const jsonObject = JSON.parse(principalText);
			console.log(jsonObject);
			console.log(jsonObject.users[0].id);
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
		console.log('Using mock data');
		
		return false;
	}

	$: console.log('Parent statsDatesValues updated:', $statsDatesValues);

	onMount(() => {
		get_snapshot_data();
	});
</script>

<div class="mt-px space-y-4">
	<ChartWidget
		title="Users"
		description="Active users in the platform"
		dateValues={$statsDatesValues}
	/>

	<ChartWidget
		title="Organizations"
		description="Total registered organizations"
		dateValues={$orgsDatesValues}
	/>

	<ChartWidget
		title="Assets"
		description="Total assets value in USD"
		dateValues={$assetsDatesValues}
	/>

	<OrganizationTable />
	<div class="grid grid-cols-1 gap-4 xl:grid-cols-1">
		<ActivityList />
	</div>

</div>
