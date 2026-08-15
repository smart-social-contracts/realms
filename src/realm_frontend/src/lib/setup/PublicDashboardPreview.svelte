<script lang="ts">
	let {
		logoPreview = '',
		backgroundPreview = '',
		welcomeMessage = '',
		manifesto = '',
		realmName = 'Your realm',
		primaryColor = '#111827'
	}: {
		logoPreview?: string;
		backgroundPreview?: string;
		welcomeMessage?: string;
		manifesto?: string;
		realmName?: string;
		primaryColor?: string;
	} = $props();

	const defaultLogo = '/images/logo_sphere_only.svg';
	const heroBackground = $derived(
		backgroundPreview ? `url(${backgroundPreview})` : 'none'
	);
</script>

<div class="dashboard-preview">
	<div
		class="dashboard-preview__hero"
		class:dashboard-preview__hero--empty={!backgroundPreview}
		style={`background-image: ${heroBackground};`}
	>
		<div class="dashboard-preview__gradient"></div>
		<div class="dashboard-preview__hero-content">
			<div class="dashboard-preview__identity">
				<div class="dashboard-preview__brand-row">
					<img
						src={logoPreview || defaultLogo}
						alt={realmName}
						class="dashboard-preview__logo"
					/>
					<h3 class="dashboard-preview__title">{realmName}</h3>
				</div>
				{#if welcomeMessage.trim()}
					<p class="dashboard-preview__welcome">{welcomeMessage}</p>
				{/if}
			</div>
		</div>
	</div>

	{#if manifesto.trim()}
		<p class="dashboard-preview__manifesto">{manifesto}</p>
	{/if}

	<div class="dashboard-preview__join-row">
		<button
			type="button"
			class="dashboard-preview__join-btn"
			style={`background:${primaryColor || '#111827'}`}
			disabled
		>
			Join this Realm
			<svg
				class="dashboard-preview__join-icon"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				viewBox="0 0 24 24"
				aria-hidden="true"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
			</svg>
		</button>
	</div>
</div>

<style>
	.dashboard-preview {
		display: flex;
		flex-direction: column;
		min-height: 360px;
		border-radius: 0.75rem;
		border: 1px solid #e2e8f0;
		background: #ffffff;
		overflow: hidden;
	}

	.dashboard-preview__hero {
		position: relative;
		min-height: 220px;
		background: center / cover no-repeat #0f172a;
		overflow: hidden;
	}

	.dashboard-preview__hero--empty {
		background-color: #1e293b;
	}

	.dashboard-preview__gradient {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 55%;
		background: linear-gradient(
			to top,
			#ffffff 0%,
			#ffffff 90%,
			rgba(255, 255, 255, 0.7) 96%,
			transparent 100%
		);
		pointer-events: none;
	}

	.dashboard-preview__hero-content {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1.5rem 1rem 1.25rem;
		z-index: 1;
	}

	.dashboard-preview__identity {
		width: 100%;
		max-width: 28rem;
		text-align: center;
	}

	.dashboard-preview__brand-row {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.dashboard-preview__logo {
		width: 2.5rem;
		height: 2.5rem;
		object-fit: contain;
		flex-shrink: 0;
	}

	.dashboard-preview__title {
		font-size: 1.35rem;
		font-weight: 700;
		color: #111827;
		margin: 0;
		line-height: 1.15;
	}

	.dashboard-preview__welcome {
		font-size: 0.95rem;
		color: #374151;
		font-style: italic;
		margin: 0 auto;
		max-width: 24rem;
		line-height: 1.55;
	}

	.dashboard-preview__manifesto {
		max-width: 36rem;
		margin: 0 auto;
		padding: 1.5rem 1rem 0;
		font-size: 1.1rem;
		color: #374151;
		line-height: 1.8;
		text-align: center;
	}

	.dashboard-preview__join-row {
		display: flex;
		justify-content: center;
		padding: 1.5rem 1rem 1.75rem;
		margin-top: auto;
	}

	.dashboard-preview__join-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.625rem;
		padding: 0.875rem 2rem;
		border-radius: 0.75rem;
		border: none;
		background: #111827;
		color: #fff;
		font-size: 1rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
		cursor: not-allowed;
		opacity: 0.92;
	}

	.dashboard-preview__join-icon {
		width: 1.125rem;
		height: 1.125rem;
	}
</style>
