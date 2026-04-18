<script lang="ts">
  export let size: number = 24;
</script>

<span
  class="spinner"
  style="--size: {size}px; --border: {Math.max(2, Math.round(size / 10))}px"
  role="status"
  aria-label="Loading"
></span>

<style>
  .spinner {
    display: inline-block;
    width: var(--size);
    height: var(--size);
    border: var(--border) solid var(--surface-2);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
