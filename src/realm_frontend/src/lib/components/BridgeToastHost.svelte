<script lang="ts">
	import { bridgeToasts, dismissBridgeToast } from '$lib/stores/bridge-toast';

	function colorClass(level: string): string {
		switch (level) {
			case 'success':
				return 'border-green-300 bg-green-50 text-green-800 dark:border-green-700 dark:bg-green-900/30 dark:text-green-200';
			case 'error':
				return 'border-red-300 bg-red-50 text-red-800 dark:border-red-700 dark:bg-red-900/30 dark:text-red-200';
			default:
				return 'border-blue-300 bg-blue-50 text-blue-800 dark:border-blue-700 dark:bg-blue-900/30 dark:text-blue-200';
		}
	}
</script>

<div class="pointer-events-none fixed bottom-4 right-4 z-[100] flex max-w-sm flex-col gap-2">
	{#each $bridgeToasts as toast (toast.id)}
		<div
			class="pointer-events-auto rounded-lg border px-4 py-3 text-sm shadow-lg {colorClass(toast.level)}"
			role="status"
		>
			<div class="flex items-start justify-between gap-3">
				<span>{toast.message}</span>
				<button
					type="button"
					class="shrink-0 text-current opacity-60 hover:opacity-100"
					aria-label="Dismiss"
					onclick={() => dismissBridgeToast(toast.id)}
				>
					&times;
				</button>
			</div>
		</div>
	{/each}
</div>
