<script lang="ts">
	import { onMount } from 'svelte';
	import VaultManager from '$lib/extensions/vault';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../../utils/MetaTag.svelte';
	import { _ } from 'svelte-i18n';
	
	const path: string = '/extensions/vault';
	const description: string = 'Manage your vault balance and transfer tokens';
	const title: string = SITE_NAME + ' - ' + $_('extensions.vault.title');
	const subtitle: string = $_('extensions.vault.title');
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="w-full">
	<div class="w-full pb-32">
		<VaultManager />
	</div>
</main>
