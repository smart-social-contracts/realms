<script lang="ts">
	interface Props {
		code: string;
		language?: string;
	}

	let { code, language }: Props = $props();

	let copied = $state(false);
	let copyTimeout: ReturnType<typeof setTimeout> | undefined;

	async function copyCode() {
		try {
			if (navigator.clipboard?.writeText) {
				await navigator.clipboard.writeText(code);
			} else {
				const textarea = document.createElement('textarea');
				textarea.value = code;
				textarea.style.position = 'fixed';
				textarea.style.opacity = '0';
				document.body.appendChild(textarea);
				textarea.select();
				document.execCommand('copy');
				document.body.removeChild(textarea);
			}
			copied = true;
			clearTimeout(copyTimeout);
			copyTimeout = setTimeout(() => {
				copied = false;
			}, 1500);
		} catch {
			// Clipboard unavailable — fail silently
		}
	}
</script>

<div class="relative code-block">
	<button
		type="button"
		class="absolute right-2 top-2 rounded-md border border-gray-600 bg-gray-700 px-2 py-1 text-xs font-medium text-gray-200 transition-colors hover:bg-gray-600 code-block-copy"
		onclick={copyCode}
	>
		{copied ? 'Copied!' : 'Copy'}
	</button>
	<pre
		class="overflow-x-auto rounded-lg bg-gray-900 p-4 pr-16 font-mono text-sm text-gray-100 code-block-pre"
	><code>{code}</code></pre>
</div>

<style>
	.code-block-pre {
		background-color: var(--color-bg-inverse, #111827);
		color: var(--color-text-inverse, #f3f4f6);
	}
</style>
