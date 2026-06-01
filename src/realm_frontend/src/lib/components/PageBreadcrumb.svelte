<script lang="ts">
	import { Breadcrumb, BreadcrumbItem } from 'flowbite-svelte';
	import { page } from '$app/stores';
	import { sidebarConfig } from '$lib/stores/sidebar';
	import { resolveBreadcrumb } from '$lib/utils/breadcrumb';

	$: segments = resolveBreadcrumb($page.url.pathname, $sidebarConfig);
	$: showBreadcrumb = segments.length > 0 && $page.url.pathname !== '/';
</script>

{#if showBreadcrumb}
	<Breadcrumb class="mb-6 px-4 pt-4 lg:px-0 lg:pt-4">
		{#each segments as segment, index}
			<BreadcrumbItem href={index < segments.length - 1 ? segment.href : undefined}>
				{segment.label}
			</BreadcrumbItem>
		{/each}
	</Breadcrumb>
{/if}
