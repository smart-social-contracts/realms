<script lang="ts">
	import { Modal, Button } from 'flowbite-svelte';
	import { bridgeModalRequest, dismissBridgeModal } from '$lib/stores/bridge-modal';

	let open = false;

	$: open = $bridgeModalRequest !== null;

	function actionClass(tone: string | undefined): string {
		switch (tone) {
			case 'danger':
				return 'bg-red-600 text-white hover:bg-red-700';
			case 'secondary':
				return 'bg-gray-100 text-gray-900 hover:bg-gray-200 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600';
			default:
				return 'bg-gray-900 text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900';
		}
	}

	function choose(actionId: string) {
		$bridgeModalRequest?.resolve(actionId);
	}
</script>

{#if $bridgeModalRequest}
	<Modal
		bind:open
		title={$bridgeModalRequest.title}
		size="sm"
		autoclose={false}
		outsideclose
		on:close={dismissBridgeModal}
	>
		<p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
			{$bridgeModalRequest.body}
		</p>
		<svelte:fragment slot="footer">
			{#each $bridgeModalRequest.actions as action (action.id)}
				<Button
					color="none"
					class={actionClass(action.tone)}
					on:click={() => choose(action.id)}
				>
					{action.label}
				</Button>
			{/each}
		</svelte:fragment>
	</Modal>
{/if}
