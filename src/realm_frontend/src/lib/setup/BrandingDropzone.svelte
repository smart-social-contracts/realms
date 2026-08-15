<script lang="ts">
	interface Props {
		label: string;
		preview?: string;
		onFile: (file: File) => void;
	}

	let { label, preview = '', onFile }: Props = $props();

	let dragging = $state(false);
	let inputEl: HTMLInputElement | undefined;

	function take(files: FileList | null | undefined) {
		const file = files?.[0];
		if (file) onFile(file);
	}
</script>

<div class="drop-field">
	<p class="drop-field__label">{label}</p>
	<button
		type="button"
		class="drop"
		class:drop--active={dragging}
		class:drop--filled={Boolean(preview)}
		ondragover={(event) => {
			event.preventDefault();
			dragging = true;
		}}
		ondragleave={() => {
			dragging = false;
		}}
		ondrop={(event) => {
			event.preventDefault();
			dragging = false;
			take(event.dataTransfer?.files);
		}}
		onclick={() => inputEl?.click()}
	>
		{#if preview}
			<img src={preview} alt="" class="drop__preview" />
		{/if}
		<span class="drop__copy">
			{preview ? 'Replace — choose file or drag here' : 'Choose file or drag here'}
		</span>
	</button>
	<input
		bind:this={inputEl}
		type="file"
		accept="image/*"
		class="drop__input"
		onchange={(event) => take(event.currentTarget.files)}
	/>
</div>

<style>
	.drop-field {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.drop-field__label {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 500;
		color: #0b1120;
	}

	.drop {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.6rem;
		min-height: 7.5rem;
		width: 100%;
		padding: 1rem;
		border: 1.5px dashed #cbd5e1;
		border-radius: 0.85rem;
		background: #f8fafc;
		color: #475569;
		font: inherit;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.drop--active,
	.drop:hover {
		border-color: #0b1120;
		background: #ffffff;
		color: #0b1120;
	}

	.drop--filled {
		border-style: solid;
	}

	.drop__preview {
		max-height: 4.5rem;
		max-width: 100%;
		object-fit: contain;
	}

	.drop__copy {
		text-align: center;
	}

	.drop__input {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
	}
</style>
