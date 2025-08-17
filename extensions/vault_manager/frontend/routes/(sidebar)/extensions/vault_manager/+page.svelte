<script lang="ts">
	import { onMount } from 'svelte';
	import VaultManager from '$lib/extensions/vault_manager';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../../utils/MetaTag.svelte';
	import { _ } from 'svelte-i18n';
	
	const path: string = '/extensions/vault_manager';
	const description: string = 'Manage your vault balance and transfer tokens';
	const title: string = SITE_NAME + ' - ' + $_('extensions.vault_manager.title');
	const subtitle: string = $_('extensions.vault_manager.title');
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="fixed inset-0 lg:ml-64 overflow-auto">
	<div class="w-full h-full">
		<VaultManager />
	</div>
</main>
