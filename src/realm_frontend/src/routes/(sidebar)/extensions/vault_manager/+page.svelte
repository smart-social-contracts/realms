<script lang="ts">
	import { onMount } from 'svelte';
	import VaultManager from '$lib/extensions/vault_manager';
	import { SITE_NAME } from '$lib/globals';
	import MetaTag from '../../../utils/MetaTag.svelte';
	
	const path: string = '/extensions/vault_manager';
	const description: string = 'Manage your vault balance and transfer tokens';
	const title: string = SITE_NAME + ' - Vault Manager';
	const subtitle: string = 'Vault Manager';
</script>

<MetaTag {path} {description} {title} {subtitle} />

<main class="p-4">
	<div class="max-w-7xl mx-auto">
		<VaultManager />
	</div>
</main>
