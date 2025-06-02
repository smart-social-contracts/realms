<script lang="ts">
	import MetaTag from '../../utils/MetaTag.svelte';
	import IdentityCard from '../../utils/settings/IdentityCard.svelte';
	import { imagesPath } from '../../utils/variables';
	import Footer from '../Footer.svelte';

	const path: string = '/idenities';
	const description: string = 'Identities';
	const metaTitle: string = 'Identities';
	const subtitle: string = 'Identities';

	import { onMount } from 'svelte';

	onMount(() => {});
</script>

<MetaTag {path} {description} title={metaTitle} {subtitle} />

<div class="mt-px space-y-4">
	<div class="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3"></div>

	<IdentityCard
		src={imagesPath('outdid_logo.jpeg')}
		title="Outdid"
		description="Passport:ETH[0x388C818CA8B9251b393131C08a736A67ccB19297]"
	/>

	<IdentityCard src={imagesPath('logo-swissid_bianco.jpg')} title="SwissID" description="" />
</div>
<!-- <Footer /> -->
