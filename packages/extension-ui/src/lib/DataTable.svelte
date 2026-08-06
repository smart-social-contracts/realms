<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Column {
		key: string;
		label: string;
		align?: 'left' | 'right' | 'center';
	}

	interface Props {
		columns: Column[];
		rows: Array<Record<string, unknown>>;
		empty?: string;
		cell?: Snippet<[Record<string, unknown>, Column]>;
	}

	let { columns, rows, empty = 'No data', cell }: Props = $props();

	const alignClasses: Record<NonNullable<Column['align']>, string> = {
		left: 'text-left',
		right: 'text-right',
		center: 'text-center'
	};

	function cellAlign(column: Column): string {
		return alignClasses[column.align ?? 'left'];
	}
</script>

{#if rows.length === 0}
	<p class="py-8 text-center text-sm text-gray-500 dark:text-gray-400 data-table-empty">{empty}</p>
{:else}
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700 data-table">
			<thead>
				<tr>
					{#each columns as column}
						<th
							scope="col"
							class="px-4 py-3 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400 {cellAlign(column)} data-table-head"
						>
							{column.label}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
				{#each rows as row}
					<tr class="transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50 data-table-row">
						{#each columns as column}
							<td class="whitespace-nowrap px-4 py-3 text-sm text-gray-700 dark:text-gray-300 {cellAlign(column)} data-table-cell">
								{#if cell}
									{@render cell(row, column)}
								{:else}
									{String(row[column.key] ?? '')}
								{/if}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<style>
	.data-table-head {
		color: var(--color-text-secondary, #6b7280);
	}

	.data-table-cell {
		color: var(--color-text-primary, #374151);
	}

	.data-table-empty {
		color: var(--color-text-secondary, #6b7280);
	}

	:global(.dark) .data-table-head {
		color: var(--color-text-secondary, #9ca3af);
	}

	:global(.dark) .data-table-cell {
		color: var(--color-text-primary, #d1d5db);
	}

	:global(.dark) .data-table-empty {
		color: var(--color-text-secondary, #9ca3af);
	}
</style>
