<script lang="ts">
	import { Button, P } from 'flowbite-svelte';
	import { _ } from 'svelte-i18n';
	export let title = '';
	export let description = '';
	export let btnHref = '/';
	export let btnTitle = '';
	/** When set, the primary button reloads the page instead of navigating. */
	export let reloadOnClick = false;
	export let mainClass = 'bg-gray-50 dark:bg-gray-900';
	export let mainDivClass =
		'flex flex-col justify-center items-center px-6 mx-auto h-viewport xl:px-0 dark:bg-gray-900';
	export let h1Class =
		'mb-3 text-2xl font-bold leading-tight text-gray-900 sm:text-4xl lg:text-5xl dark:text-white';
	export let imgDiv = 'block md:max-w-lg';
	export let div2Class = 'text-center xl:max-w-4xl';
	export let image = {
		src: '/images/error.svg',
		alt: 'Error'
	};
</script>

<main class={mainClass}>
	<div class={mainDivClass}>
		<div class={imgDiv}>
			<img src={image.src} alt={image.alt} />
		</div>
		<div class={div2Class}>
			<h1 class={h1Class}>
				{title || $_('errors.server_error_title')}
			</h1>
			<P class="mb-5 text-base font-normal text-gray-500 dark:text-gray-400 md:text-lg">
				{description || $_('errors.server_error_description')}
			</P>
			{#if reloadOnClick}
				<Button on:click={() => location.reload()}>
					<svg
						class="-ml-1 mr-2 h-5 w-5"
						fill="currentColor"
						viewBox="0 0 20 20"
						xmlns="http://www.w3.org/2000/svg"
						><path
							fill-rule="evenodd"
							d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
							clip-rule="evenodd"
						/></svg
					>
					{btnTitle || $_('errors.refresh_page')}
				</Button>
			{:else}
				<Button href={btnHref}>
					<svg
						class="-ml-1 mr-2 h-5 w-5"
						fill="currentColor"
						viewBox="0 0 20 20"
						xmlns="http://www.w3.org/2000/svg"
						><path
							fill-rule="evenodd"
							d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
							clip-rule="evenodd"
						/></svg
					>
					{btnTitle || $_('errors.go_back_home')}
				</Button>
			{/if}
		</div>
	</div>
</main>
