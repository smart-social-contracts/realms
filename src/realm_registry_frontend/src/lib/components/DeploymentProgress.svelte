<script>
  /** @type {import('$lib/deployment-progress.js').getDeploymentProgress extends (j: infer J) => infer R ? R : never} */
  export let progress;
  /** @type {'full' | 'compact'} */
  export let variant = 'full';
  /** @type {boolean} */
  export let showSteps = true;
</script>

<div class="deployment-progress" class:compact={variant === 'compact'}>
  <div class="progress-header">
    <div class="progress-label-row">
      <span class="progress-label">{progress.currentLabel}</span>
      <span class="progress-percent" aria-hidden="true">{progress.percent}%</span>
    </div>
    <div
      class="progress-track"
      role="progressbar"
      aria-valuenow={progress.percent}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-label="Deployment progress"
    >
      <div
        class="progress-fill"
        class:failed={progress.isFailed}
        class:complete={progress.isComplete}
        style="width: {progress.percent}%"
      ></div>
    </div>
    <p class="progress-description">{progress.currentDescription}</p>
  </div>

  {#if progress.isFailed && progress.error}
    <div class="progress-error" role="alert">
      <strong>Deployment failed</strong>
      <p>{progress.error}</p>
    </div>
  {/if}

  {#if showSteps && variant === 'full'}
    <ol class="progress-steps">
      {#each progress.stages as stage, i}
        {#if stage.id !== 'complete' || progress.isComplete}
          <li class="progress-step" class:done={stage.state === 'done'} class:active={stage.state === 'active'} class:failed={stage.state === 'failed'}>
            <span class="step-marker" aria-hidden="true">
              {#if stage.state === 'done'}
                ✓
              {:else if stage.state === 'failed'}
                ✕
              {:else if stage.state === 'active'}
                …
              {:else}
                {i + 1}
              {/if}
            </span>
            <span class="step-label">{stage.label}</span>
            {#if stage.durationLabel && stage.state !== 'upcoming'}
              <span
                class="step-duration"
                class:estimated={stage.durationEstimated}
                title={stage.durationEstimated ? 'Estimated stage duration' : 'Stage duration'}
              >
                {stage.durationLabel}{#if stage.durationEstimated}~{/if}
              </span>
            {:else if stage.state === 'active'}
              <span class="step-duration active">in progress</span>
            {/if}
          </li>
        {/if}
      {/each}
    </ol>
  {/if}

  {#if progress.backendCanisterId || progress.frontendCanisterId}
    <div class="canister-ids subtle">
      {#if progress.backendCanisterId}
        <span>Backend: {progress.backendCanisterId}</span>
      {/if}
      {#if progress.frontendCanisterId}
        <span>Frontend: {progress.frontendCanisterId}</span>
      {/if}
    </div>
  {/if}
</div>

<style>
  .deployment-progress {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .deployment-progress.compact {
    gap: 0.5rem;
  }

  .progress-header {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .progress-label-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
  }

  .progress-label {
    font-weight: 600;
    font-size: 0.875rem;
    color: #171717;
  }

  .progress-percent {
    font-size: 0.75rem;
    font-weight: 600;
    color: #525252;
    font-variant-numeric: tabular-nums;
  }

  .progress-track {
    height: 0.5rem;
    background: #e5e5e5;
    border-radius: 999px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #2563eb);
    border-radius: 999px;
    transition: width 0.4s ease;
  }

  .progress-fill.complete {
    background: linear-gradient(90deg, #22c55e, #16a34a);
  }

  .progress-fill.failed {
    background: linear-gradient(90deg, #ef4444, #dc2626);
  }

  .progress-description {
    margin: 0;
    font-size: 0.8125rem;
    color: #525252;
    line-height: 1.4;
  }

  .progress-error {
    padding: 0.625rem 0.75rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 0.5rem;
    font-size: 0.8125rem;
    color: #991b1b;
  }

  .progress-error strong {
    display: block;
    margin-bottom: 0.25rem;
  }

  .progress-error p {
    margin: 0;
    word-break: break-word;
  }

  .progress-steps {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .compact .progress-steps {
    display: none;
  }

  .progress-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8125rem;
    color: #a3a3a3;
  }

  .step-label {
    flex: 1;
    min-width: 0;
  }

  .step-duration {
    margin-left: auto;
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
    color: #737373;
    flex-shrink: 0;
  }

  .step-duration.estimated {
    color: #a3a3a3;
  }

  .step-duration.active {
    color: #2563eb;
    font-style: italic;
  }

  .progress-step.done .step-duration {
    color: #15803d;
  }

  .progress-step.failed .step-duration {
    color: #b91c1c;
  }

  .progress-step.done {
    color: #16a34a;
  }

  .progress-step.active {
    color: #2563eb;
    font-weight: 600;
  }

  .progress-step.failed {
    color: #dc2626;
    font-weight: 600;
  }

  .step-marker {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 999px;
    background: #f5f5f5;
    font-size: 0.6875rem;
    flex-shrink: 0;
  }

  .progress-step.active .step-marker {
    background: #dbeafe;
  }

  .progress-step.done .step-marker {
    background: #dcfce7;
  }

  .progress-step.failed .step-marker {
    background: #fee2e2;
  }

  .canister-ids {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    font-size: 0.6875rem;
    color: #737373;
    word-break: break-all;
  }

  .subtle {
    opacity: 0.9;
  }
</style>
