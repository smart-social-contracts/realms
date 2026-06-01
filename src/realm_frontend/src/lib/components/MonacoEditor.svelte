<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import loader from '@monaco-editor/loader';
	import type * as Monaco from 'monaco-editor';
	import { DEFAULT_MONACO_THEME, DEFAULT_MONACO_LANGUAGE } from './monaco-theme';

	let {
		code = '',
		language = DEFAULT_MONACO_LANGUAGE,
		readOnly = true,
		theme = DEFAULT_MONACO_THEME,
	}: {
		code?: string;
		language?: string;
		readOnly?: boolean;
		theme?: string;
	} = $props();

	let container: HTMLDivElement | undefined = $state();
	let editor: Monaco.editor.IStandaloneCodeEditor | undefined = $state();
	let monacoApi: typeof Monaco | undefined = $state();
	let loadError = $state('');

	const MONACO_VERSION = '0.52.2';
	const MONACO_VS = `https://cdn.jsdelivr.net/npm/monaco-editor@${MONACO_VERSION}/min/vs`;

	onMount(() => {
		let disposed = false;

		(async () => {
			if (!container) return;
			try {
				loader.config({ paths: { vs: MONACO_VS } });
				const monaco = await loader.init();
				if (disposed || !container) return;

				monacoApi = monaco;
				monaco.editor.setTheme(theme);

				editor = monaco.editor.create(container, {
					value: code,
					language,
					readOnly,
					theme,
					automaticLayout: true,
					minimap: { enabled: true },
					scrollBeyondLastLine: false,
					fontSize: 13,
					lineNumbers: 'on',
					renderLineHighlight: 'all',
					wordWrap: 'off',
					padding: { top: 12, bottom: 12 },
					scrollbar: {
						verticalScrollbarSize: 10,
						horizontalScrollbarSize: 10,
					},
				});
			} catch (e: unknown) {
				loadError = e instanceof Error ? e.message : String(e);
			}
		})();

		return () => {
			disposed = true;
		};
	});

	$effect(() => {
		if (!editor) return;
		const model = editor.getModel();
		if (model && code !== model.getValue()) {
			const pos = editor.getPosition();
			editor.setValue(code);
			if (pos) editor.setPosition(pos);
		}
	});

	$effect(() => {
		if (!editor || !monacoApi) return;
		const model = editor.getModel();
		if (model && monacoApi.editor.getModelLanguage(model) !== language) {
			monacoApi.editor.setModelLanguage(model, language);
		}
	});

	$effect(() => {
		editor?.updateOptions({ readOnly });
	});

	$effect(() => {
		monacoApi?.editor.setTheme(theme);
	});

	onDestroy(() => {
		editor?.dispose();
		editor = undefined;
	});
</script>

{#if loadError}
	<div class="monaco-error">
		<p>Failed to load code editor.</p>
		<pre>{loadError}</pre>
	</div>
{:else}
	<div class="monaco-host" bind:this={container}></div>
{/if}

<style>
	.monaco-host {
		width: 100%;
		height: 100%;
		min-height: 0;
	}

	.monaco-error {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		padding: 24px;
		background: #f3f3f3;
		color: #b91c1c;
		font-size: 0.875rem;
		text-align: center;
	}

	.monaco-error pre {
		margin-top: 8px;
		font-size: 0.75rem;
		color: #6b7280;
		white-space: pre-wrap;
		max-width: 100%;
	}
</style>
