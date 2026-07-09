<script lang="ts">
	import '../app.pcss';
	import { page } from '$app/stores';
	import NotFound from './utils/pages/NotFound.svelte';
	import Maintenance from './utils/pages/Maintenance.svelte';
	import ServerError from './utils/pages/ServerError.svelte';

	const pages = {
		400: Maintenance,
		404: NotFound,
		500: ServerError
	} as const;

	type ErrorCode = keyof typeof pages;

	const status = +$page.status;
	const index = Object.keys(pages)
		.map((x) => +x)
		.reduce((p, c) => (p < status ? c : p)) as ErrorCode;
	const component = pages[index];
	const errMessage = $page.error?.message;

	import MetaTag from './utils/MetaTag.svelte';

	const path: string = `/errors/${index}`;
	const description: string = `${index} - Smart Social Contracts`;
	const title: string = `Realms - ${index} page`;
	const subtitle: string = `${index} page`;
</script>

<MetaTag {path} {description} {title} {subtitle} />

{#if index === 500}
	<ServerError
		description={errMessage ||
			"It's always time for a coffee break. We should be back by the time you finish your coffee."}
		btnTitle={errMessage ? 'Refresh page' : 'Go back home'}
		reloadOnClick={!!errMessage}
	/>
{:else}
	<svelte:component this={component} />
{/if}
